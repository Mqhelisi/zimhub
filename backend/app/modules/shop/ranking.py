"""Ranking — Shop home page rankings, per STAGE_2_SPEC.md §5.2.5.

Both rankings are fresh per request — no caching this stage.
"""
from datetime import datetime, timezone, timedelta

from sqlalchemy import func, text

from extensions import db
from app.models import User
from app.modules.purchase_interface.models import Purchase

from .models import Product


def _thirty_days_ago():
    return datetime.now(timezone.utc) - timedelta(days=30)


def top_products(limit: int = 12):
    """Top active products by units sold in completed Purchases over the last 30d.

    Tiebreaker: total `stock_sold` (lifetime) desc, then created_at desc.
    """
    cutoff = _thirty_days_ago()

    # JSONB items array in domain_payload — extract sold quantities per product
    # using jsonb_array_elements. We compute the 30-day units per product from
    # the cross-joined elements, then left-join to the products table.
    sql = text("""
        WITH recent_items AS (
            SELECT
                (item->>'product_id')::uuid    AS product_id,
                (item->>'qty')::int             AS qty
            FROM purchases p
            CROSS JOIN LATERAL jsonb_array_elements(
                COALESCE(p.domain_payload->'items', '[]'::jsonb)
            ) AS item
            WHERE p.status = 'completed'
              AND p.listing_type = 'product'
              AND p.completed_at >= :cutoff
        ),
        units_30d AS (
            SELECT product_id, SUM(qty)::int AS units
            FROM recent_items
            GROUP BY product_id
        )
        SELECT pr.id
        FROM products pr
        LEFT JOIN units_30d u ON u.product_id = pr.id
        WHERE pr.status = 'active'
        ORDER BY COALESCE(u.units, 0) DESC, pr.stock_sold DESC, pr.created_at DESC
        LIMIT :limit
    """)
    rows = db.session.execute(sql, {'cutoff': cutoff, 'limit': limit}).fetchall()
    ids = [r[0] for r in rows]
    if not ids:
        return []
    # Preserve order using a dict
    products = Product.query.filter(Product.id.in_(ids)).all()
    by_id = {p.id: p for p in products}
    ordered = [by_id[i] for i in ids if i in by_id]
    return ordered


def top_salesmen(limit: int = 8):
    """Top active Salesmen by completed Purchase count over the last 30d.

    Only includes Salesmen with >= 1 active product. Tiebreaker: most active
    products listed.
    """
    cutoff = _thirty_days_ago()
    sql = text("""
        WITH sales_30d AS (
            SELECT seller_id, COUNT(*) AS purchases_count
            FROM purchases
            WHERE status = 'completed'
              AND listing_type = 'product'
              AND completed_at >= :cutoff
            GROUP BY seller_id
        ),
        active_counts AS (
            SELECT salesman_user_id, COUNT(*) AS product_count
            FROM products
            WHERE status = 'active'
            GROUP BY salesman_user_id
        )
        SELECT u.id
        FROM users u
        JOIN active_counts ac ON ac.salesman_user_id = u.id
        LEFT JOIN sales_30d s ON s.seller_id = u.id
        WHERE u.is_salesman = TRUE
          AND u.status = 'active'
        ORDER BY COALESCE(s.purchases_count, 0) DESC, ac.product_count DESC, u.created_at ASC
        LIMIT :limit
    """)
    rows = db.session.execute(sql, {'cutoff': cutoff, 'limit': limit}).fetchall()
    ids = [r[0] for r in rows]
    if not ids:
        return []
    users = User.query.filter(User.id.in_(ids)).all()
    by_id = {u.id: u for u in users}
    return [by_id[i] for i in ids if i in by_id]
