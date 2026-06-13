"""ZimHub Stage 4 — management CLI.

Usage:
    python manage.py db-init                          # create tables
    python manage.py seed                             # runs stage1 → … → stage5
    python manage.py seed --stage 1                   # only stage 1
    python manage.py seed --stage 2                   # only stage 2
    python manage.py seed --stage 3                   # only stage 3
    python manage.py seed --stage 4                   # only stage 4
    python manage.py reset                            # drop + recreate + reseed (destructive)
    python manage.py create-superadmin --email <e> --password <p> [--name <n>]
"""
import argparse
import os
import sys

# Don't start the APScheduler while running management commands.
os.environ['ZIMHUB_NO_SCHEDULER'] = '1'

from sqlalchemy import text

from app import create_app
from extensions import db
from app.models import User
from app.services import auth_service
from app.utils.passwords import hash_password


def _print_header(title: str):
    print()
    print('=' * 60)
    print(title)
    print('=' * 60)


def _ensure_postgres_extensions():
    """We use UUIDs but generate them in Python — no pgcrypto extension needed.
    This is kept as a hook in case Stage 2+ wants gen_random_uuid() at the DB.
    """
    pass


def cmd_db_init():
    """Create tables. Uses SQLAlchemy metadata directly for Stage 1 — simple and
    reliable for a fresh install. The alembic migration is included in the repo
    for future schema changes; if you want to use it instead, run:
        flask db upgrade
    instead of this command.
    """
    app = create_app()
    with app.app_context():
        _print_header('Initialising database')
        _ensure_postgres_extensions()
        db.create_all()
        # Stamp the alembic version so future `flask db upgrade` runs are no-ops
        # on a freshly create_all'd schema.
        try:
            from flask_migrate import stamp
            stamp(revision='head')
            print('• Tables created.')
            print('• Alembic version stamped to head.')
        except Exception as e:
            print(f'• Tables created. (Alembic stamp skipped: {e})')
        print('Done.')


def cmd_seed(stage=None):
    app = create_app()
    with app.app_context():
        if stage in (None, 1):
            _print_header('Running Stage 1 seed')
            from seeds.stage1_seed import run as run_stage1
            run_stage1()
        if stage in (None, 2):
            _print_header('Running Stage 2 seed')
            from seeds.stage2_seed import run as run_stage2
            run_stage2()
        if stage in (None, 3):
            _print_header('Running Stage 3 seed')
            from seeds.stage3_seed import run as run_stage3
            run_stage3()
        if stage in (None, 4):
            _print_header('Running Stage 4 seed')
            from seeds.stage4_seed import run as run_stage4
            run_stage4()
        if stage in (None, 5):
            _print_header('Running Stage 5 seed')
            from seeds.stage5_seed import run as run_stage5
            run_stage5()


def cmd_reset():
    app = create_app()
    print('⚠️  This will DROP ALL TABLES and reseed. Type "yes" to continue: ', end='', flush=True)
    confirmation = input().strip().lower()
    if confirmation != 'yes':
        print('Aborted.')
        return
    with app.app_context():
        _print_header('Resetting database')
        # NOTE: several Stage 1–4 tables have mutually-circular FKs (purchases
        # ↔ disputes, bookings ↔ booking_disputes). SQLAlchemy's drop_all()
        # cannot topologically sort those on a *populated* DB and raises
        # CircularDependencyError, so a clean schema drop is the reliable reset
        # (works whether the DB is empty or already seeded). create_all() below
        # rebuilds everything, breaking the cycle with post-create ALTERs.
        db.session.remove()
        db.engine.dispose()
        with db.engine.begin() as conn:
            conn.execute(text('DROP SCHEMA public CASCADE'))
            conn.execute(text('CREATE SCHEMA public'))
        print('• Schema dropped and recreated (clean).')
        db.create_all()
        print('• Tables re-created.')
        try:
            from flask_migrate import stamp
            stamp(revision='head')
            print('• Alembic version stamped to head.')
        except Exception as e:
            print(f'• Alembic stamp skipped: {e}')
        from seeds.stage1_seed import run as run_stage1
        run_stage1()
        from seeds.stage2_seed import run as run_stage2
        run_stage2()
        from seeds.stage3_seed import run as run_stage3
        run_stage3()
        from seeds.stage4_seed import run as run_stage4
        run_stage4()
        from seeds.stage5_seed import run as run_stage5
        run_stage5()


def cmd_create_superadmin(email: str, password: str, name: str = 'ZimHub Admin', phone: str = '+263772000000'):
    app = create_app()
    with app.app_context():
        existing = User.query.filter_by(email=email.strip().lower()).first()
        if existing:
            print(f'• User {email} already exists. Setting is_super_admin = True.')
            existing.is_super_admin = True
            existing.password_hash = hash_password(password)
            db.session.commit()
            print('✓ Done.')
            return

        u = User(
            email=email.strip().lower(),
            phone=phone,
            password_hash=hash_password(password),
            name=name,
            suburb=None,
            city='Bulawayo',
            is_buyer=True,
            is_super_admin=True,
            password_reset_required=False,
        )
        db.session.add(u)
        db.session.commit()
        print(f'✓ Super admin created: {email}')


def main():
    parser = argparse.ArgumentParser(description='ZimHub Stage 2 management CLI')
    sub = parser.add_subparsers(dest='cmd', required=True)

    sub.add_parser('db-init', help='Create tables.')
    p_seed = sub.add_parser('seed', help='Run seed runners (Stage 1 → … → Stage 5 by default).')
    p_seed.add_argument('--stage', type=int, choices=[1, 2, 3, 4, 5], default=None,
                        help='Run only this stage; default runs all stages.')
    sub.add_parser('reset', help='Drop + recreate + reseed (destructive).')

    p_sa = sub.add_parser('create-superadmin', help='Create or promote a super admin user.')
    p_sa.add_argument('--email', required=True)
    p_sa.add_argument('--password', required=True)
    p_sa.add_argument('--name', default='ZimHub Admin')
    p_sa.add_argument('--phone', default='+263772000000')

    args = parser.parse_args()

    if args.cmd == 'db-init':
        cmd_db_init()
    elif args.cmd == 'seed':
        cmd_seed(stage=args.stage)
    elif args.cmd == 'reset':
        cmd_reset()
    elif args.cmd == 'create-superadmin':
        cmd_create_superadmin(args.email, args.password, args.name, args.phone)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
