"""APScheduler in-process job runner.

Powers PurchaseInterface sweepers:
  - expire awaiting_payment Purchases past hold_expires_at  (every 60s)
  - auto-complete awaiting_buyer_confirmation past auto_complete_at  (every 60s)

Started from create_app() behind ENABLE_SCHEDULER and not-TESTING guards so
migrations and seed runs don't spawn a scheduler thread.
"""
import logging
import atexit

from apscheduler.schedulers.background import BackgroundScheduler


log = logging.getLogger('zimhub.scheduler')

_scheduler = None


def _run_in_context(app, fn):
    def runner():
        with app.app_context():
            try:
                fn()
            except Exception:
                log.exception('Scheduled job failed: %s', getattr(fn, '__name__', '?'))
    return runner


def start_scheduler(app):
    """Idempotent — calling twice (e.g. Flask reloader) is a no-op."""
    global _scheduler
    if _scheduler is not None:
        return _scheduler

    from app.modules.purchase_interface.services import (
        expire_purchases_due, auto_complete_purchases_due,
    )
    # Stage 4 — BookingInterface sweepers share the same instance. Distinct
    # job ids; no scheduler collisions with PurchaseInterface's jobs.
    from app.modules.booking_interface.services import (
        expire_bookings_due, complete_bookings_due,
    )

    sched = BackgroundScheduler(timezone='UTC', daemon=True)
    sched.add_job(
        _run_in_context(app, expire_purchases_due),
        'interval', seconds=60, id='purchase_interface.expire',
        replace_existing=True, max_instances=1,
    )
    sched.add_job(
        _run_in_context(app, auto_complete_purchases_due),
        'interval', seconds=60, id='purchase_interface.auto_complete',
        replace_existing=True, max_instances=1,
    )
    sched.add_job(
        _run_in_context(app, expire_bookings_due),
        'interval', seconds=60, id='booking_interface.expire',
        replace_existing=True, max_instances=1,
    )
    sched.add_job(
        _run_in_context(app, complete_bookings_due),
        'interval', seconds=60, id='booking_interface.complete',
        replace_existing=True, max_instances=1,
    )
    sched.start()
    _scheduler = sched
    log.info('APScheduler started (PurchaseInterface + BookingInterface sweepers, 60s interval).')

    atexit.register(stop_scheduler)
    return sched


def stop_scheduler(*args, **kwargs):
    global _scheduler
    if _scheduler is None:
        return
    try:
        _scheduler.shutdown(wait=False)
    except Exception:
        pass
    _scheduler = None
