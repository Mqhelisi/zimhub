"""Mock transport helpers — high-level email/SMS/WhatsApp message builders.

The plumbing (logging + writing mock_messages) lives in host.send(...). This file
just builds Stage-1 message bodies and calls host.send.
"""
from flask import current_app
from app.services import host


def _login_url() -> str:
    return current_app.config.get('FRONTEND_BASE_URL', 'http://localhost:5173') + '/login'


def dispatch_approval_credentials(*, recipient_email: str, recipient_phone: str,
                                  channels: list[str], full_name: str, category: str,
                                  temp_password: str):
    """Dispatch temp-password credentials to a newly-approved seller.
    Returns a list of MockMessage rows created.
    """
    login_url = _login_url()
    body_email = (
        f"Hi {full_name},\n\n"
        f"Welcome to ZimHub. Your application to sell as a {category} has been approved.\n\n"
        f"Sign in here: {login_url}\n"
        f"Email: {recipient_email}\n"
        f"Temporary password: {temp_password}\n\n"
        f"You'll be asked to set a new password on first sign-in.\n\n"
        f"— The ZimHub team"
    )
    body_short = (
        f"ZimHub: Welcome {full_name}. Your {category} application is approved. "
        f"Sign in at {login_url} with temp password: {temp_password}. "
        f"You'll be asked to change it on first sign-in."
    )

    sent = []
    if 'email' in channels:
        sent.append(host.send(
            channel='email',
            recipient=recipient_email,
            subject='ZimHub — your seller application is approved',
            body=body_email,
            payload={
                'template': 'seller_application_approved',
                'category': category,
                'temp_password': temp_password,
                'login_url': login_url,
            },
        ))
    if 'whatsapp' in channels:
        wa = host.whatsapp_link(recipient_phone, body_short)
        sent.append(host.send(
            channel='whatsapp',
            recipient=recipient_phone,
            subject=None,
            body=body_short,
            payload={
                'template': 'seller_application_approved',
                'category': category,
                'wa_link': wa,
                'temp_password': temp_password,
                'login_url': login_url,
            },
        ))
    if 'sms' in channels:
        sent.append(host.send(
            channel='sms',
            recipient=recipient_phone,
            subject=None,
            body=body_short,
            payload={
                'template': 'seller_application_approved',
                'temp_password': temp_password,
                'login_url': login_url,
            },
        ))
    return sent


def dispatch_rejection_email(*, recipient_email: str, full_name: str, category: str, reason: str):
    body = (
        f"Hi {full_name},\n\n"
        f"Thanks for applying to sell on ZimHub as a {category}.\n"
        f"We've reviewed your application carefully and unfortunately can't take it forward at this time.\n\n"
        f"Reason from the review team:\n{reason}\n\n"
        f"You're welcome to re-apply in future.\n\n"
        f"— The ZimHub team"
    )
    return host.send(
        channel='email',
        recipient=recipient_email,
        subject='ZimHub — your seller application',
        body=body,
        payload={
            'template': 'seller_application_rejected',
            'category': category,
            'reason': reason,
        },
    )


def dispatch_password_reset_email(*, recipient_email: str, full_name: str, token: str):
    base = current_app.config.get('FRONTEND_BASE_URL', 'http://localhost:5173')
    reset_url = f"{base}/password-reset/{token}"
    body = (
        f"Hi {full_name},\n\n"
        f"Someone asked to reset the password on your ZimHub account.\n"
        f"If that was you, follow this link within the next hour:\n\n"
        f"{reset_url}\n\n"
        f"If it wasn't you, ignore this message.\n\n"
        f"— The ZimHub team"
    )
    return host.send(
        channel='email',
        recipient=recipient_email,
        subject='ZimHub — password reset',
        body=body,
        payload={
            'template': 'password_reset',
            'reset_url': reset_url,
            'token': str(token),
        },
    )


def dispatch_temp_password(*, recipient_email: str, recipient_phone: str,
                          channels: list[str], full_name: str, temp_password: str):
    """Used by the super admin password-reset action (not the user-initiated flow)."""
    login_url = _login_url()
    body_email = (
        f"Hi {full_name},\n\n"
        f"A ZimHub admin has reset your password.\n\n"
        f"Sign in: {login_url}\n"
        f"Email: {recipient_email}\n"
        f"Temporary password: {temp_password}\n\n"
        f"You'll be asked to set a new password on sign-in.\n\n"
        f"— The ZimHub team"
    )
    body_short = (
        f"ZimHub: an admin has reset your password. "
        f"Sign in at {login_url} with temp password: {temp_password}."
    )
    sent = []
    if 'email' in channels:
        sent.append(host.send(
            channel='email',
            recipient=recipient_email,
            subject='ZimHub — your password has been reset',
            body=body_email,
            payload={'template': 'admin_password_reset', 'temp_password': temp_password},
        ))
    if 'whatsapp' in channels:
        sent.append(host.send(
            channel='whatsapp',
            recipient=recipient_phone,
            subject=None,
            body=body_short,
            payload={
                'template': 'admin_password_reset',
                'wa_link': host.whatsapp_link(recipient_phone, body_short),
                'temp_password': temp_password,
            },
        ))
    if 'sms' in channels:
        sent.append(host.send(
            channel='sms',
            recipient=recipient_phone,
            subject=None,
            body=body_short,
            payload={'template': 'admin_password_reset', 'temp_password': temp_password},
        ))
    return sent
