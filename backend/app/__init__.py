"""Flask app factory. Per spec §3."""
import logging
import sys

from flask import Flask, jsonify

from config import Config
from extensions import db, migrate, jwt, cors


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # ----- Logging: stdout, INFO by default. ----------------------------------
    _configure_logging(app)

    # ----- Extensions ---------------------------------------------------------
    db.init_app(app)
    # Importing the models package registers them with SQLAlchemy so Alembic
    # autogenerate sees them. Without this, migrations would be empty.
    from app import models  # noqa: F401
    migrate.init_app(app, db)
    jwt.init_app(app)
    cors.init_app(
        app,
        resources={r"/api/*": {"origins": app.config['CORS_ORIGINS']}},
        supports_credentials=True,
    )

    # ----- JWT error handlers — return JSON, not HTML -------------------------
    @jwt.unauthorized_loader
    def _unauth(reason):
        return jsonify({'error': 'unauthenticated', 'message': 'You must be signed in.'}), 401

    @jwt.invalid_token_loader
    def _invalid(reason):
        return jsonify({'error': 'unauthenticated', 'message': 'Your session is invalid.'}), 401

    @jwt.expired_token_loader
    def _expired(jwt_header, jwt_payload):
        return jsonify({'error': 'unauthenticated', 'message': 'Your session has expired.'}), 401

    # ----- Blueprints ---------------------------------------------------------
    from app.routes.auth import auth_bp
    from app.routes.signup_requests import signup_bp
    from app.routes.super_users import super_users_bp
    from app.routes.notifications import notifications_bp
    from app.routes.system import system_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(signup_bp)
    app.register_blueprint(super_users_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(system_bp)

    # ----- Stage 2 modules ----------------------------------------------------
    from app.modules.purchase_interface.routes import purchases_bp, disputes_bp
    from app.modules.shop.routes import salesman_admin_bp, public_shop_bp
    app.register_blueprint(purchases_bp)
    app.register_blueprint(disputes_bp)
    app.register_blueprint(salesman_admin_bp)
    app.register_blueprint(public_shop_bp)

    # Register the ProductHandler with the PurchaseInterface registry.
    from app.modules.shop import register_shop_module
    register_shop_module()

    # ----- Stage 3 modules ----------------------------------------------------
    from app.modules.ticket_generator.routes import (
        promoter_admin_bp as tg_promoter_admin_bp,
        public_events_bp as tg_public_events_bp,
        tickets_bp as tg_tickets_bp,
        gate_bp as tg_gate_bp,
    )
    from app.modules.events_section.routes import (
        promoter_section_bp,
        public_events_feed_bp,
    )
    # Public unified feed registers BEFORE TG's by-tg list so /api/events
    # resolves to the unified feed. /api/events/:id lives on TG. /api/promoter/*
    # has separate blueprint names so flask doesn't see a conflict —
    # the URL paths are distinct (TG: events/ticket-types/gatemen/attendees;
    # events_section: profile/dashboard/events/flyer/uploads/etc).
    app.register_blueprint(public_events_feed_bp)
    app.register_blueprint(tg_public_events_bp)
    app.register_blueprint(tg_promoter_admin_bp)
    app.register_blueprint(promoter_section_bp)
    app.register_blueprint(tg_tickets_bp)
    app.register_blueprint(tg_gate_bp)

    # Register the TicketHandler with the PurchaseInterface registry.
    from app.modules.ticket_generator import register_ticket_generator_module
    register_ticket_generator_module()

    # ----- Stage 4 modules ----------------------------------------------------
    # BookingInterface — a PARALLEL system to PurchaseInterface (separate
    # tables, state machine, registry, dispute desk; no money movement).
    from app.modules.booking_interface.routes import (
        bookings_bp, availability_bp, booking_disputes_bp,
    )
    from app.modules.services_section.routes import (
        provider_admin_bp, public_services_bp,
    )
    app.register_blueprint(bookings_bp)
    app.register_blueprint(availability_bp)
    app.register_blueprint(booking_disputes_bp)
    app.register_blueprint(provider_admin_bp)
    app.register_blueprint(public_services_bp)

    # Register the 'service_provider' handler against BookingInterface's
    # separate registry (Stage 4 spec §5.1 registry initialisation).
    from app.modules.services_section import register_services_module
    register_services_module()

    # ----- Stage 5 module — CreatorPlatform (Creators section) ---------------
    # Mounted LAST so its any-of event_ticket capability re-assertion wins over
    # TicketGenerator's boot-time 'is_promoter' registration (Stage 5 §5.3).
    from app.modules.creator_platform.routes import (
        public_creators_bp,
        creator_studio_bp,
        music_bp,
        gallery_bp,
        creator_events_bp,
    )
    app.register_blueprint(public_creators_bp)
    app.register_blueprint(creator_studio_bp)
    app.register_blueprint(music_bp)
    app.register_blueprint(gallery_bp)
    app.register_blueprint(creator_events_bp)

    from app.modules.creator_platform import register_creator_platform_module
    register_creator_platform_module()

    # ----- Local uploads static route (dev fallback for image uploads) --------
    import os
    from flask import send_from_directory
    local_uploads_dir = os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', 'local_uploads')
    )
    os.makedirs(local_uploads_dir, exist_ok=True)

    @app.get('/local_uploads/<path:filename>')
    def _local_uploads(filename):
        # conditional=True enables HTTP range requests so the audio player's
        # seek bar works against locally-served seed/uploaded audio (Stage 5 §5.4).
        return send_from_directory(local_uploads_dir, filename, conditional=True)

    # ----- Background scheduler (Stage 2) -------------------------------------
    # Guarded so migrations and seed runs don't spawn a scheduler thread.
    enable_sched = str(os.environ.get('ENABLE_SCHEDULER', 'true')).lower() in ('1', 'true', 'yes', 'on')
    if enable_sched and not app.config.get('TESTING') and not os.environ.get('ZIMHUB_NO_SCHEDULER'):
        try:
            from app.jobs.scheduler import start_scheduler
            start_scheduler(app)
        except Exception as e:
            app.logger.warning('Could not start scheduler: %s', e)

    # ----- Health check (handy for sanity) ------------------------------------
    @app.get('/api/health')
    def _health():
        return jsonify({'ok': True, 'app': 'zimhub-stage5'})

    # ----- Generic 404 / 500 for /api/* ---------------------------------------
    @app.errorhandler(404)
    def _not_found(e):
        return jsonify({'error': 'not_found', 'message': 'Not found.'}), 404

    @app.errorhandler(500)
    def _server_error(e):
        app.logger.exception('Unhandled server error')
        return jsonify({'error': 'server_error', 'message': 'Something went wrong on our side.'}), 500

    return app


def _configure_logging(app: Flask):
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(
        '[%(asctime)s] %(levelname)s %(name)s — %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    ))
    root = logging.getLogger()
    # Avoid double-handlers when reloader restarts.
    if not any(isinstance(h, logging.StreamHandler) for h in root.handlers):
        root.addHandler(handler)
    root.setLevel(logging.INFO)
    app.logger.setLevel(logging.INFO)
