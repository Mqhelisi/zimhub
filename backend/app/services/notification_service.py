"""Notification helpers — thin wrappers around host.notify with Stage-1 message
templates. Anything that wants to send a notification goes through here.
"""
from app.services import host
from app.models import User


def notify_super_admins(kind: str, title: str, body: str, metadata: dict = None):
    """Insert one notification per super admin."""
    admins = User.query.filter_by(is_super_admin=True).all()
    notifications = []
    for admin in admins:
        notifications.append(host.notify(admin.id, kind, title, body, metadata=metadata))
    return notifications


def notify_seller_application_approved(user: User, category: str, temp_password: str = None,
                                       login_url: str = None):
    body = (
        f"Welcome to ZimHub. Your application to sell as a {category} has been approved. "
        f"You can now access your {category} admin from your account."
    )
    metadata = {'category': category}
    if login_url:
        metadata['login_url'] = login_url
    return host.notify(
        user.id,
        'seller_application_approved',
        title=f'Approved: {category.title()} application',
        body=body,
        metadata=metadata,
    )


def notify_seller_application_rejected(user: User | None, category: str, reason: str,
                                       user_id=None):
    """Note: rejected applicants may not have a user account yet. If we can't find
    one (which is the normal case for rejection), we skip the on-platform
    notification and rely on the email/mock-message we dispatch separately.
    """
    target_id = user.id if user else user_id
    if target_id is None:
        return None
    body = f"Your application to sell as a {category} was not approved. Reason: {reason}"
    return host.notify(
        target_id,
        'seller_application_rejected',
        title=f'Application not approved',
        body=body,
        metadata={'category': category, 'reason': reason},
    )


def notify_password_reset_requested(user: User):
    return host.notify(
        user.id,
        'password_reset_requested',
        title='Password reset link sent',
        body='Check your inbox for the reset link. It expires in 1 hour.',
    )


def notify_new_signup_request(application):
    return notify_super_admins(
        kind='new_signup_request',
        title=f'New {application.category} application',
        body=f"{application.full_name} ({application.email}) applied to sell as {application.category}.",
        metadata={
            'request_id': str(application.id),
            'category': application.category,
            'email': application.email,
        },
    )
