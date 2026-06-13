"""Image uploads — Cloudinary with local-filesystem fallback for dev.

Per STAGE_2_SPEC.md §5.5: production uses Cloudinary; dev falls back to
backend/local_uploads/<uuid>.<ext> served via /local_uploads/<filename>.

Limits: 5MB max per file, image MIME types only.
"""
import os
from pathlib import Path
from uuid import uuid4

from flask import current_app, request, url_for


ALLOWED_MIMES = {'image/jpeg', 'image/png', 'image/webp'}
ALLOWED_EXTS = {'.jpg', '.jpeg', '.png', '.webp'}
MAX_BYTES = 5 * 1024 * 1024  # 5MB


class UploadError(Exception):
    def __init__(self, code, message, status=400):
        self.code = code
        self.message = message
        self.status = status
        super().__init__(message)


def _cloudinary_configured() -> bool:
    return bool(
        os.environ.get('CLOUDINARY_CLOUD_NAME')
        and os.environ.get('CLOUDINARY_API_KEY')
        and os.environ.get('CLOUDINARY_API_SECRET')
    )


def _local_uploads_dir() -> Path:
    """Path is rooted at backend/ — same level as run.py."""
    # The Flask root is backend/app, so its parent is backend/.
    backend_dir = Path(current_app.root_path).parent
    p = backend_dir / 'local_uploads'
    p.mkdir(parents=True, exist_ok=True)
    return p


def upload_image_file(fs) -> str:
    """Take a Werkzeug FileStorage, return the public URL of the stored image.

    Raises UploadError on validation failure.
    """
    if not fs or not getattr(fs, 'filename', None):
        raise UploadError('validation_failed', 'No file provided.')

    # MIME check
    mt = (fs.mimetype or '').lower()
    if mt and mt not in ALLOWED_MIMES:
        raise UploadError('validation_failed', f'Unsupported file type: {mt}.')

    # Extension fallback
    ext = ''
    if '.' in fs.filename:
        ext = '.' + fs.filename.rsplit('.', 1)[-1].lower()
    if ext and ext not in ALLOWED_EXTS:
        raise UploadError('validation_failed', f'Unsupported file extension: {ext}.')
    if not ext:
        ext = '.jpg'

    # Size check — read once to bytes, peek length.
    data = fs.read()
    if not data:
        raise UploadError('validation_failed', 'File is empty.')
    if len(data) > MAX_BYTES:
        raise UploadError('validation_failed',
                          f'File too large ({len(data)} bytes). Max 5MB.')

    # Cloudinary path
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
            result = cloudinary.uploader.upload(
                data, folder='zimhub', resource_type='image',
            )
            return result.get('secure_url') or result.get('url')
        except ImportError:
            current_app.logger.warning(
                'cloudinary env vars present but cloudinary package not installed; falling back to local.'
            )
        except Exception as e:
            current_app.logger.exception('Cloudinary upload failed; falling back to local: %s', e)

    # Local-filesystem fallback
    name = f"{uuid4().hex}{ext}"
    dest = _local_uploads_dir() / name
    dest.write_bytes(data)
    # Build public URL via the static route registered in app/__init__.py.
    base = (request.host_url or '').rstrip('/')
    return f"{base}/local_uploads/{name}"
