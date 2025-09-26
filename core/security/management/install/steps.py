from __future__ import annotations

import json
from os.path import basename
from pathlib import Path
from typing import Dict

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.files import File
from django.core.management import CommandError, call_command
from django.db import connection

from core.pos.models import Company
from core.security.models import Dashboard, GroupModule, Module, ModuleType
from core.subscription.models import Plan, Subscription

from .context import InstallationContext


def confirm_execution(ctx: InstallationContext) -> bool:
    """Solicita confirmación al usuario antes de reiniciar el entorno."""

    if ctx.force:
        return True

    ctx.stdout.write(ctx.style.WARNING(
        'ADVERTENCIA: Este proceso eliminará TODAS las migraciones locales y el archivo de base de datos (si es SQLite).'
    ))
    ctx.stdout.write(ctx.style.WARNING('Se regenerarán migraciones 0001_*.'))
    confirm = input('¿Desea continuar? (escriba SI para continuar): ')
    if confirm.strip().upper() != 'SI':
        ctx.stdout.write(ctx.style.ERROR('Operación cancelada.'))
        return False
    return True


def reset_database(ctx: InstallationContext) -> None:
    """Elimina la base de datos SQLite (si aplica) y purga migraciones locales."""

    command = ctx.command

    if command._remove_sqlite_db():
        ctx.stdout.write(ctx.style.SUCCESS('Base de datos SQLite eliminada.'))
    else:
        ctx.stdout.write('No se eliminó archivo de base de datos (puede no existir o no es SQLite).')

    removed = command._purge_local_migrations(ctx.local_app_labels)
    ctx.stdout.write(ctx.style.SUCCESS(f'Migraciones eliminadas: {removed}'))


def generate_initial_migrations(ctx: InstallationContext) -> None:
    """Genera las migraciones 0001_* para las apps locales."""

    try:
        ctx.stdout.write('Generando migraciones iniciales (0001_*)...')
        call_command('makemigrations', *ctx.local_app_labels, interactive=False, verbosity=0)
    except Exception as exc:  # pragma: no cover - output útil
        raise CommandError(f'Error al generar migraciones: {exc}') from exc


def apply_migrations(ctx: InstallationContext) -> None:
    """Aplica las migraciones pendientes."""

    try:
        ctx.stdout.write('Aplicando migraciones...')
        call_command('migrate', interactive=False, verbosity=0)
    except Exception as exc:  # pragma: no cover - output útil
        raise CommandError(f'Error al aplicar migraciones: {exc}') from exc


def validate_required_tables(ctx: InstallationContext) -> bool:
    """Comprueba que las tablas necesarias existen tras las migraciones."""

    existing_tables = set(connection.introspection.table_names())
    if 'security_dashboard' not in existing_tables:
        ctx.stdout.write(ctx.style.ERROR('No se creó la tabla security_dashboard. Abortando seed.'))
        return False
    return True


def ensure_dashboard_and_types(ctx: InstallationContext) -> None:
    """Crea el dashboard inicial y garantiza la existencia de los tipos de módulo base."""

    if not Dashboard.objects.filter(name='INVOICE').exists():
        dashboard = Dashboard.objects.create(
            name='INVOICE',
            author='AllpaSoft',
            footer_url='https://allpasoft.com',
            icon='fas fa-shopping-cart',
        )
        image_path = f"{settings.BASE_DIR}{settings.STATIC_URL}img/default/logo.png"
        if Path(image_path).exists():
            with Path(image_path).open('rb') as image_file:
                dashboard.image.save(
                    basename(image_path),
                    content=File(image_file),
                    save=False,
                )
        dashboard.save()
        ctx.stdout.write(ctx.style.SUCCESS('Dashboard creado'))
    else:
        ctx.stdout.write('Dashboard existente detectado, se reutiliza.')

    base_types: Dict[str, str] = {
        'Seguridad': 'fas fa-lock',
        'Bodega': 'fas fa-boxes',
        'Administrativo': 'fas fa-hand-holding-usd',
        'Facturación': 'fas fa-calculator',
        'Reportes': 'fas fa-chart-pie',
    }
    for name, icon in base_types.items():
        ModuleType.objects.get_or_create(name=name, defaults={'icon': icon})


def seed_modules_from_json(ctx: InstallationContext) -> None:
    """Crea módulos predefinidos desde el archivo JSON de despliegue."""

    module_json_path = Path(settings.BASE_DIR) / 'deploy' / 'json' / 'module.json'
    if not module_json_path.exists():
        ctx.stdout.write(ctx.style.WARNING('Archivo module.json no encontrado, se omite seed de módulos predefinidos.'))
        return

    with module_json_path.open(encoding='utf-8') as handler:
        for module_json in json.load(handler):
            if Module.objects.filter(name=module_json['name']).exists():
                continue

            permissions = module_json.pop('permissions', [])
            moduletype_id = module_json.pop('moduletype_id', None)
            moduletype = ModuleType.objects.filter(id=moduletype_id).first() if moduletype_id else None
            module_json['module_type'] = moduletype

            module = Module.objects.create(**module_json)
            for codename in permissions:
                perm = Permission.objects.filter(codename=codename).first()
                if perm:
                    module.permissions.add(perm)
            ctx.stdout.write(ctx.style.SUCCESS(f"Módulo sembrado: {module.name}"))


def ensure_subscription_modules(ctx: InstallationContext) -> None:
    """Garantiza la existencia de los módulos Planes y Suscripciones."""

    administrativo = ModuleType.objects.filter(name='Administrativo').first()

    plan_defaults = {
        'url': '/subscription/plan/',
        'icon': 'fas fa-layer-group',
        'description': 'Permite administrar los planes de suscripción',
        'module_type': administrativo,
    }
    plan_module, created_plan = Module.objects.get_or_create(name='Planes', defaults=plan_defaults)
    if created_plan:
        for codename in ['view_plan', 'add_plan', 'change_plan', 'delete_plan']:
            perm = Permission.objects.filter(codename=codename).first()
            if perm:
                plan_module.permissions.add(perm)
        ctx.stdout.write(ctx.style.SUCCESS('Módulo Planes creado'))
    else:
        ctx.stdout.write('Módulo Planes ya existía')

    subscription_defaults = {
        'url': '/subscription/',
        'icon': 'fas fa-receipt',
        'description': 'Permite administrar las suscripciones de las compañías',
        'module_type': administrativo,
    }
    subscription_module, created_sub = Module.objects.get_or_create(name='Suscripciones', defaults=subscription_defaults)
    if created_sub:
        for codename in ['view_subscription', 'add_subscription', 'change_subscription', 'delete_subscription']:
            perm = Permission.objects.filter(codename=codename).first()
            if perm:
                subscription_module.permissions.add(perm)
        ctx.stdout.write(ctx.style.SUCCESS('Módulo Suscripciones creado'))
    else:
        ctx.stdout.write('Módulo Suscripciones ya existía')


def ensure_company_admin_module(ctx: InstallationContext) -> None:
    """Crea el módulo de administración de Empresas y asocia permisos CRUD."""
    administrativo = ModuleType.objects.filter(name='Administrativo').first()
    defaults = {
        'url': '/security/company/',
        'icon': 'fas fa-building',
        'description': 'Permite administrar las empresas (Super Administrador)',
        'module_type': administrativo,
    }
    module, created = Module.objects.get_or_create(name='Empresas', defaults=defaults)
    if created:
        for codename in ['view_company', 'add_company', 'change_company', 'delete_company']:
            perm = Permission.objects.filter(codename=codename).first()
            if perm:
                module.permissions.add(perm)
        ctx.stdout.write(ctx.style.SUCCESS('Módulo Empresas creado'))
    else:
        # Asegurar permisos vinculados aunque ya exista
        for codename in ['view_company', 'add_company', 'change_company', 'delete_company']:
            perm = Permission.objects.filter(codename=codename).first()
            if perm and not module.permissions.filter(id=perm.id).exists():
                module.permissions.add(perm)
        ctx.stdout.write('Módulo Empresas ya existía')


def configure_groups_and_permissions(ctx: InstallationContext) -> Dict[str, Group]:
    """Configura los grupos principales y sus permisos asociados."""

    super_admin_group, _ = Group.objects.get_or_create(name='Super Administrador')
    admin_group, _ = Group.objects.get_or_create(name='Administrador')
    warehouse_group, _ = Group.objects.get_or_create(name='Operador Bodega')
    sales_group, _ = Group.objects.get_or_create(name='Operador Venta')
    client_group, _ = Group.objects.get_or_create(name='Cliente')
    readonly_group, _ = Group.objects.get_or_create(name='Consulta')

    all_modules = list(Module.objects.all())

    def link_module(group: Group, module: Module, include_perms: bool = True) -> None:
        if not GroupModule.objects.filter(group=group, module=module).exists():
            GroupModule.objects.create(group=group, module=module)
        if include_perms:
            for perm in module.permissions.all():
                group.permissions.add(perm)

    restricted_admin_exact_names = {
        'Conf. Dashboard',
        'Dashboard',
        'Grupos',
        'Planes',
        'Suscripciones',
        'Módulos',
        'Tipos de Módulos',
        'Tipo de Módulo',
    }
    restricted_admin_keywords = {
        'plan',
        'suscrip',
        'dashboard',
        'grupo',
        'group',
        'module',
        'módulo',
        'module type',
        'tipo de módulo',
    }
    restricted_admin_url_tokens = {
        '/subscription/',
        '/subscription',
        '/security/module',
        '/security/group',
        '/dashboard',
    }

    def is_admin_restricted(module: Module) -> bool:
        name_lower = module.name.lower()
        url_lower = (module.url or '').lower()

        if module.name in restricted_admin_exact_names:
            return True
        if any(keyword in name_lower for keyword in restricted_admin_keywords):
            return True
        if any(token in url_lower for token in restricted_admin_url_tokens):
            return True
        return False

    for module in all_modules:
        link_module(super_admin_group, module, include_perms=True)
        if not is_admin_restricted(module):
            link_module(admin_group, module, include_perms=True)

    warehouse_keywords = ['Producto', 'Product', 'Inventario', 'Inventory', 'Bodega', 'Compra', 'Purchase', 'Proveedor', 'Provider']
    for module in all_modules:
        if any(keyword.lower() in module.name.lower() for keyword in warehouse_keywords):
            link_module(warehouse_group, module, include_perms=True)

    sales_keywords = ['Factura', 'Invoice', 'Cliente', 'Customer', 'Crédito', 'Credit']
    for module in all_modules:
        if any(keyword.lower() in module.name.lower() for keyword in sales_keywords):
            link_module(sales_group, module, include_perms=True)

    client_urls = ['/pos/customer/update/profile/', '/pos/invoice/customer/', '/pos/credit/note/customer/']
    for module in Module.objects.filter(url__in=client_urls + ['/user/update/password/']):
        link_module(client_group, module, include_perms=True)

    for module in all_modules:
        link_module(readonly_group, module, include_perms=False)
        for perm in module.permissions.all():
            if perm.codename.startswith('view_'):
                readonly_group.permissions.add(perm)

    return {
        'super_admin': super_admin_group,
        'admin': admin_group,
        'warehouse': warehouse_group,
        'sales': sales_group,
        'client': client_group,
        'readonly': readonly_group,
    }


def ensure_admin_user(ctx: InstallationContext, groups: Dict[str, Group]) -> None:
    """Crea el usuario admin por defecto y lo asocia a los grupos clave."""

    user_model = get_user_model()

    if user_model.objects.filter(username='admin').exists():
        ctx.stdout.write('Usuario admin ya existe')
        return

    user = user_model.objects.create(
        username='admin',
        names='Administrador General',
        email='admin@example.com',
        is_active=True,
        is_superuser=True,
        is_staff=True,
    )
    user.set_password('admin')
    user.save()

    super_admin_group = groups.get('super_admin')
    if super_admin_group:
        user.groups.set([super_admin_group])
    ctx.stdout.write(ctx.style.SUCCESS('Usuario admin creado y asociado a grupos'))


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


def seed_default_plans(ctx: InstallationContext) -> None:
    created = 0
    for data in DEFAULT_PLANS:
        _, was_created = Plan.objects.get_or_create(name=data['name'], defaults=data)
        if was_created:
            created += 1
    ctx.stdout.write(ctx.style.SUCCESS(f'Planes verificados/creados: {created} nuevos'))


def ensure_owner_subscription(ctx: InstallationContext) -> None:
    company = Company.objects.select_related('owner').first()
    if not company or not company.owner:
        return

    starter = Plan.objects.filter(name='Starter').first()
    if starter and not company.owner.subscriptions.exists():
        Subscription.objects.create(user=company.owner, plan=starter)
        ctx.stdout.write(ctx.style.SUCCESS('Suscripción Starter creada para el propietario de la compañía existente'))


def backfill_company_relations(ctx: InstallationContext) -> None:
    try:
        call_command('backfill_company_fk', verbosity=0)
    except Exception as exc:  # pragma: no cover - output útil
        ctx.stdout.write(ctx.style.WARNING(f'Backfill de compañía omitido: {exc}'))


def maybe_start_dev_server(ctx: InstallationContext) -> None:
    if ctx.no_serve:
        return

    host = ctx.get_option('host') or '0.0.0.0'
    port = str(ctx.get_option('port') or '80')
    ctx.stdout.write(ctx.style.WARNING(
        f'Iniciando servidor de desarrollo en http://{host}:{port} (Ctrl+C para detener)...'
    ))
    try:
        call_command('runserver', f'{host}:{port}')
    except Exception as exc:  # pragma: no cover - output útil
        ctx.stdout.write(ctx.style.ERROR(f'No se pudo iniciar el servidor: {exc}'))
