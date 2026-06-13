"""CreatorPlatform blueprints — registered by create_app() via the module __init__."""
from .public_creators import public_creators_bp
from .creator_studio import creator_studio_bp
from .music import music_bp
from .gallery import gallery_bp
from .creator_events import creator_events_bp

__all__ = [
    'public_creators_bp',
    'creator_studio_bp',
    'music_bp',
    'gallery_bp',
    'creator_events_bp',
]
