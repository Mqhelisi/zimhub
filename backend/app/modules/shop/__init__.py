"""Shop module — Stage 2.

Owns:
  - the `products` table
  - the `ProductHandler` which plugs into PurchaseInterface as
    `listing_type='product'`
  - /api/salesman/* admin routes
  - /api/shop/* public routes
  - image upload endpoint (Cloudinary in prod, local fallback in dev)

Registration with PurchaseInterface happens via `register_shop_module()` which
the app factory calls at boot, after blueprints. We do NOT register at import
time because PurchaseInterface registry is initialised once at create_app().
"""
from app.modules.purchase_interface import register_purchasable
from .services.product_handler import ProductHandler

CATEGORIES = [
    'Phones & Accessories',
    'Clothing',
    'Footwear',
    'Beauty & Personal Care',
    'Home Goods',
    'Food & Groceries',
    'Electronics',
    'Books & Stationery',
    'Toys & Kids',
    'Other',
]


def register_shop_module():
    """Call from create_app() once.

    Registers the 'product' handler and adds the capability mapping into the
    host registry. Idempotent — safe to call twice (e.g. on Flask reloader).
    """
    from app.services.host import register_listing_type
    register_listing_type('product', 'is_salesman')
    register_purchasable('product', ProductHandler)
