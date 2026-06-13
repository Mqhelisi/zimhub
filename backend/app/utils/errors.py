"""Standard error helpers — per spec §5.8.

All error responses: {error: 'code', message: 'Human-readable.'} with HTTP status.
"""
from flask import jsonify


def error_response(code: str, message: str, status: int, field_errors=None):
    body = {'error': code, 'message': message}
    if field_errors:
        body['field_errors'] = field_errors
    return jsonify(body), status


def unauthenticated(message='You must be signed in.'):
    return error_response('unauthenticated', message, 401)


def forbidden(message='You do not have access to this resource.'):
    return error_response('forbidden', message, 403)


def not_found(message='Not found.'):
    return error_response('not_found', message, 404)


def validation_failed(message='Some fields are invalid.', field_errors=None):
    return error_response('validation_failed', message, 400, field_errors=field_errors)


def conflict(message='Conflict.'):
    return error_response('conflict', message, 409)


def email_taken(message='An account with this email already exists.'):
    return error_response('email_taken', message, 409)
