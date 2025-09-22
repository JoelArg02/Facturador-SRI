import json
import os
from os.path import basename

import django
from django.core.files import File
from django.core.management import BaseCommand

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.security.models import *
from django.contrib.auth.models import Permission


class Command(BaseCommand):
    help = 'Allows to initiate the base software installation'

    def load_json_from_file(self, file):
        with open(f'{settings.BASE_DIR}/deploy/json/{file}', encoding='utf-8', mode='r') as wr:
            return json.loads(wr.read())

    def handle(self, *args, **options):
        dashboard = Dashboard.objects.create(
            name='INVOICE',
            author='William Jair Dávila Vargas',
            footer_url='https://algorisoft.com',
            icon='fas fa-shopping-cart',
        )
        image_path = f'{settings.BASE_DIR}{settings.STATIC_URL}img/default/logo.png'
        dashboard.image.save(basename(image_path), content=File(open(image_path, 'rb')), save=False)
        dashboard.save()

        for module_type_json in self.load_json_from_file(file='module_type.json'):
            ModuleType.objects.create(**module_type_json)

        for module_json in self.load_json_from_file(file='module.json'):
            permissions = module_json.pop('permissions')
            moduletype_id = module_json.pop('moduletype_id')
            moduletype = ModuleType.objects.filter(id=moduletype_id).first() if moduletype_id else None
            module_json['module_type'] = moduletype
            module = Module.objects.create(**module_json)
            if permissions:
                for codename in permissions:
                    permission = Permission.objects.filter(codename=codename).first()
                    if permission:
                        module.permissions.add(permission)

        group = Group.objects.create(name='Administrador')
        print(f'insertado {group.name}')

        client_urls = ['/pos/customer/update/profile/', '/pos/invoice/customer/', '/pos/credit/note/customer/']

        for module in Module.objects.filter().exclude(url__in=client_urls):
            GroupModule.objects.create(module=module, group=group)
            for permission in module.permissions.all():
                group.permissions.add(permission)

        user = User.objects.create(
            username='admin',
            names='William Jair Dávila Vargas',
            email='davilawilliam93@gmail.com',
            is_active=True,
            is_superuser=True,
            is_staff=True
        )
        user.set_password('hacker94')
        user.save()
        user.groups.add(group)
        print(f'Bienvenido {user.username}')

        group = Group.objects.create(name='Cliente')
        print(f'insertado {group.name}')

        for module in Module.objects.filter(url__in=client_urls + ['/user/update/password/']):
            GroupModule.objects.create(module=module, group=group)
            for permission in module.permissions.all():
                group.permissions.add(permission)
