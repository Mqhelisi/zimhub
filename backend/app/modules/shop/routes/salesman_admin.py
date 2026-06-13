"""/api/salesman/* — Salesman admin routes per STAGE_2_SPEC.md §5.2.3."""
import logging
from datetime import datetime, timezone, timedelta
from decimal import Decimal, InvalidOperation

from flask import Blueprint, request, jsonify
from sqlalchemy import or_, func
from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from app.models import SalesmanProfile, User
from app.utils.decorators import require_auth
from app.utils.errors import (
    error_response, validation_failed, forbidden, not_found, conflict,
)
from app.utils.slugify import slugify_unique

from ..models import Product
from ..uploads import upload_image_file, UploadError
from .. import CATEGORIES
from app.modules.purchase_interface.models import Purchase, PurchaseEvent


log = logging.getLogger('zimhub.shop.salesman_admin')

salesman_admin_bp = Blueprint('shop_salesman_admin', __name__, url_prefix='/api/salesman')


def _require_salesman(user):
    if not user.is_salesman:
        return forbidden('You need a Salesman capability to access this.')
    return None


# ----------------------------------------------------------------------
# /api/salesman/profile
# ----------------------------------------------------------------------
@salesman_admin_bp.get('/profile')
@require_auth
def get_profile(user):
    gate = _require_salesman(user)
    if gate is not None:
        return gate
    # Auto-vivify a profile shell if missing (defensive — should exist via approval).
    profile = user.salesman_profile
    if not profile:
        slug = slugify_unique(
            user.name,
            exists_fn=lambda s: db.session.query(SalesmanProfile.user_id).filter_by(shop_slug=s).first() is not None,
        )
        profile = SalesmanProfile(user_id=user.id, shop_name=user.name, shop_slug=slug)
        db.session.add(profile)
        db.session.commit()
    return jsonify({'profile': profile.to_dict()})


@salesman_admin_bp.put('/profile')
@require_auth
def update_profile(user):
    gate = _require_salesman(user)
    if gate is not None:
        return gate
    data = request.get_json(silent=True) or {}
    profile = user.salesman_profile
    if not profile:
        return not_found('Salesman profile missing.')

    # shop_name is editable but slug is locked after first save (per spec §6.5).
    if 'shop_name' in data and data['shop_name']:
        new_name = str(data['shop_name']).strip()[:200]
        if new_name:
            profile.shop_name = new_name
    if 'bio' in data:
        profile.bio = (data.get('bio') or '').strip() or None
    if 'photo_url' in data:
        profile.photo_url = (data.get('photo_url') or '').strip() or None
    if 'banner_url' in data:
        profile.banner_url = (data.get('banner_url') or '').strip() or None
    if 'pickup_delivery_policy' in data:
        profile.pickup_delivery_policy = (data.get('pickup_delivery_policy') or '').strip() or None
    db.session.commit()
    return jsonify({'profile': profile.to_dict()})


# ----------------------------------------------------------------------
# /api/salesman/products
# ----------------------------------------------------------------------
@salesman_admin_bp.get('/products')
@require_auth
def list_products(user):
    gate = _require_salesman(user)
    if gate is not None:
        return gate
    status = (request.args.get('status') or '').strip().lower()
    q_str = (request.args.get('q') or '').strip()
    category = (request.args.get('category') or '').strip()
    try:
        page = max(1, int(request.args.get('page') or 1))
    except ValueError:
        page = 1
    page_size = 24

    query = Product.query.filter(Product.salesman_user_id == user.id)
    if status in ('active', 'draft', 'archived'):
        query = query.filter(Product.status == status)
    if category:
        query = query.filter(Product.category == category)
    if q_str:
        like = f'%{q_str}%'
        query = query.filter(or_(Product.name.ilike(like), Product.description.ilike(like)))

    total = query.count()
    rows = (query.order_by(Product.created_at.desc())
                 .limit(page_size).offset((page - 1) * page_size).all())
    return jsonify({
        'products': [p.to_dict() for p in rows],
        'total': total,
        'page': page,
        'page_size': page_size,
    })


def _parse_price(v):
    try:
        d = Decimal(str(v))
    except (InvalidOperation, TypeError):
        raise ValueError('price_usd must be a valid amount.')
    if d < 0:
        raise ValueError('price_usd must be >= 0.')
    return d.quantize(Decimal('0.01'))


def _parse_stock(v):
    try:
        i = int(v)
    except (ValueError, TypeError):
        raise ValueError('stock_quantity must be an integer.')
    if i < 0:
        raise ValueError('stock_quantity must be >= 0.')
    return i


@salesman_admin_bp.post('/products')
@require_auth
def create_product(user):
    gate = _require_salesman(user)
    if gate is not None:
        return gate
    data = request.get_json(silent=True) or {}
    field_errors = {}

    name = (data.get('name') or '').strip()
    description = (data.get('description') or '').strip()
    category = (data.get('category') or '').strip()
    status = (data.get('status') or 'active').strip().lower()
    photos = data.get('photos') or []

    if not name:
        field_errors['name'] = 'Required.'
    if not description:
        field_errors['description'] = 'Required.'
    if not category or category not in CATEGORIES:
        field_errors['category'] = f'Must be one of: {", ".join(CATEGORIES)}.'
    if status not in ('active', 'draft', 'archived'):
        field_errors['status'] = 'Must be active, draft, or archived.'
    if not isinstance(photos, list):
        field_errors['photos'] = 'Must be a list of image URLs.'
    if status == 'active' and len(photos or []) < 1:
        field_errors['photos'] = 'At least one photo is required for active products.'

    try:
        price = _parse_price(data.get('price_usd'))
    except ValueError as e:
        field_errors['price_usd'] = str(e)
    try:
        stock = _parse_stock(data.get('stock_quantity', 0))
    except ValueError as e:
        field_errors['stock_quantity'] = str(e)

    if field_errors:
        return validation_failed('Some fields are invalid.', field_errors=field_errors)

    p = Product(
        salesman_user_id=user.id,
        name=name[:200],
        description=description,
        category=category,
        price_usd=price,
        stock_quantity=stock,
        photos=list(photos),
        status=status,
    )
    db.session.add(p)
    db.session.commit()
    return jsonify({'product': p.to_dict()}), 201


@salesman_admin_bp.get('/products/<product_id>')
@require_auth
def get_product(user, product_id):
    gate = _require_salesman(user)
    if gate is not None:
        return gate
    p = db.session.get(Product, product_id)
    if not p or str(p.salesman_user_id) != str(user.id):
        return not_found('Product not found.')
    return jsonify({'product': p.to_dict()})


@salesman_admin_bp.put('/products/<product_id>')
@require_auth
def update_product(user, product_id):
    gate = _require_salesman(user)
    if gate is not None:
        return gate
    p = db.session.get(Product, product_id)
    if not p or str(p.salesman_user_id) != str(user.id):
        return not_found('Product not found.')

    data = request.get_json(silent=True) or {}
    field_errors = {}

    if 'name' in data:
        nm = (data.get('name') or '').strip()
        if not nm:
            field_errors['name'] = 'Required.'
        else:
            p.name = nm[:200]
    if 'description' in data:
        de = (data.get('description') or '').strip()
        if not de:
            field_errors['description'] = 'Required.'
        else:
            p.description = de
    if 'category' in data:
        cat = (data.get('category') or '').strip()
        if cat not in CATEGORIES:
            field_errors['category'] = f'Must be one of: {", ".join(CATEGORIES)}.'
        else:
            p.category = cat
    if 'photos' in data:
        ph = data.get('photos') or []
        if not isinstance(ph, list):
            field_errors['photos'] = 'Must be a list.'
        else:
            p.photos = list(ph)
    if 'status' in data:
        st = (data.get('status') or '').strip().lower()
        if st not in ('active', 'draft', 'archived'):
            field_errors['status'] = 'Must be active, draft, or archived.'
        else:
            p.status = st
    if 'price_usd' in data:
        try:
            new_price = _parse_price(data.get('price_usd'))
        except ValueError as e:
            field_errors['price_usd'] = str(e)
        else:
            # Block price edits while stock_held > 0 (in-flight Purchases).
            if (p.stock_held or 0) > 0 and Decimal(str(new_price)) != Decimal(str(p.price_usd)):
                return conflict(
                    'Cannot change price while there are in-flight purchases. '
                    'Wait until pending payments are confirmed or cancelled.'
                )
            p.price_usd = new_price
    if 'stock_quantity' in data:
        try:
            new_stock = _parse_stock(data.get('stock_quantity'))
        except ValueError as e:
            field_errors['stock_quantity'] = str(e)
        else:
            reserved = (p.stock_held or 0) + (p.stock_sold or 0)
            if new_stock < reserved:
                field_errors['stock_quantity'] = (
                    f'Cannot be less than reserved + sold ({reserved}).'
                )
            else:
                p.stock_quantity = new_stock

    if field_errors:
        return validation_failed('Some fields are invalid.', field_errors=field_errors)

    # If active but no photos, refuse.
    if p.status == 'active' and not (p.photos or []):
        return validation_failed(
            'At least one photo is required for active products.',
            field_errors={'photos': 'At least one photo is required for active products.'},
        )

    db.session.commit()
    return jsonify({'product': p.to_dict()})


@salesman_admin_bp.delete('/products/<product_id>')
@require_auth
def delete_product(user, product_id):
    gate = _require_salesman(user)
    if gate is not None:
        return gate
    p = db.session.get(Product, product_id)
    if not p or str(p.salesman_user_id) != str(user.id):
        return not_found('Product not found.')

    # Hard-delete only if never referenced by a Purchase. Otherwise soft-archive.
    referenced = db.session.query(Purchase.id).filter(
        Purchase.listing_type == 'product',
    ).filter(
        Purchase.listing_id == p.id,
    ).first() is not None
    if referenced or (p.stock_sold or 0) > 0 or (p.stock_held or 0) > 0:
        p.status = 'archived'
        db.session.commit()
        return jsonify({'ok': True, 'soft_deleted': True})

    db.session.delete(p)
    db.session.commit()
    return jsonify({'ok': True})


# ----------------------------------------------------------------------
# Uploads
# ----------------------------------------------------------------------
@salesman_admin_bp.post('/uploads/image')
@require_auth
def upload_image(user):
    gate = _require_salesman(user)
    if gate is not None:
        return gate
    fs = request.files.get('file')
    if not fs:
        return validation_failed('file is required (multipart upload).')
    try:
        url = upload_image_file(fs)
    except UploadError as e:
        return error_response(e.code, e.message, e.status)
    except Exception:
        log.exception('Upload failed')
        return error_response('server_error', 'Could not upload image.', 500)
    return jsonify({'url': url})


# ----------------------------------------------------------------------
# Dashboard
# ----------------------------------------------------------------------
@salesman_admin_bp.get('/dashboard')
@require_auth
def dashboard(user):
    gate = _require_salesman(user)
    if gate is not None:
        return gate
    now = datetime.now(timezone.utc)
    day_start = now - timedelta(hours=24)
    thirty_d = now - timedelta(days=30)
    low_threshold = 3  # mirrors LOW_STOCK_THRESHOLD; could read from host.config

    pending_today = (Purchase.query
        .filter(Purchase.seller_id == user.id, Purchase.status == 'awaiting_payment')
        .filter(Purchase.created_at >= day_start)
        .count())
    completed_today = (Purchase.query
        .filter(Purchase.seller_id == user.id, Purchase.status == 'completed')
        .filter(Purchase.completed_at >= day_start)
        .count())
    low_stock = (Product.query
        .filter(Product.salesman_user_id == user.id, Product.status == 'active')
        .all())
    low_stock_count = sum(1 for p in low_stock if p.available < low_threshold and p.available >= 0)

    completed_rows = (Purchase.query
        .filter(Purchase.seller_id == user.id, Purchase.status == 'completed')
        .filter(Purchase.completed_at >= thirty_d)
        .all())
    revenue_30d = sum((Decimal(str(p.total_usd or '0')) for p in completed_rows), Decimal('0'))

    # Recent activity (events scoped to this salesman's purchases)
    recent_events = (db.session.query(PurchaseEvent, Purchase)
        .join(Purchase, PurchaseEvent.purchase_id == Purchase.id)
        .filter(Purchase.seller_id == user.id)
        .order_by(PurchaseEvent.created_at.desc())
        .limit(10).all())
    recent = []
    for ev, p in recent_events:
        recent.append({
            'purchase_id': str(p.id),
            'from_status': ev.from_status,
            'to_status': ev.to_status,
            'actor_role': ev.actor_role,
            'note': ev.note,
            'created_at': ev.created_at.isoformat() if ev.created_at else None,
            'total_usd': str(p.total_usd),
            'quantity': p.quantity,
        })

    return jsonify({
        'stats': {
            'today_pending_payments': pending_today,
            'today_completed': completed_today,
            'low_stock_count': low_stock_count,
            'revenue_30d_usd': str(revenue_30d.quantize(Decimal('0.01'))),
        },
        'recent_purchases': recent,
    })


# ----------------------------------------------------------------------
# Categories enum (handy for the editor dropdown)
# ----------------------------------------------------------------------
@salesman_admin_bp.get('/categories')
@require_auth
def list_categories(user):
    return jsonify({'categories': CATEGORIES})
