"""/api/shop/* — public read-only routes per STAGE_2_SPEC.md §5.2.4."""
from decimal import Decimal, InvalidOperation

from flask import Blueprint, request, jsonify
from sqlalchemy import or_

from extensions import db
from app.models import User, SalesmanProfile

from ..models import Product
from ..ranking import top_products, top_salesmen
from .. import CATEGORIES


public_shop_bp = Blueprint('shop_public', __name__, url_prefix='/api/shop')


def _serialise_salesman_card(user):
    profile = getattr(user, 'salesman_profile', None)
    product_count = Product.query.filter(
        Product.salesman_user_id == user.id,
        Product.status == 'active',
    ).count()
    return {
        'user_id': str(user.id),
        'shop_name': profile.shop_name if profile else user.name,
        'shop_slug': profile.shop_slug if profile else None,
        'photo_url': profile.photo_url if profile else None,
        'banner_url': profile.banner_url if profile else None,
        'bio': profile.bio if profile else None,
        'suburb': user.suburb,
        'product_count': product_count,
    }


@public_shop_bp.get('/categories')
def categories():
    return jsonify({'categories': CATEGORIES})


@public_shop_bp.get('/home')
def shop_home():
    products = top_products(limit=12)
    salesmen = top_salesmen(limit=8)
    return jsonify({
        'top_products': [p.to_dict(with_salesman=True) for p in products],
        'top_salesmen': [_serialise_salesman_card(u) for u in salesmen],
        'categories': CATEGORIES,
    })


@public_shop_bp.get('/salesmen')
def list_salesmen():
    q_str = (request.args.get('q') or '').strip()
    suburb = (request.args.get('suburb') or '').strip()
    try:
        page = max(1, int(request.args.get('page') or 1))
    except ValueError:
        page = 1
    page_size = 24

    # Salesmen with at least one active product
    sm_ids_sub = (db.session.query(Product.salesman_user_id)
                  .filter(Product.status == 'active').distinct().subquery())
    q = (User.query
         .filter(User.is_salesman == True)  # noqa: E712
         .filter(User.status == 'active')
         .filter(User.id.in_(db.session.query(sm_ids_sub.c.salesman_user_id))))
    if suburb:
        q = q.filter(User.suburb.ilike(f'%{suburb}%'))
    if q_str:
        like = f'%{q_str}%'
        # Join salesman_profile for shop_name matching
        q = q.outerjoin(SalesmanProfile, SalesmanProfile.user_id == User.id) \
            .filter(or_(
                User.name.ilike(like),
                SalesmanProfile.shop_name.ilike(like),
            ))

    total = q.count()
    rows = q.order_by(User.created_at.asc()).limit(page_size).offset((page - 1) * page_size).all()

    return jsonify({
        'salesmen': [_serialise_salesman_card(u) for u in rows],
        'total': total,
        'page': page,
        'page_size': page_size,
    })


@public_shop_bp.get('/salesmen/<slug>')
def salesman_detail(slug):
    profile = SalesmanProfile.query.filter_by(shop_slug=slug).first()
    if not profile:
        return jsonify({'error': 'not_found', 'message': 'Shop not found.'}), 404
    user = profile.user
    if not user or user.status != 'active' or not user.is_salesman:
        return jsonify({'error': 'not_found', 'message': 'Shop not found.'}), 404

    products = (Product.query
                .filter(Product.salesman_user_id == user.id, Product.status == 'active')
                .order_by(Product.created_at.desc())
                .all())

    return jsonify({
        'salesman': {
            **_serialise_salesman_card(user),
            'pickup_delivery_policy': profile.pickup_delivery_policy,
            'phone': user.phone,
        },
        'products': [p.to_dict() for p in products],
    })


@public_shop_bp.get('/products')
def list_products():
    q_str = (request.args.get('q') or '').strip()
    category = (request.args.get('category') or '').strip()
    salesman_slug = (request.args.get('salesman_slug') or '').strip()
    try:
        page = max(1, int(request.args.get('page') or 1))
    except ValueError:
        page = 1
    page_size = 24

    try:
        min_price = Decimal(request.args.get('min_price')) if request.args.get('min_price') else None
        max_price = Decimal(request.args.get('max_price')) if request.args.get('max_price') else None
    except (InvalidOperation, ValueError):
        min_price = None
        max_price = None

    q = (Product.query
         .filter(Product.status == 'active')
         .join(User, User.id == Product.salesman_user_id)
         .filter(User.status == 'active'))
    if q_str:
        like = f'%{q_str}%'
        # Join SalesmanProfile for shop_name search
        q = q.outerjoin(SalesmanProfile, SalesmanProfile.user_id == User.id) \
            .filter(or_(
                Product.name.ilike(like),
                Product.description.ilike(like),
                SalesmanProfile.shop_name.ilike(like),
            ))
    if category:
        q = q.filter(Product.category == category)
    if salesman_slug:
        q = q.join(SalesmanProfile, SalesmanProfile.user_id == Product.salesman_user_id) \
             .filter(SalesmanProfile.shop_slug == salesman_slug)
    if min_price is not None:
        q = q.filter(Product.price_usd >= min_price)
    if max_price is not None:
        q = q.filter(Product.price_usd <= max_price)

    total = q.count()
    rows = q.order_by(Product.created_at.desc()) \
            .limit(page_size).offset((page - 1) * page_size).all()

    # Facets: counts by category over the filtered set (minus the category filter)
    facet_q = (Product.query
               .filter(Product.status == 'active')
               .join(User, User.id == Product.salesman_user_id)
               .filter(User.status == 'active'))
    facet_rows = db.session.query(Product.category, db.func.count(Product.id)) \
        .filter(Product.status == 'active') \
        .group_by(Product.category).all()
    facets = {'categories': [{'name': c, 'count': n} for (c, n) in facet_rows]}

    return jsonify({
        'products': [p.to_dict(with_salesman=True) for p in rows],
        'total': total,
        'page': page,
        'page_size': page_size,
        'facets': facets,
    })


@public_shop_bp.get('/products/<product_id>')
def product_detail(product_id):
    p = db.session.get(Product, product_id)
    if not p or p.status != 'active':
        # We allow viewing archived/draft only via direct admin; public 404.
        return jsonify({'error': 'not_found', 'message': 'Product not found.'}), 404
    return jsonify({
        'product': p.to_dict(with_salesman=True),
    })
