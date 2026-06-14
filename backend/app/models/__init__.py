"""Importing models here ensures Flask-Migrate / Alembic detects all of them."""
from .user import User, PasswordResetToken
from .seller_signup_request import SellerSignupRequest
from .salesman_profile import SalesmanProfile
from .promoter_profile import PromoterProfile
from .provider_profile import ProviderProfile
from .creator_profile import CreatorProfile
from .notification import Notification
from .mock_message import MockMessage

# Stage 2 — module-owned models. Re-exported here so Alembic autogenerate picks
# them up via app.models metadata. The modules also own their own __init__'s.
from app.modules.purchase_interface.models import Purchase, PurchaseEvent, PurchaseDispute  # noqa: E402, F401
from app.modules.shop.models import Product  # noqa: E402, F401

# Stage 3 — TicketGenerator models.
from app.modules.ticket_generator.models import (  # noqa: E402, F401
    Event, TicketType, Ticket, Gateman, Checkin,
)

# Stage 4 — BookingInterface + Services section models.
from app.modules.booking_interface.models import (  # noqa: E402, F401
    BIProviderProfile, AvailabilityRule, AvailabilityBlock,
    Booking, BookingEvent, BookingDispute,
)
from app.modules.services_section.models import ProviderService  # noqa: E402, F401

# Stage 5 — CreatorPlatform models.
from app.modules.creator_platform.models import (  # noqa: E402, F401
    Track, PlayEvent, GalleryCollection, GalleryItem, CreatorEvent,
)

__all__ = [
    'User',
    'PasswordResetToken',
    'SellerSignupRequest',
    'SalesmanProfile',
    'PromoterProfile',
    'ProviderProfile',
    'CreatorProfile',
    'Notification',
    'MockMessage',
    'Purchase',
    'PurchaseEvent',
    'PurchaseDispute',
    'Product',
    'Event',
    'TicketType',
    'Ticket',
    'Gateman',
    'Checkin',
    'BIProviderProfile',
    'AvailabilityRule',
    'AvailabilityBlock',
    'Booking',
    'BookingEvent',
    'BookingDispute',
    'ProviderService',
    'Track',
    'PlayEvent',
    'GalleryCollection',
    'GalleryItem',
    'CreatorEvent',
]
