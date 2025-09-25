import json
import os
from os.path import basename
from pathlib import Path

from django.core.files import File
from django.core.management import BaseCommand, call_command
from django.db import connection

from core.security.models import *  # noqa
from core.subscription.models import Plan, Subscription  # noqa
from core.pos.models import Company  # noqa
from django.contrib.auth.models import Permission


class Command(BaseCommand):
    help = 'Allows to initiate the base software installation'

    def load_json_from_file(self, file):
        with open(f'{settings.BASE_DIR}/deploy/json/{file}', encoding='utf-8', mode='r') as wr:
            return json.loads(wr.read())

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('==> Iniciando instalación integral (migraciones + seed + SaaS)'))

        # 1. Generar migraciones si faltan (o siempre para asegurar consistencia sin duplicar archivos existentes)
        local_app_labels = ['dashboard', 'login', 'pos', 'report', 'security', 'user', 'subscription']
        try:
            self.stdout.write('Generando migraciones (si hay cambios pendientes)...')
            call_command('makemigrations', *local_app_labels, interactive=False, verbosity=0)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error al generar migraciones: {e}'))
            return

        # 2. Aplicar migraciones
        try:
            self.stdout.write('Aplicando migraciones...')
            call_command('migrate', interactive=False, verbosity=0)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error al aplicar migraciones: {e}'))
            return

        existing_tables = set(connection.introspection.table_names())
        if 'security_dashboard' not in existing_tables:
            self.stdout.write(self.style.ERROR('No se creó la tabla security_dashboard. Abortando.'))
            return

        # 3. Sembrar dashboard y módulos solo si no existen (idempotente)
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

        # 6. Crear / asegurar grupos base
        admin_group, _ = Group.objects.get_or_create(name='Administrador')
        client_group, _ = Group.objects.get_or_create(name='Cliente')

        # Vincular módulos al grupo Administrador (todos los módulos existentes)
        for module in Module.objects.all():
            if not GroupModule.objects.filter(group=admin_group, module=module).exists():
                GroupModule.objects.create(group=admin_group, module=module)
                for perm in module.permissions.all():
                    admin_group.permissions.add(perm)

        # Cliente: restringido solo a urls cliente (similar lógica anterior)
        client_urls = ['/pos/customer/update/profile/', '/pos/invoice/customer/', '/pos/credit/note/customer/']
        for module in Module.objects.filter(url__in=client_urls + ['/user/update/password/']):
            if not GroupModule.objects.filter(group=client_group, module=module).exists():
                GroupModule.objects.create(group=client_group, module=module)
                for perm in module.permissions.all():
                    client_group.permissions.add(perm)

        # 7. Crear usuario admin si no existe
        if not User.objects.filter(username='admin').exists():
            user = User.objects.create(
                username='admin',
                names='Administrador General',
                email='admin@example.com',
                is_active=True,
                is_superuser=True,
                is_staff=True
            )
            user.set_password('hacker94')
            user.save()
            user.groups.add(admin_group)
            self.stdout.write(self.style.SUCCESS('Usuario admin creado'))
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

        # 9. Crear suscripción Starter por defecto si hay compañía y no tiene suscripción
        company = Company.objects.first()
        if company:
            starter = Plan.objects.filter(name='Starter').first()
            if starter and not company.subscriptions.exists():
                Subscription.objects.create(company=company, plan=starter)
                self.stdout.write(self.style.SUCCESS('Suscripción Starter creada para la compañía existente'))

        # 10. Backfill company en modelos que tengan el campo (si comando existe)
        try:
            call_command('backfill_company_fk', verbosity=0)
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'Backfill de compañía omitido: {e}'))

        self.stdout.write(self.style.SUCCESS('Instalación completa (migraciones + seed + SaaS).'))
