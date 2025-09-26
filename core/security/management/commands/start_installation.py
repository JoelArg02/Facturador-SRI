from __future__ import annotations

import shutil
from pathlib import Path
from typing import List

from django.conf import settings
from django.core.management import BaseCommand

from core.security.management.install import (
    InstallationContext,
    apply_migrations,
    backfill_company_relations,
    confirm_execution,
    configure_groups_and_permissions,
    ensure_admin_user,
    ensure_dashboard_and_types,
    ensure_owner_subscription,
    ensure_subscription_modules,
    ensure_company_admin_module,
    generate_initial_migrations,
    maybe_start_dev_server,
    reset_database,
    seed_default_plans,
    seed_modules_from_json,
    validate_required_tables,
)


class Command(BaseCommand):
    """Reinicia la instalación y siembra datos iniciales."""

    help = (
        'Reinicia completamente la instalación: elimina DB SQLite y migraciones locales y vuelve a sembrar datos.'
    )

    local_app_labels: List[str] = ['dashboard', 'login', 'pos', 'report', 'security', 'user', 'subscription']

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            default=False,
            help='No solicitar confirmación interactiva (DANGER).',
        )
        parser.add_argument(
            '--no-seed',
            action='store_true',
            default=False,
            help='Solo recrea DB y migraciones, sin sembrar datos (dashboard, módulos, planes, etc.).',
        )
        parser.add_argument(
            '--no-serve',
            action='store_true',
            default=False,
            help='No iniciar el servidor de desarrollo al finalizar.',
        )
        parser.add_argument(
            '--host',
            default='0.0.0.0',
            help='Host a enlazar al iniciar el servidor (default 0.0.0.0).',
        )
        parser.add_argument(
            '--port',
            default='80',
            help='Puerto a usar al iniciar el servidor (default 80).',
        )

    def _purge_local_migrations(self, app_labels):
        """Elimina los archivos de migraciones (excepto __init__.py) para cada app local indicada."""

        removed_files = 0
        for app in app_labels:
            migrations_path = Path(settings.BASE_DIR) / 'core' / app / 'migrations'
            if not migrations_path.exists():
                continue
            for item in migrations_path.iterdir():
                if item.name == '__init__.py':
                    continue
                if item.is_file() and item.suffix == '.py':
                    try:
                        item.unlink()
                        removed_files += 1
                    except Exception:
                        pass
                elif item.is_dir() and item.name == '__pycache__':
                    shutil.rmtree(item, ignore_errors=True)
            for pyc in migrations_path.glob('*.pyc'):
                try:
                    pyc.unlink()
                except Exception:
                    pass
        return removed_files

    def _remove_sqlite_db(self):
        db_conf = settings.DATABASES.get('default', {})
        engine = db_conf.get('ENGINE', '')
        if 'sqlite' not in engine:
            self.stdout.write(
                self.style.WARNING(
                    'Base de datos no es SQLite; se omite borrado físico (para otros motores haga DROP manual).'
                )
            )
            return False
        db_path = Path(db_conf.get('NAME'))
        if db_path.exists():
            try:
                db_path.unlink()
                return True
            except Exception as exc:
                self.stdout.write(self.style.ERROR(f'No se pudo eliminar la DB SQLite: {exc}'))
                return False
        return False

    def handle(self, *args, **options):
        ctx = InstallationContext(self, options, self.local_app_labels)

        if not confirm_execution(ctx):
            return

        self.stdout.write(self.style.WARNING('==> Reinicio completo: borrando DB + migraciones'))

        reset_database(ctx)
        generate_initial_migrations(ctx)
        apply_migrations(ctx)

        if ctx.no_seed:
            self.stdout.write(self.style.SUCCESS('Reinicio completo SIN seed (--no-seed).'))
            return

        if not validate_required_tables(ctx):
            return

        ensure_dashboard_and_types(ctx)
        seed_modules_from_json(ctx)
        ensure_subscription_modules(ctx)
        ensure_company_admin_module(ctx)

        groups = configure_groups_and_permissions(ctx)
        ensure_admin_user(ctx, groups)

        seed_default_plans(ctx)
        ensure_owner_subscription(ctx)
        backfill_company_relations(ctx)

        self.stdout.write(self.style.SUCCESS('Instalación completa (reinicio + migraciones + seed).'))

        maybe_start_dev_server(ctx)
