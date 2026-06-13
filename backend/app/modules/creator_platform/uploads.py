"""CreatorPlatform uploads — Stage 5 §5.4.

Images (cover art, hero, profile, gallery) reuse Stage 2's shop image helper.
Audio is new: MP3/AAC, default 20MB, Cloudinary (resource_type='video' is how
Cloudinary stores audio) in prod, local-filesystem fallback in dev. Dev files
land in backend/local_uploads/ and are served by the existing static route with
HTTP range support, so the player's seek bar works locally.
"""
import os
from pathlib import Path
from uuid import uuid4

from flask import current_app, request

# Reuse the proven image pipeline verbatim for all images.
from app.modules.shop.uploads import upload_image_file, UploadError  # noqa: F401

AUDIO_MIMES = {'audio/mpeg', 'audio/mp3', 'audio/mp4', 'audio/aac', 'audio/x-m4a'}
AUDIO_EXTS = {'.mp3', '.m4a', '.aac', '.mp4'}
AUDIO_MAX_BYTES = 20 * 1024 * 1024  # 20MB (CreatorPlatform §5.2)


def _cloudinary_configured() -> bool:
    return bool(
        os.environ.get('CLOUDINARY_CLOUD_NAME')
        and os.environ.get('CLOUDINARY_API_KEY')
        and os.environ.get('CLOUDINARY_API_SECRET')
    )


def _local_uploads_dir() -> Path:
    backend_dir = Path(current_app.root_path).parent
    p = backend_dir / 'local_uploads'
    p.mkdir(parents=True, exist_ok=True)
    return p


def upload_audio_file(fs) -> tuple[str, str | None]:
    """Take a Werkzeug FileStorage, return (public_url, cloudinary_public_id).

    Raises UploadError on validation failure.
    """
    if not fs or not getattr(fs, 'filename', None):
        raise UploadError('validation_failed', 'No audio file provided.')

    mt = (fs.mimetype or '').lower()
    if mt and mt not in AUDIO_MIMES:
        raise UploadError('validation_failed', f'Unsupported audio type: {mt}.')

    ext = ''
    if '.' in fs.filename:
        ext = '.' + fs.filename.rsplit('.', 1)[-1].lower()
    if ext and ext not in AUDIO_EXTS:
        raise UploadError('validation_failed', f'Unsupported audio extension: {ext}.')
    if not ext:
        ext = '.mp3'

    data = fs.read()
    if not data:
        raise UploadError('validation_failed', 'Audio file is empty.')
    if len(data) > AUDIO_MAX_BYTES:
        raise UploadError('validation_failed',
                          f'Audio too large ({len(data)} bytes). Max 20MB.')

    if _cloudinary_configured():
        try:
            import cloudinary
            import cloudinary.uploader
            cloudinary.config(
                cloud_name=os.environ['CLOUDINARY_CLOUD_NAME'],
                api_key=os.environ['CLOUDINARY_API_KEY'],
                api_secret=os.environ['CLOUDINARY_API_SECRET'],
                secure=True,
            )
            # Cloudinary stores audio under resource_type='video'.
            result = cloudinary.uploader.upload(
                data, folder='zimhub/creators/audio', resource_type='video',
            )
            return (result.get('secure_url') or result.get('url'),
                    result.get('public_id'))
        except ImportError:
            current_app.logger.warning(
                'cloudinary present but package missing; falling back to local audio.'
            )
        except Exception as e:
            current_app.logger.exception('Cloudinary audio upload failed; local fallback: %s', e)

    # Local-filesystem fallback (served with range support — see static route).
    name = f"{uuid4().hex}{ext}"
    dest = _local_uploads_dir() / name
    dest.write_bytes(data)
    base = (request.host_url or '').rstrip('/')
    return f"{base}/local_uploads/{name}", None
