import json
import os
import random
import string
from os.path import basename

import django
from django.contrib.auth.models import Group
from django.core.management import BaseCommand

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.pos.models import *


class Command(BaseCommand):
    help = 'It allows me to insert test data into the software'

    def load_json_from_file(self, file):
        with open(f'{settings.BASE_DIR}/deploy/json/{file}', encoding='utf-8', mode='r') as wr:
            return json.loads(wr.read())

    def handle(self, *args, **options):
        company = Company.objects.create(
            ruc='1002376026001',
            company_name='CAZARES ZULETA JUAN FRANCISCO',
            commercial_name='DISTRIBUIDORA MAYORGA',
            establishment_code='006',
            issuing_point_code='006',
            special_taxpayer='000',
            main_address='ORELLANA / LORETO / LORETO / AV. RAFAEL ANDRADE S/N Y GREGORIO URAPARI',
            establishment_address='ORELLANA / LORETO / LORETO / AV. RAFAEL ANDRADE S/N Y GREGORIO URAPARI',
            mobile='0986462199',
            phone='982270674',
            email='cazareszuleta@gmail.com',
            website='http://www.ialoreto.com',
            description='VENTA AL POR MENOR DE ARTÍCULOS DE FERRETERÍA: MARTILLOS, SIERRAS, DESTORNILLADORES Y PEQUEÑAS HERRAMIENTAS EN GENERAL, EQUIPO Y MATERIALES DE PREFABRICADOS PARA ARMADO CASERO (EQUIPO DE BRICOLAJE); ALAMBRES Y CABLES ELÉCTRICOS, CERRADURAS, MONTAJES Y ADORNOS, EXTINTORES, SEGADORAS DE CÉSPED DE CUALQUIER TIPO, ETCÉTERA EN ESTABLECIMIENTOS ESPECIALIZADOS.',
            tax=15.00,
            electronic_signature_key='JFcz0326',
            email_host_user='netdev@in-planet.net',
            email_host_password='llylnrfzcsvykyyl',
        )
        image_path = f'{settings.BASE_DIR}{settings.STATIC_URL}img/default/logo.png'
        company.image.save(basename(image_path), content=File(open(image_path, 'rb')), save=False)
        electronic_signature_path = f'{settings.BASE_DIR}/deploy/files/firma.p12'
        company.electronic_signature.save(basename(electronic_signature_path), content=File(open(electronic_signature_path, 'rb')), save=False)
        company.save()

        numbers = list(string.digits)
        for item in VOUCHER_TYPE:
            Receipt.objects.create(voucher_type=item[0], establishment_code=company.establishment_code, issuing_point_code=company.issuing_point_code, sequence=0 if item[0] == VOUCHER_TYPE[2][0] else random.randint(10000, 99999))

        for product_json in self.load_json_from_file(file='product.json'):
            product_json['category'] = Category.objects.get_or_create(name=product_json.pop('category'))[0]
            product = Product.objects.create(**product_json)
            print(f'Product record created successfully: {product.id}')

        for expense_type in self.load_json_from_file(file='expense_type.json'):
            expense_type = ExpenseType.objects.create(**expense_type)
            print(f'Expense type record created successfully: {expense_type.id}')

        for provider_json in self.load_json_from_file(file='provider.json'):
            provider = Provider.objects.create(**provider_json)
            print(f'Provider record created successfully: {provider.id}')

        for customer_json in self.load_json_from_file(file='customer.json')[0:20]:
            user = User.objects.create(username=customer_json['dni'], names=customer_json.pop('names'), email=customer_json.pop('email'))
            user.set_password(user.username)
            user.is_active = customer_json['identification_type'] != IDENTIFICATION_TYPE[-2][0]
            user.save()
            user.groups.add(Group.objects.get(id=settings.GROUPS['customer']))
            customer_json['user'] = user
            customer = Customer.objects.create(**customer_json)
            print(f'Customer record created successfully: {customer.id}')

        provider_id = list(Provider.objects.all().values_list('id', flat=True))
        product_id = list(Product.objects.filter(is_inventoried=True).values_list('id', flat=True))

        for i in range(1, random.randint(4, 10)):
            purchase = Purchase.objects.create(number=''.join(random.choices(numbers, k=8)), provider_id=random.choice(provider_id))
            for d in range(1, random.randint(3, 10)):
                product_choice = random.choice(product_id)
                while purchase.purchasedetail_set.filter(product_id=product_choice).exists():
                    product_choice = random.choice(product_id)
                product = Product.objects.get(pk=product_choice)
                detail = PurchaseDetail.objects.create(purchase_id=purchase.id, product_id=product.id, quantity=random.randint(1, 50), price=product.pvp)
                detail.subtotal = float(detail.price) * detail.quantity
                detail.save()
                product.stock += detail.quantity
                product.save()
            purchase.recalculate_invoice()
            print(f'Purchase record created successfully: {purchase.id}')
