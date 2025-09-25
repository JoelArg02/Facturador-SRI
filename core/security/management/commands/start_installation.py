import json
import os
import shutil
from os.path import basename
from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.management import BaseCommand, call_command, CommandError
from django.db import connection

from core.security.models import *  # noqa
from core.subscription.models import Plan, Subscription  # noqa
from core.pos.models import Company  # noqa
from django.contrib.auth.models import Permission


class Command(BaseCommand):
    help = 'Reinicia completamente la instalación: elimina DB SQLite y migraciones locales y vuelve a sembrar datos.'

    # ------------------------ ARGUMENTOS ------------------------ #
    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', default=False,
                            help='No solicitar confirmación interactiva (DANGER).')
        parser.add_argument('--no-seed', action='store_true', default=False,
                            help='Solo recrea DB y migraciones, sin sembrar datos (dashboard, módulos, planes, etc.).')
        parser.add_argument('--no-serve', action='store_true', default=False,
                            help='No iniciar el servidor de desarrollo al finalizar.')
        parser.add_argument('--host', default='0.0.0.0', help='Host a enlazar al iniciar el servidor (default 0.0.0.0).')
        parser.add_argument('--port', default='80', help='Puerto a usar al iniciar el servidor (default 80).')

    # ------------------------ UTILIDADES ------------------------ #
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
            self.stdout.write(self.style.WARNING('Base de datos no es SQLite; se omite borrado físico (para otros motores haga DROP manual).'))
            return False
        db_path = Path(db_conf.get('NAME'))
        if db_path.exists():
            try:
                db_path.unlink()
                return True
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'No se pudo eliminar la DB SQLite: {e}'))
                return False
        return False

    def load_json_from_file(self, file):
        with open(f'{settings.BASE_DIR}/deploy/json/{file}', encoding='utf-8', mode='r') as wr:
            return json.loads(wr.read())

    # ------------------------ FLUJO PRINCIPAL ------------------------ #
    def handle(self, *args, **options):
        force = options.get('force')
        no_seed = options.get('no_seed')

        local_app_labels = ['dashboard', 'login', 'pos', 'report', 'security', 'user', 'subscription']

        if not force:
            self.stdout.write(self.style.WARNING('ADVERTENCIA: Este proceso eliminará TODAS las migraciones locales y el archivo de base de datos (si es SQLite).'))
            self.stdout.write(self.style.WARNING('Se regenerarán migraciones 0001_*.'))
            confirm = input('¿Desea continuar? (escriba SI para continuar): ')
            if confirm.strip().upper() != 'SI':
                self.stdout.write(self.style.ERROR('Operación cancelada.'))
                return

        self.stdout.write(self.style.WARNING('==> Reinicio completo: borrando DB + migraciones'))

        # 1. Eliminar DB (solo SQLite)
        if self._remove_sqlite_db():
            self.stdout.write(self.style.SUCCESS('Base de datos SQLite eliminada.'))
        else:
            self.stdout.write('No se eliminó archivo de base de datos (puede no existir o no es SQLite).')

        # 2. Eliminar migraciones
        removed = self._purge_local_migrations(local_app_labels)
        self.stdout.write(self.style.SUCCESS(f'Migraciones eliminadas: {removed}'))

        # 3. Generar migraciones iniciales
        try:
            self.stdout.write('Generando migraciones iniciales (0001_*)...')
            call_command('makemigrations', *local_app_labels, interactive=False, verbosity=0)
        except Exception as e:
            raise CommandError(f'Error al generar migraciones: {e}')

        # 4. Aplicar migraciones
        try:
            self.stdout.write('Aplicando migraciones...')
            call_command('migrate', interactive=False, verbosity=0)
        except Exception as e:
            raise CommandError(f'Error al aplicar migraciones: {e}')

        if no_seed:
            self.stdout.write(self.style.SUCCESS('Reinicio completo SIN seed (--no-seed).'))
            return

        # 5. Validar tabla base antes de seed
        existing_tables = set(connection.introspection.table_names())
        if 'security_dashboard' not in existing_tables:
            self.stdout.write(self.style.ERROR('No se creó la tabla security_dashboard. Abortando seed.'))
            return

        # 6. Sembrar dashboard y módulos solo si no existen (idempotente)
        if not Dashboard.objects.filter(name='INVOICE').exists():
            dashboard = Dashboard.objects.create(
                name='INVOICE',
                author='William Jair Dávila Vargas',
                footer_url='https://algorisoft.com',
                icon='fas fa-shopping-cart',
            )
            image_path = f'{settings.BASE_DIR}{settings.STATIC_URL}img/default/logo.png'
            if os.path.exists(image_path):
                dashboard.image.save(basename(image_path), content=File(open(image_path, 'rb')), save=False)
            dashboard.save()
            self.stdout.write(self.style.SUCCESS('Dashboard creado'))
        else:
            dashboard = Dashboard.objects.get(name='INVOICE')
            self.stdout.write('Dashboard existente detectado, se reutiliza.')

        def ensure_module_type(name: str, icon: str):
            obj, _ = ModuleType.objects.get_or_create(name=name, defaults={'icon': icon})
            return obj

        # Asegurar los tipos base (coinciden con JSON, idempotente)
        ensure_module_type('Seguridad', 'fas fa-lock')
        ensure_module_type('Bodega', 'fas fa-boxes')
        ensure_module_type('Administrativo', 'fas fa-hand-holding-usd')
        ensure_module_type('Facturación', 'fas fa-calculator')
        ensure_module_type('Reportes', 'fas fa-chart-pie')

        # 7. Sembrar módulos desde JSON si no existen
        module_json_path = Path(settings.BASE_DIR) / 'deploy' / 'json' / 'module.json'
        if module_json_path.exists():
            with open(module_json_path, encoding='utf-8') as f:
                for module_json in json.load(f):
                    if not Module.objects.filter(name=module_json['name']).exists():
                        permissions = module_json.pop('permissions')
                        moduletype_id = module_json.pop('moduletype_id')
                        moduletype = ModuleType.objects.filter(id=moduletype_id).first() if moduletype_id else None
                        module_json['module_type'] = moduletype
                        module = Module.objects.create(**module_json)
                        if permissions:
                            for codename in permissions:
                                perm = Permission.objects.filter(codename=codename).first()
                                if perm:
                                    module.permissions.add(perm)
                        self.stdout.write(self.style.SUCCESS(f"Módulo sembrado: {module.name}"))
        else:
            self.stdout.write(self.style.WARNING('Archivo module.json no encontrado, se omite seed de módulos predefinidos.'))

        # 8. Crear módulos Planes y Suscripciones (Administrativo) si no existen
        administrativo = ModuleType.objects.filter(name='Administrativo').first()
        plan_module, created_plan = Module.objects.get_or_create(
            name='Planes',
            defaults={
                'url': '/subscription/plan/',
                'icon': 'fas fa-layer-group',
                'description': 'Permite administrar los planes de suscripción',
                'module_type': administrativo
            }
        )
        if created_plan:
            for codename in ['view_plan', 'add_plan', 'change_plan', 'delete_plan']:
                perm = Permission.objects.filter(codename=codename).first()
                if perm:
                    plan_module.permissions.add(perm)
            self.stdout.write(self.style.SUCCESS('Módulo Planes creado'))
        else:
            self.stdout.write('Módulo Planes ya existía')

        subscription_module, created_sub = Module.objects.get_or_create(
            name='Suscripciones',
            defaults={
                'url': '/subscription/',
                'icon': 'fas fa-receipt',
                'description': 'Permite administrar las suscripciones de las compañías',
                'module_type': administrativo
            }
        )
        if created_sub:
            for codename in ['view_subscription', 'add_subscription', 'change_subscription', 'delete_subscription']:
                perm = Permission.objects.filter(codename=codename).first()
                if perm:
                    subscription_module.permissions.add(perm)
            self.stdout.write(self.style.SUCCESS('Módulo Suscripciones creado'))
        else:
            self.stdout.write('Módulo Suscripciones ya existía')

        # 9. Crear / asegurar grupos base y nuevos roles multi-tenant
        # Roles:
        # - Super Administrador (usa is_superuser, accede a todo)
        # - Administrador (interno full access sin marcar is_superuser)
        # - Cliente Propietario (dueño de la compañía: puede gestionar su empresa, usuarios de su tenant, catálogo y facturación)
        # - Operador Bodega (gestiona inventario / productos / compras, no configura compañía ni usuarios)
        # - Operador Venta (crea facturas y ve clientes, no cambia configuración ni usuarios)
        # - Cliente (perfil final para que un cliente final revise sus facturas / portal reducido)
        # - Consulta (solo lectura de reportes e inventario)
        admin_group, _ = Group.objects.get_or_create(name='Administrador')
        super_admin_group, _ = Group.objects.get_or_create(name='Super Administrador')
        owner_group, _ = Group.objects.get_or_create(name='Cliente Propietario')
        warehouse_group, _ = Group.objects.get_or_create(name='Operador Bodega')
        sales_group, _ = Group.objects.get_or_create(name='Operador Venta')
        client_group, _ = Group.objects.get_or_create(name='Cliente')
        readonly_group, _ = Group.objects.get_or_create(name='Consulta')

        # Map de permisos a excluir para roles restringidos (codenames startswith patterns)
        # Construiremos sets dinámicos según módulos.
        from django.contrib.auth.models import Permission as DjPermission

        all_modules = list(Module.objects.all())

        def link_module(group: Group, module: Module, include_perms=True):
            if not GroupModule.objects.filter(group=group, module=module).exists():
                GroupModule.objects.create(group=group, module=module)
            if include_perms:
                for perm in module.permissions.all():
                    group.permissions.add(perm)

        # 9.1 Super Administrador: asignar todos los módulos y permisos
        for m in all_modules:
            link_module(super_admin_group, m, include_perms=True)
        # 9.2 Administrador (excluye configuraciones SaaS globales)
        excluded_admin_names = {
            'Planes', 'Suscripciones', 'Conf. Dashboard', 'Tipos de Módulos', 'Módulos', 'Grupos'
        }
        for m in all_modules:
            if m.name not in excluded_admin_names:
                link_module(admin_group, m, include_perms=True)

        # 9.3 Cliente Propietario: todos los módulos excepto aquellos netamente administrativos globales si existieran
        excluded_owner_module_names = set([])  # placeholder para excluir futuros módulos globales (ej: Planes/Suscripciones si se desea limitar)
        for m in all_modules:
            if m.name in excluded_owner_module_names:
                continue
            link_module(owner_group, m, include_perms=True)

        # 9.4 Operador Bodega: módulos relacionados a inventario / productos / compras / proveedores
        warehouse_keywords = ['Producto', 'Product', 'Inventario', 'Inventory', 'Bodega', 'Compra', 'Purchase', 'Proveedor', 'Provider']
        for m in all_modules:
            if any(k.lower() in m.name.lower() for k in warehouse_keywords):
                link_module(warehouse_group, m, include_perms=True)

        # 9.5 Operador Venta: módulos de facturación, clientes, notas de crédito
        sales_keywords = ['Factura', 'Invoice', 'Cliente', 'Customer', 'Crédito', 'Credit']
        for m in all_modules:
            if any(k.lower() in m.name.lower() for k in sales_keywords):
                link_module(sales_group, m, include_perms=True)

        # 9.6 Cliente final (portal reducido)
        client_urls = ['/pos/customer/update/profile/', '/pos/invoice/customer/', '/pos/credit/note/customer/']
        for module in Module.objects.filter(url__in=client_urls + ['/user/update/password/']):
            link_module(client_group, module, include_perms=True)

        # 9.7 Consulta: asignar módulos pero solo permisos de view
        view_perms_cache = {}
        for m in all_modules:
            # asignar el módulo
            link_module(readonly_group, m, include_perms=False)
            for perm in m.permissions.all():
                if perm.codename.startswith('view_'):
                    readonly_group.permissions.add(perm)

        # Nota: no se eliminan permisos existentes para conservar personalizaciones previas.

        # 10. Crear usuario admin si no existe
        if not User.objects.filter(username='admin').exists():
            user = User.objects.create(
                username='admin',
                names='Administrador General',
                email='admin@example.com',
                is_active=True,
                is_superuser=True,
                is_staff=True
            )
            user.set_password('admin')
            user.save()
            user.groups.add(admin_group)
            self.stdout.write(self.style.SUCCESS('Usuario admin creado'))
        else:
            self.stdout.write('Usuario admin ya existe')

        # 11. Seed planes
        DEFAULT_PLANS = [
            {
                'name': 'Starter',
                'description': 'Plan básico para iniciar la facturación',
                'max_invoices': 100,
                'max_customers': 100,
                'max_products': 200,
                'price': 0,
                'period_days': 30,
            },
            {
                'name': 'Pro',
                'description': 'Plan profesional para pymes',
                'max_invoices': 1000,
                'max_customers': 3000,
                'max_products': 5000,
                'price': 29.90,
                'period_days': 30,
            },
            {
                'name': 'Enterprise',
                'description': 'Grandes volúmenes y soporte avanzado',
                'max_invoices': 100000,
                'max_customers': 200000,
                'max_products': 500000,
                'price': 199.00,
                'period_days': 30,
            },
        ]
        created_plans = 0
        for data in DEFAULT_PLANS:
            _, was_created = Plan.objects.get_or_create(name=data['name'], defaults=data)
            if was_created:
                created_plans += 1
        self.stdout.write(self.style.SUCCESS(f'Planes verificados/creados: {created_plans} nuevos'))

        # 12. Crear suscripción Starter por defecto si hay compañía y no tiene suscripción
        company = Company.objects.first()
        if company:
            starter = Plan.objects.filter(name='Starter').first()
            if starter and not company.subscriptions.exists():
                Subscription.objects.create(company=company, plan=starter)
                self.stdout.write(self.style.SUCCESS('Suscripción Starter creada para la compañía existente'))

        # 13. Backfill company en modelos que tengan el campo (si comando existe)
        try:
            call_command('backfill_company_fk', verbosity=0)
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'Backfill de compañía omitido: {e}'))

        self.stdout.write(self.style.SUCCESS('Instalación completa (reinicio + migraciones + seed).'))

        # 3. Sembrar dashboard y módulos solo si no existen (idempotente)
        if not Dashboard.objects.filter(name='INVOICE').exists():
            dashboard = Dashboard.objects.create(
                name='INVOICE',
                author='AllpaSoft',
                footer_url='https://allpasoft.com',
                icon='fas fa-shopping-cart',
            )
            image_path = f'{settings.BASE_DIR}{settings.STATIC_URL}img/default/logo.png'
            if os.path.exists(image_path):
                dashboard.image.save(basename(image_path), content=File(open(image_path, 'rb')), save=False)
            dashboard.save()
            self.stdout.write(self.style.SUCCESS('Dashboard creado'))
        else:
            dashboard = Dashboard.objects.get(name='INVOICE')
            self.stdout.write('Dashboard existente detectado, se reutiliza.')

        def ensure_module_type(name: str, icon: str):
            obj, _ = ModuleType.objects.get_or_create(name=name, defaults={'icon': icon})
            return obj

        # Asegurar los tipos base (coinciden con JSON, idempotente)
        ensure_module_type('Seguridad', 'fas fa-lock')
        ensure_module_type('Bodega', 'fas fa-boxes')
        ensure_module_type('Administrativo', 'fas fa-hand-holding-usd')
        ensure_module_type('Facturación', 'fas fa-calculator')
        ensure_module_type('Reportes', 'fas fa-chart-pie')

        # 4. Sembrar módulos desde JSON si no existen
        module_json_path = Path(settings.BASE_DIR) / 'deploy' / 'json' / 'module.json'
        if module_json_path.exists():
            with open(module_json_path, encoding='utf-8') as f:
                for module_json in json.load(f):
                    if not Module.objects.filter(name=module_json['name']).exists():
                        permissions = module_json.pop('permissions')
                        moduletype_id = module_json.pop('moduletype_id')
                        moduletype = ModuleType.objects.filter(id=moduletype_id).first() if moduletype_id else None
                        module_json['module_type'] = moduletype
                        module = Module.objects.create(**module_json)
                        if permissions:
                            for codename in permissions:
                                perm = Permission.objects.filter(codename=codename).first()
                                if perm:
                                    module.permissions.add(perm)
                        self.stdout.write(self.style.SUCCESS(f"Módulo sembrado: {module.name}"))
        else:
            self.stdout.write(self.style.WARNING('Archivo module.json no encontrado, se omite seed de módulos predefinidos.'))

        # 5. Crear módulos Planes y Suscripciones (Administrativo) si no existen
        administrativo = ModuleType.objects.filter(name='Administrativo').first()
        plan_module, created_plan = Module.objects.get_or_create(
            name='Planes',
            defaults={
                'url': '/subscription/plan/',
                'icon': 'fas fa-layer-group',
                'description': 'Permite administrar los planes de suscripción',
                'module_type': administrativo
            }
        )
        if created_plan:
            for codename in ['view_plan', 'add_plan', 'change_plan', 'delete_plan']:
                perm = Permission.objects.filter(codename=codename).first()
                if perm:
                    plan_module.permissions.add(perm)
            self.stdout.write(self.style.SUCCESS('Módulo Planes creado'))
        else:
            self.stdout.write('Módulo Planes ya existía')

        subscription_module, created_sub = Module.objects.get_or_create(
            name='Suscripciones',
            defaults={
                'url': '/subscription/',
                'icon': 'fas fa-receipt',
                'description': 'Permite administrar las suscripciones de las compañías',
                'module_type': administrativo
            }
        )
        if created_sub:
            for codename in ['view_subscription', 'add_subscription', 'change_subscription', 'delete_subscription']:
                perm = Permission.objects.filter(codename=codename).first()
                if perm:
                    subscription_module.permissions.add(perm)
            self.stdout.write(self.style.SUCCESS('Módulo Suscripciones creado'))
        else:
            self.stdout.write('Módulo Suscripciones ya existía')

        # 6. Asegurar grupos multi-tenant (segunda pasada idempotente para garantizar coherencia)
        super_admin_group, _ = Group.objects.get_or_create(name='Super Administrador')
        admin_group, _ = Group.objects.get_or_create(name='Administrador')
        owner_group, _ = Group.objects.get_or_create(name='Cliente Propietario')
        warehouse_group, _ = Group.objects.get_or_create(name='Operador Bodega')
        sales_group, _ = Group.objects.get_or_create(name='Operador Venta')
        client_group, _ = Group.objects.get_or_create(name='Cliente')
        readonly_group, _ = Group.objects.get_or_create(name='Consulta')

        all_modules = list(Module.objects.all())

        def link_module(group: Group, module: Module, include_perms=True):
            if not GroupModule.objects.filter(group=group, module=module).exists():
                GroupModule.objects.create(group=group, module=module)
            if include_perms:
                for perm in module.permissions.all():
                    group.permissions.add(perm)

        excluded_admin_names = {
            'Planes', 'Suscripciones', 'Conf. Dashboard', 'Tipos de Módulos', 'Módulos', 'Grupos'
        }
        for m in all_modules:
            # Super Administrador siempre todo
            link_module(super_admin_group, m, include_perms=True)
            # Administrador: excluir configuraciones globales SaaS
            if m.name not in excluded_admin_names:
                link_module(admin_group, m, include_perms=True)

        excluded_owner_module_names = set([])
        for m in all_modules:
            if m.name in excluded_owner_module_names:
                continue
            link_module(owner_group, m, include_perms=True)

        warehouse_keywords = ['Producto', 'Product', 'Inventario', 'Inventory', 'Bodega', 'Compra', 'Purchase', 'Proveedor', 'Provider']
        for m in all_modules:
            if any(k.lower() in m.name.lower() for k in warehouse_keywords):
                link_module(warehouse_group, m, include_perms=True)

        sales_keywords = ['Factura', 'Invoice', 'Cliente', 'Customer', 'Crédito', 'Credit']
        for m in all_modules:
            if any(k.lower() in m.name.lower() for k in sales_keywords):
                link_module(sales_group, m, include_perms=True)

        client_urls = ['/pos/customer/update/profile/', '/pos/invoice/customer/', '/pos/credit/note/customer/']
        for module in Module.objects.filter(url__in=client_urls + ['/user/update/password/']):
            link_module(client_group, module, include_perms=True)

        for m in all_modules:
            link_module(readonly_group, m, include_perms=False)
            for perm in m.permissions.all():
                if perm.codename.startswith('view_'):
                    readonly_group.permissions.add(perm)

        # 7. Crear usuario admin si no existe (asociado a Super Administrador y Administrador)
        if not User.objects.filter(username='admin').exists():
            user = User.objects.create(
                username='admin',
                names='Administrador General',
                email='admin@example.com',
                is_active=True,
                is_superuser=True,  # super admin real
                is_staff=True
            )
            user.set_password('admin')
            user.save()
            user.groups.add(super_admin_group)
            user.groups.add(admin_group)
            self.stdout.write(self.style.SUCCESS('Usuario admin creado (super + admin)'))
        else:
            self.stdout.write('Usuario admin ya existe')

        # 8. Seed planes
        DEFAULT_PLANS = [
            {
                'name': 'Starter',
                'description': 'Plan básico para iniciar la facturación',
                'max_invoices': 100,
                'max_customers': 100,
                'max_products': 200,
                'price': 0,
                'period_days': 30,
            },
            {
                'name': 'Pro',
                'description': 'Plan profesional para pymes',
                'max_invoices': 1000,
                'max_customers': 3000,
                'max_products': 5000,
                'price': 29.90,
                'period_days': 30,
            },
            {
                'name': 'Enterprise',
                'description': 'Grandes volúmenes y soporte avanzado',
                'max_invoices': 100000,
                'max_customers': 200000,
                'max_products': 500000,
                'price': 199.00,
                'period_days': 30,
            },
        ]
        created_plans = 0
        for data in DEFAULT_PLANS:
            _, was_created = Plan.objects.get_or_create(name=data['name'], defaults=data)
            if was_created:
                created_plans += 1
        self.stdout.write(self.style.SUCCESS(f'Planes verificados/creados: {created_plans} nuevos'))

        company = Company.objects.first()
        if company:
            starter = Plan.objects.filter(name='Starter').first()
            if starter and not company.subscriptions.exists():
                Subscription.objects.create(company=company, plan=starter)
                self.stdout.write(self.style.SUCCESS('Suscripción Starter creada para la compañía existente'))

        try:
            call_command('backfill_company_fk', verbosity=0)
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'Backfill de compañía omitido: {e}'))

        self.stdout.write(self.style.SUCCESS('Instalación completa (migraciones + seed + SaaS).'))
        # Iniciar servidor si no se pidió lo contrario
        if not options.get('no_serve'):
            host = options.get('host') or '0.0.0.0'
            port = str(options.get('port') or '80')
            self.stdout.write(self.style.WARNING(f'Iniciando servidor de desarrollo en http://{host}:{port} (Ctrl+C para detener)...'))
            try:
                call_command('runserver', f'{host}:{port}')
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'No se pudo iniciar el servidor: {e}'))
