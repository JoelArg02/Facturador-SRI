import base64
import math
import os
import smtplib
import tempfile
import time
import unicodedata
from decimal import Decimal
from datetime import datetime
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from io import BytesIO
from xml.etree import ElementTree
from email.utils import formataddr

import barcode
from barcode import writer
from django.core.files.base import ContentFile, File
from django.db import models, transaction
from django.db.models import F, Sum, FloatField
from django.db.models.functions import Coalesce
from django.forms import model_to_dict

from config import settings
from core.pos.choices import *
from core.pos.utilities.pdf_creator import PDFCreator
from core.pos.utilities.sri import SRI
from core.user.models import User


class Company(models.Model):
    ruc = models.CharField(max_length=13, help_text='Ingrese un número de RUC', verbose_name='Número de RUC')
    company_name = models.CharField(max_length=50, help_text='Ingrese la razón social', verbose_name='Razón social')
    commercial_name = models.CharField(max_length=50, help_text='Ingrese el nombre comercial', verbose_name='Nombre Comercial')
    main_address = models.CharField(max_length=200, help_text='Ingrese la dirección del Establecimiento Matriz', verbose_name='Dirección del Establecimiento Matriz')
    establishment_address = models.CharField(max_length=200, help_text='Ingrese la dirección del Establecimiento Emisor', verbose_name='Dirección del Establecimiento Emisor')
    establishment_code = models.CharField(max_length=3, help_text='Ingrese el código del Establecimiento Emisor', verbose_name='Código del Establecimiento Emisor')
    issuing_point_code = models.CharField(max_length=3, help_text='Ingrese el código del Punto de Emisión', verbose_name='Código del Punto de Emisión')
    special_taxpayer = models.CharField(max_length=13, help_text='Ingrese el número de Resolución del Contribuyente Especial', verbose_name='Contribuyente Especial (Número de Resolución)')
    obligated_accounting = models.CharField(max_length=2, choices=OBLIGATED_ACCOUNTING, default=OBLIGATED_ACCOUNTING[1][0], verbose_name='Obligado a Llevar Contabilidad')
    image = models.ImageField(upload_to='company/%Y/%m/%d', null=True, blank=True, verbose_name='Logotipo')
    environment_type = models.PositiveIntegerField(choices=ENVIRONMENT_TYPE, default=1, verbose_name='Tipo de Ambiente')
    emission_type = models.PositiveIntegerField(choices=EMISSION_TYPE, default=1, verbose_name='Tipo de Emisión')
    retention_agent = models.CharField(max_length=2, choices=RETENTION_AGENT, default=RETENTION_AGENT[1][0], verbose_name='Agente de Retención')
    regimen_rimpe = models.CharField(max_length=50, choices=REGIMEN_RIMPE, default=REGIMEN_RIMPE[0][0], verbose_name='Regimen Tributario')
    mobile = models.CharField(max_length=10, null=True, blank=True, help_text='Ingrese el teléfono celular', verbose_name='Teléfono celular')
    phone = models.CharField(max_length=9, null=True, blank=True, help_text='Ingrese el teléfono convencional', verbose_name='Teléfono convencional')
    email = models.CharField(max_length=50, help_text='Ingrese la dirección de correo electrónico', verbose_name='Email')
    website = models.CharField(max_length=250, help_text='Ingrese la dirección de la página web', verbose_name='Dirección de página web')
    description = models.CharField(max_length=500, null=True, blank=True, help_text='Ingrese una breve descripción', verbose_name='Descripción')
    tax = models.DecimalField(default=0.00, decimal_places=2, max_digits=9, verbose_name='Impuesto IVA')
    tax_percentage = models.IntegerField(choices=TAX_PERCENTAGE, default=TAX_PERCENTAGE[3][0], verbose_name='Porcentaje del impuesto IVA')
    electronic_signature = models.FileField(null=True, blank=True, upload_to='company/%Y/%m/%d', verbose_name='Firma electrónica (Archivo P12)')
    electronic_signature_key = models.CharField(max_length=100, help_text='Ingrese la clave de firma electrónica', verbose_name='Clave de firma electrónica')
    email_host = models.CharField(max_length=30, default='smtp.gmail.com', verbose_name='Servidor de correo')
    email_port = models.IntegerField(default=587, verbose_name='Puerto del servidor de correo')
    email_host_user = models.CharField(max_length=100, help_text='Ingrese el nombre de usuario del servidor de correo', verbose_name='Username del servidor de correo')
    email_host_password = models.CharField(max_length=30, help_text='Ingrese la contraseña del servidor de correo', verbose_name='Password del servidor de correo')
    # OneToOne propietario (evitar choque con User.company => usar related_name 'owned_company')
    owner = models.OneToOneField('user.User', null=True, blank=True, related_name='owned_company', on_delete=models.SET_NULL, verbose_name='Propietario')

    def __str__(self):
        return self.commercial_name

    @property
    def is_popular_business(self):
        return self.regimen_rimpe == REGIMEN_RIMPE[2][0]

    @property
    def is_popular_regime(self):
        return self.regimen_rimpe == REGIMEN_RIMPE[0][0]

    @property
    def is_retention_agent(self):
        return self.retention_agent == RETENTION_AGENT[0][0]

    @property
    def tax_percentage_value(self) -> Decimal:
        mapped = TAX_PERCENTAGE_VALUE_MAP.get(self.tax_percentage)
        if mapped is not None:
            return Decimal(str(mapped))
        return Decimal(self.tax or 0)

    @property
    def base64_image(self):
        try:
            if self.image:
                with open(self.image.path, 'rb') as image_file:
                    base64_data = base64.b64encode(image_file.read()).decode('utf-8')
                    extension = os.path.splitext(self.image.name)[1]
                    content_type = f'image/{extension.lstrip(".")}'
                    return f"data:{content_type};base64,{base64_data}"
        except:
            pass
        return None

    @property
    def tax_rate(self):
        return float(self.tax_percentage_value) / 100

    def get_image(self):
        if self.image:
            return f'{settings.MEDIA_URL}{self.image}'
        return f'{settings.STATIC_URL}img/default/empty.png'

    def get_full_path_image(self):
        if self.image:
            return self.image.path
        return f'{settings.BASE_DIR}{settings.STATIC_URL}img/default/empty.png'

    def get_electronic_signature(self):
        if self.electronic_signature:
            return f'{settings.MEDIA_URL}{self.electronic_signature}'
        return None

    def as_dict(self):
        item = model_to_dict(self)
        item['image'] = self.get_image()
        item['electronic_signature'] = self.get_electronic_signature()
        item['tax'] = float(self.tax_percentage_value)
        item['tax_percentage_value'] = float(self.tax_percentage_value)
        item['owner'] = self.owner_id
        return item

    # Helpers multi-tenant iniciales
    def active_subscription(self):
        from core.subscription.models import get_active_subscription
        return get_active_subscription(self)

    def can_create(self, kind: str):
        """Verifica cuotas del plan antes de crear recursos (kind: invoice|customer|product)."""
        from core.subscription.services import ensure_quota, QuotaExceeded
        try:
            ensure_quota(self, kind)
            return True, None
        except QuotaExceeded as e:
            return False, str(e)

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        mapped_tax = TAX_PERCENTAGE_VALUE_MAP.get(self.tax_percentage)
        if mapped_tax is not None:
            self.tax = Decimal(str(mapped_tax))
        if self.pk:
            Receipt.objects.update(establishment_code=self.establishment_code, issuing_point_code=self.issuing_point_code)
        super(Company, self).save()

    class Meta:
        verbose_name = 'Compañia'
        verbose_name_plural = 'Compañias'
        default_permissions = ()
        permissions = (
            ('change_company', 'Can change Compañia'),
        )


class Provider(models.Model):
    company = models.ForeignKey('pos.Company', null=True, blank=True, related_name='providers', on_delete=models.CASCADE, verbose_name='Compañía')
    name = models.CharField(max_length=50, help_text='Ingrese un nombre', verbose_name='Nombre')
    ruc = models.CharField(max_length=13, help_text='Ingrese un RUC', verbose_name='RUC')
    mobile = models.CharField(max_length=10, help_text='Ingrese un número de teléfono celular', verbose_name='Teléfono celular')
    address = models.CharField(max_length=500, null=True, blank=True, help_text='Ingrese una dirección', verbose_name='Dirección')
    email = models.CharField(max_length=50, help_text='Ingrese un email', verbose_name='Email')

    def __str__(self):
        return self.get_full_name()

    def get_full_name(self):
        return f'{self.name} ({self.ruc})'

    def as_dict(self):
        item = model_to_dict(self)
        item['text'] = self.get_full_name()
        return item

    class Meta:
        verbose_name = 'Proveedor'
        verbose_name_plural = 'Proveedores'
        constraints = [
            # Unicidad por compañía (solo aplica cuando company NO es nula)
            models.UniqueConstraint(fields=['company', 'name'], name='uniq_provider_company_name', condition=models.Q(company__isnull=False)),
            models.UniqueConstraint(fields=['company', 'ruc'], name='uniq_provider_company_ruc', condition=models.Q(company__isnull=False)),
            models.UniqueConstraint(fields=['company', 'mobile'], name='uniq_provider_company_mobile', condition=models.Q(company__isnull=False)),
            models.UniqueConstraint(fields=['company', 'email'], name='uniq_provider_company_email', condition=models.Q(company__isnull=False)),
        ]


class Category(models.Model):
    company = models.ForeignKey('pos.Company', null=True, blank=True, related_name='categories', on_delete=models.CASCADE, verbose_name='Compañía')
    # Se elimina unique=True global para permitir mismo nombre en distintas compañías.
    name = models.CharField(max_length=50, help_text='Ingrese un nombre', verbose_name='Nombre')

    def __str__(self):
        return self.name

    def as_dict(self):
        item = model_to_dict(self)
        return item

    class Meta:
        verbose_name = 'Categoria'
        verbose_name_plural = 'Categorias'
        constraints = [
            models.UniqueConstraint(fields=['company', 'name'], name='uniq_category_company_name')
        ]


class Product(models.Model):
    company = models.ForeignKey('pos.Company', null=True, blank=True, related_name='products', on_delete=models.CASCADE, verbose_name='Compañía')
    name = models.CharField(max_length=150, help_text='Ingrese un nombre', verbose_name='Nombre')
    code = models.CharField(max_length=50, unique=True, help_text='Ingrese un código', verbose_name='Código')
    description = models.CharField(max_length=500, null=True, blank=True, help_text='Ingrese una descripción', verbose_name='Descripción')
    category = models.ForeignKey(Category, on_delete=models.PROTECT, verbose_name='Categoría')
    price = models.DecimalField(max_digits=9, decimal_places=4, default=0.00, verbose_name='Precio de Compra')
    pvp = models.DecimalField(max_digits=9, decimal_places=4, default=0.00, verbose_name='Precio de Venta Sin Impuesto')
    image = models.ImageField(upload_to='product/%Y/%m/%d', null=True, blank=True, verbose_name='Imagen')
    barcode = models.ImageField(upload_to='barcode/%Y/%m/%d', null=True, blank=True, verbose_name='Código de barra')
    is_inventoried = models.BooleanField(default=True, verbose_name='¿Es inventariado?')
    stock = models.IntegerField(default=0)
    has_tax = models.BooleanField(default=True, verbose_name='¿Se cobra impuesto?')

    def __str__(self):
        return self.get_full_name()

    def get_full_name(self):
        return f'{self.name} ({self.code}) ({self.category.name})'

    def get_short_name(self):
        return f'{self.name} ({self.category.name})'

    def get_price_promotion(self):
        promotion = self.promotiondetail_set.filter(promotion__active=True).first()
        if promotion:
            return promotion.final_price
        return 0.00

    def get_current_price(self):
        price_promotion = self.get_price_promotion()
        return price_promotion if price_promotion else self.pvp

    def get_image(self):
        if self.image:
            return f'{settings.MEDIA_URL}{self.image}'
        return f'{settings.STATIC_URL}img/default/empty.png'

    def get_barcode(self):
        if self.barcode:
            return f'{settings.MEDIA_URL}{self.barcode}'
        return f'{settings.STATIC_URL}img/default/empty.png'

    def get_benefit(self):
        return round(float(self.pvp) - float(self.price), 2)

    def generate_barcode(self):
        try:
            image_io = BytesIO()
            barcode.Gs1_128(self.code, writer=barcode.writer.ImageWriter()).write(image_io)
            filename = f'{self.code}.png'
            self.barcode.save(filename, content=ContentFile(image_io.getvalue()), save=False)
        except:
            pass

    def as_dict(self):
        item = model_to_dict(self)
        item['value'] = self.get_full_name()
        item['full_name'] = self.get_full_name()
        item['short_name'] = self.get_short_name()
        item['category'] = self.category.as_dict()
        item['price'] = float(self.price)
        item['price_promotion'] = float(self.get_price_promotion())
        item['current_price'] = float(self.get_current_price())
        item['pvp'] = float(self.pvp)
        item['image'] = self.get_image()
        item['barcode'] = self.get_barcode()
        return item

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        self.generate_barcode()
        super(Product, self).save()

    class Meta:
        verbose_name = 'Producto'
        verbose_name_plural = 'Productos'
        default_permissions = ()
        permissions = (
            ('view_product', 'Can view Producto'),
            ('add_product', 'Can add Producto'),
            ('change_product', 'Can change Producto'),
            ('delete_product', 'Can delete Producto'),
            ('adjust_product_stock', 'Can adjust_product_stock Producto'),
        )


class Purchase(models.Model):
    company = models.ForeignKey('pos.Company', null=True, blank=True, related_name='purchases', on_delete=models.CASCADE, verbose_name='Compañía')
    number = models.CharField(max_length=8, unique=True, help_text='Ingrese un número de factura', verbose_name='Número de factura')
    provider = models.ForeignKey(Provider, on_delete=models.PROTECT, verbose_name='Proveedor')
    payment_type = models.CharField(max_length=50, choices=PAYMENT_TYPE, default=PAYMENT_TYPE[0][0], verbose_name='Tipo de pago')
    date_joined = models.DateField(default=datetime.now, verbose_name='Fecha de registro')
    end_credit = models.DateField(default=datetime.now, verbose_name='Fecha de plazo de crédito')
    subtotal = models.DecimalField(max_digits=9, decimal_places=2, default=0.00, verbose_name='Subtotal')
    tax = models.DecimalField(max_digits=9, decimal_places=2, default=0.00, verbose_name='IVA')
    total_tax = models.DecimalField(max_digits=9, decimal_places=2, default=0.00, verbose_name='Total de IVA')
    total_amount = models.DecimalField(max_digits=9, decimal_places=2, default=0.00, verbose_name='Total a pagar')

    def __str__(self):
        return self.provider.name

    def calculate_detail(self):
        for detail in self.purchasedetail_set.filter():
            detail.subtotal = int(detail.quantity) * float(detail.price)
            detail.save()

    def calculate_invoice(self):
        self.subtotal = float(self.purchasedetail_set.aggregate(result=Coalesce(Sum('subtotal'), 0.00, output_field=FloatField()))['result'])
        self.total_tax = round(self.subtotal * float(self.tax), 2)
        self.total_amount = round(self.subtotal, 2) + float(self.total_tax)
        self.save()

    def recalculate_invoice(self):
        self.calculate_detail()
        self.calculate_invoice()

    def delete(self, using=None, keep_parents=False):
        try:
            for i in self.purchasedetail_set.all():
                i.product.stock -= i.quantity
                i.product.save()
        except:
            pass
        super(Purchase, self).delete()

    def as_dict(self):
        item = model_to_dict(self)
        item['provider'] = self.provider.as_dict()
        item['payment_type'] = {'id': self.payment_type, 'name': self.get_payment_type_display()}
        item['date_joined'] = self.date_joined.strftime('%Y-%m-%d')
        item['end_credit'] = self.end_credit.strftime('%Y-%m-%d')
        item['subtotal'] = float(self.subtotal)
        item['tax'] = float(self.tax)
        item['total_tax'] = float(self.total_tax)
        item['total_amount'] = float(self.total_amount)
        return item

    class Meta:
        verbose_name = 'Compra'
        verbose_name_plural = 'Compras'
        default_permissions = ()
        permissions = (
            ('view_purchase', 'Can view Compra'),
            ('add_purchase', 'Can add Compra'),
            ('delete_purchase', 'Can delete Compra'),
        )


class PurchaseDetail(models.Model):
    company = models.ForeignKey('pos.Company', null=True, blank=True, related_name='purchase_details', on_delete=models.CASCADE, verbose_name='Compañía')
    purchase = models.ForeignKey(Purchase, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.IntegerField(default=0)
    price = models.DecimalField(max_digits=9, decimal_places=4, default=0.00)
    subtotal = models.DecimalField(max_digits=9, decimal_places=4, default=0.00)

    def __str__(self):
        return self.product.name

    def as_dict(self):
        item = model_to_dict(self, exclude=['purchase'])
        item['product'] = self.product.as_dict()
        item['price'] = float(self.price)
        item['subtotal'] = float(self.subtotal)
        return item

    class Meta:
        verbose_name = 'Detalle de Compra'
        verbose_name_plural = 'Detalle de Compras'
        default_permissions = ()


class AccountPayable(models.Model):
    company = models.ForeignKey('pos.Company', null=True, blank=True, related_name='accounts_payable', on_delete=models.CASCADE, verbose_name='Compañía')
    purchase = models.ForeignKey(Purchase, on_delete=models.PROTECT)
    date_joined = models.DateField(default=datetime.now)
    end_date = models.DateField(default=datetime.now)
    debt = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)
    balance = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.get_full_name()

    def formatted_date_joined(self):
        return self.date_joined.strftime('%Y-%m-%d')

    def get_full_name(self):
        return f"{self.purchase.provider.name} ({self.purchase.number}) / {self.formatted_date_joined()} / ${f'{self.debt:.2f}'}"

    def validate_debt(self):
        try:
            balance = self.accountpayablepayment_set.aggregate(result=Coalesce(Sum('amount'), 0.00, output_field=FloatField()))['result']
            self.balance, self.active = float(self.debt) - float(balance), (float(self.debt) - float(balance)) > 0.00
            self.save()
        except:
            pass

    def as_dict(self):
        item = model_to_dict(self)
        item['text'] = self.get_full_name()
        item['purchase'] = self.purchase.as_dict()
        item['date_joined'] = self.formatted_date_joined()
        item['end_date'] = self.end_date.strftime('%Y-%m-%d')
        item['debt'] = float(self.debt)
        item['balance'] = float(self.balance)
        return item

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        if not self.pk:
            self.balance = self.debt
        super(AccountPayable, self).save()

    class Meta:
        verbose_name = 'Cuenta por pagar'
        verbose_name_plural = 'Cuentas por pagar'
        default_permissions = ()
        permissions = (
            ('view_account_payable', 'Can view Cuenta por pagar'),
            ('add_account_payable', 'Can add Cuenta por pagar'),
            ('delete_account_payable', 'Can delete Cuenta por pagar'),
        )


class AccountPayablePayment(models.Model):
    company = models.ForeignKey('pos.Company', null=True, blank=True, related_name='accounts_payable_payments', on_delete=models.CASCADE, verbose_name='Compañía')
    account_payable = models.ForeignKey(AccountPayable, on_delete=models.CASCADE, verbose_name='Cuenta por pagar')
    date_joined = models.DateField(default=datetime.now, verbose_name='Fecha de registro')
    description = models.CharField(max_length=500, null=True, blank=True, help_text='Ingrese una descripción', verbose_name='Detalles')
    amount = models.DecimalField(max_digits=9, decimal_places=2, default=0.00, verbose_name='Monto')

    def __str__(self):
        return self.account_payable.id

    def as_dict(self):
        item = model_to_dict(self, exclude=['debts_pay'])
        item['date_joined'] = self.date_joined.strftime('%Y-%m-%d')
        item['amount'] = float(self.amount)
        return item

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        if not self.description:
            self.description = 's/n'
        super(AccountPayablePayment, self).save()
        self.account_payable.validate_debt()

    def delete(self, using=None, keep_parents=False):
        account_payable = self.account_payable
        super(AccountPayablePayment, self).delete()
        account_payable.validate_debt()

    class Meta:
        verbose_name = 'Pago de una Cuenta por pagar'
        verbose_name_plural = 'Pago de unas Cuentas por pagar'
        default_permissions = ()


class Customer(models.Model):
    # Campos alineados con las migraciones ya aplicadas en la BD (NO generar nuevas migraciones)
    company = models.ForeignKey('pos.Company', null=True, blank=True, related_name='customers', on_delete=models.CASCADE, verbose_name='Compañía')
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    # En la BD existen dos columnas: dni (10) y ruc (13) ambas únicas y opcionales
    dni = models.CharField(max_length=10, null=True, blank=True, unique=True, verbose_name='Cédula')
    ruc = models.CharField(max_length=13, null=True, blank=True, unique=True, verbose_name='RUC')
    mobile = models.CharField(max_length=10, null=True, blank=True, help_text='Ingrese un teléfono', verbose_name='Teléfono')
    address = models.CharField(max_length=500, null=True, blank=True, help_text='Ingrese una dirección', verbose_name='Dirección')
    business_name = models.CharField(max_length=250, null=True, blank=True, verbose_name='Razón Social')
    commercial_name = models.CharField(max_length=250, null=True, blank=True, verbose_name='Nombre Comercial')
    tradename = models.CharField(max_length=200, null=True, blank=True, verbose_name='Nombre Comercial Facturación')
    is_business = models.BooleanField(default=False, verbose_name='Es Empresa')
    is_credit_authorized = models.BooleanField(default=False, verbose_name='Está autorizado para crédito')
    credit_limit = models.DecimalField(max_digits=9, decimal_places=2, default=0.00, verbose_name='Límite de crédito')

    def __str__(self):
        return self.get_full_name()

    @property
    def identification(self):
        # Compatibilidad: usar ruc si existe, caso contrario dni
        return self.ruc or self.dni or ''

    def get_full_name(self):
        return f'{self.user.names} ({self.identification})'

    def formatted_birthdate(self):
        # birthdate ya no es columna física; devolver cadena vacía o una fecha por defecto
        # Ajustar si en la UI se requiere un valor específico.
        return ''

    def as_dict(self):
        # No incluimos identification_type ni send_email_invoice en model_to_dict porque ya no son
        # columnas físicas en la BD; se añaden manualmente para mantener compatibilidad API/UI.
        item = model_to_dict(self)
        item['text'] = self.get_full_name()
        item['user'] = self.user.as_dict()
        item['birthdate'] = self.formatted_birthdate()
        ident_type = self.identification_type
        item['identification_type'] = {'id': ident_type, 'name': dict(IDENTIFICATION_TYPE).get(ident_type, ident_type)}
        item['identification'] = self.identification
        item['send_email_invoice'] = True  # siempre True según requerimiento
        # Evitar problemas de serialización JSON con Decimal
        if 'credit_limit' in item and item['credit_limit'] is not None:
            try:
                item['credit_limit'] = float(item['credit_limit'])
            except Exception:
                item['credit_limit'] = 0.0
        return item

    @property
    def identification_type(self):
        ident = self.identification
        if len(ident) == 13:
            return '04'
        if len(ident) == 10:
            return '05'
        return '07'

    @property
    def send_email_invoice(self):
        # Campo removido físicamente: siempre debe devolver True
        return True

    class Meta:
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'


class Receipt(models.Model):
    company = models.ForeignKey('pos.Company', null=True, blank=True, related_name='receipts', on_delete=models.CASCADE, verbose_name='Compañía')
    voucher_type = models.CharField(max_length=10, choices=VOUCHER_TYPE, verbose_name='Tipo de Comprobante')
    establishment_code = models.CharField(max_length=3, help_text='Ingrese un código del establecimiento emisor', verbose_name='Código del Establecimiento Emisor')
    issuing_point_code = models.CharField(max_length=3, help_text='Ingrese un código del punto de emisión', verbose_name='Código del Punto de Emisión')
    sequence = models.PositiveIntegerField(default=1, verbose_name='Secuencia actual')

    def __str__(self):
        return f'{self.name} - {self.establishment_code} - {self.issuing_point_code}'

    @property
    def is_ticket(self):
        return self.voucher_type == VOUCHER_TYPE[2][0]

    @property
    def name(self):
        return self.get_voucher_type_display()

    def get_name_file(self):
        return self.remove_accents(self.name.replace(' ', '_').lower()).upper()

    def remove_accents(self, text):
        return ''.join((c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn'))

    def get_sequence(self):
        return f'{self.sequence:09d}'

    def as_dict(self):
        item = model_to_dict(self)
        item['name'] = self.name
        item['voucher_type'] = {'id': self.voucher_type, 'name': self.get_voucher_type_display()}
        return item

    class Meta:
        verbose_name = 'Comprobante'
        verbose_name_plural = 'Comprobantes'


class ExpenseType(models.Model):
    company = models.ForeignKey('pos.Company', null=True, blank=True, related_name='expense_types', on_delete=models.CASCADE, verbose_name='Compañía')
    name = models.CharField(max_length=50, unique=True, help_text='Ingrese un nombre', verbose_name='Nombre')

    def __str__(self):
        return self.name

    def as_dict(self):
        item = model_to_dict(self)
        return item

    class Meta:
        verbose_name = 'Tipo de Gasto'
        verbose_name_plural = 'Tipos de Gastos'
        default_permissions = ()
        permissions = (
            ('view_expense_type', 'Can view Tipo de Gasto'),
            ('add_expense_type', 'Can add Tipo de Gasto'),
            ('change_expense_type', 'Can change Tipo de Gasto'),
            ('delete_expense_type', 'Can delete Tipo de Gasto'),
        )


class Expense(models.Model):
    company = models.ForeignKey('pos.Company', null=True, blank=True, related_name='expenses', on_delete=models.CASCADE, verbose_name='Compañía')
    expense_type = models.ForeignKey(ExpenseType, on_delete=models.PROTECT, verbose_name='Tipo de Gasto')
    description = models.CharField(max_length=500, null=True, blank=True, help_text='Ingrese una descripción', verbose_name='Detalles')
    date_joined = models.DateField(default=datetime.now, verbose_name='Fecha de Registro')
    amount = models.DecimalField(max_digits=9, decimal_places=2, default=0.00, verbose_name='Monto')

    def __str__(self):
        return self.description

    def as_dict(self):
        item = model_to_dict(self)
        item['expense_type'] = self.expense_type.as_dict()
        item['date_joined'] = self.date_joined.strftime('%Y-%m-%d')
        item['amount'] = float(self.amount)
        return item

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        if not self.description:
            self.description = 's/n'
        super(Expense, self).save()

    class Meta:
        verbose_name = 'Gasto'
        verbose_name_plural = 'Gastos'


class Promotion(models.Model):
    company = models.ForeignKey('pos.Company', null=True, blank=True, related_name='promotions', on_delete=models.CASCADE, verbose_name='Compañía')
    start_date = models.DateField(default=datetime.now)
    end_date = models.DateField(default=datetime.now)
    active = models.BooleanField(default=True)

    def __str__(self):
        return str(self.id)

    def as_dict(self):
        item = model_to_dict(self)
        item['start_date'] = self.start_date.strftime('%Y-%m-%d')
        item['end_date'] = self.end_date.strftime('%Y-%m-%d')
        return item

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        self.active = self.end_date > self.start_date
        super(Promotion, self).save()

    class Meta:
        verbose_name = 'Promoción'
        verbose_name_plural = 'Promociones'


class PromotionDetail(models.Model):
    company = models.ForeignKey('pos.Company', null=True, blank=True, related_name='promotion_details', on_delete=models.CASCADE, verbose_name='Compañía')
    promotion = models.ForeignKey(Promotion, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    current_price = models.DecimalField(max_digits=9, decimal_places=4, default=0.00)
    discount = models.DecimalField(max_digits=9, decimal_places=4, default=0.00)
    total_discount = models.DecimalField(max_digits=9, decimal_places=4, default=0.00)
    final_price = models.DecimalField(max_digits=9, decimal_places=4, default=0.00)

    def __str__(self):
        return self.product.name

    def calculate_total_discount(self):
        total_dscto = float(self.current_price) * float(self.discount)
        return math.floor(total_dscto * 10 ** 2) / 10 ** 2

    def as_dict(self):
        item = model_to_dict(self, exclude=['promotion'])
        item['product'] = self.product.as_dict()
        item['current_price'] = float(self.current_price)
        item['discount'] = float(self.discount)
        item['total_discount'] = float(self.total_discount)
        item['final_price'] = float(self.final_price)
        return item

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        self.total_discount = self.calculate_total_discount()
        self.final_price = float(self.current_price) - float(self.total_discount)
        super(PromotionDetail, self).save()

    class Meta:
        verbose_name = 'Detalle Promoción'
        verbose_name_plural = 'Detalle de Promociones'
        default_permissions = ()


class TransactionSummary(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    date_joined = models.DateField(default=datetime.now, verbose_name='Fecha de registro')
    subtotal_without_tax = models.DecimalField(max_digits=9, decimal_places=2, default=0.00, verbose_name='Subtotal sin impuestos')
    subtotal_with_tax = models.DecimalField(max_digits=9, decimal_places=2, default=0.00, verbose_name='Subtotal con impuestos')
    tax = models.DecimalField(max_digits=9, decimal_places=2, default=0.00, verbose_name='IVA')
    total_tax = models.DecimalField(max_digits=9, decimal_places=2, default=0.00, verbose_name='Total de IVA')
    total_discount = models.DecimalField(max_digits=9, decimal_places=2, default=0.00, verbose_name='Valor total del descuento')
    total_amount = models.DecimalField(max_digits=9, decimal_places=2, default=0.00, verbose_name='Total a pagar')

    @property
    def subtotal(self):
        return float(self.subtotal_with_tax) + float(self.subtotal_without_tax)

    @property
    def tax_rate(self):
        return int(self.tax * 100)

    def formatted_date_joined(self):
        return (datetime.strptime(self.date_joined, '%Y-%m-%d') if isinstance(self.date_joined, str) else self.date_joined).strftime('%Y-%m-%d')

    def as_dict(self):
        item = model_to_dict(self, exclude=['company'])
        item['date_joined'] = self.formatted_date_joined()
        item['subtotal_without_tax'] = float(self.subtotal_without_tax)
        item['subtotal_with_tax'] = float(self.subtotal_with_tax)
        item['tax_rate'] = f"{self.tax_rate:.0f}%"
        item['tax'] = f"{self.tax_rate:.0f}%"

        item['total_tax'] = float(self.total_tax)
        item['total_discount'] = float(self.total_discount)
        item['total_amount'] = float(self.total_amount)
        item['subtotal'] = self.subtotal
        return item

    class Meta:
        abstract = True


class ElecBillingBase(TransactionSummary):
    receipt = models.ForeignKey(Receipt, on_delete=models.PROTECT, verbose_name='Tipo de comprobante')
    time_joined = models.DateTimeField(default=datetime.now, verbose_name='Fecha y hora de registro')
    receipt_number = models.CharField(max_length=9, null=True, blank=True, verbose_name='Número de comprobante')
    receipt_number_full = models.CharField(max_length=20, null=True, blank=True, verbose_name='Número completo de comprobante')
    environment_type = models.PositiveIntegerField(choices=ENVIRONMENT_TYPE, default=ENVIRONMENT_TYPE[0][0], verbose_name='Entorno de facturación electrónica')
    access_code = models.CharField(max_length=49, null=True, blank=True, verbose_name='Código de acceso')
    authorized_date = models.DateTimeField(null=True, blank=True, verbose_name='Fecha de autorización')
    authorized_xml = models.FileField(upload_to='authorized_xml/%Y/%m/%d', null=True, blank=True, verbose_name='XML Autorizado')
    authorized_pdf = models.FileField(upload_to='pdf_authorized/%Y/%m/%d', null=True, blank=True, verbose_name='PDF Autorizado')
    create_electronic_invoice = models.BooleanField(default=True, verbose_name='Crear factura electrónica')
    additional_info = models.JSONField(default=dict, verbose_name='Información adicional')
    status = models.CharField(max_length=50, choices=INVOICE_STATUS, default=INVOICE_STATUS[0][0], verbose_name='Estado')

    class Meta:
        abstract = True

    @property
    def voucher_type_code(self):
        if isinstance(self, Invoice):
            return VOUCHER_TYPE[0][0]
        elif isinstance(self, CreditNote):
            return VOUCHER_TYPE[1][0]
        return VOUCHER_TYPE[2][0]

    @property
    def receipt_template_name(self):
        if self.receipt.voucher_type == VOUCHER_TYPE[0][0]:
            return 'invoice/invoice_pdf.html'
        if self.receipt.voucher_type == VOUCHER_TYPE[1][0]:
            return 'credit_note/invoice_pdf.html'
        return None

    @property
    def access_code_barcode(self):
        buffer = BytesIO()
        barcode_image = barcode.Code128(self.access_code, writer=barcode.writer.ImageWriter())
        barcode_image.write(buffer, options={'text_distance': 3.0, 'font_size': 6})
        encoded_image = base64.b64encode(buffer.getvalue()).decode('ascii')
        return f"data:image/png;base64,{encoded_image}"

    def is_invoice(self):
        return self.receipt.voucher_type == VOUCHER_TYPE[0][0]

    def is_credit_note(self):
        return self.receipt.voucher_type == VOUCHER_TYPE[1][0]

    def formatted_time_joined(self):
        return self.time_joined.strftime('%Y-%m-%d %H:%M:%S')

    def formatted_authorized_date(self):
        return self.authorized_date.strftime('%Y-%m-%d') if self.authorized_date else ''

    def get_authorized_xml(self):
        if self.authorized_xml:
            return f'{settings.MEDIA_URL}{self.authorized_xml}'
        return None

    def get_authorized_pdf(self):
        if self.authorized_pdf:
            return f'{settings.MEDIA_URL}{self.authorized_pdf}'
        return None

    def as_dict(self):
        item = super().as_dict()
        item['receipt'] = self.receipt.as_dict()
        item['time_joined'] = self.formatted_time_joined()
        item['authorized_date'] = self.formatted_authorized_date()
        item['authorized_xml'] = self.get_authorized_xml()
        item['authorized_pdf'] = self.get_authorized_pdf()
        item['status'] = {'id': self.status, 'name': self.get_status_display()}
        item['is_invoice'] = self.is_invoice()
        item['is_credit_note'] = self.is_credit_note()
        return item

    def check_sequential_error(self, errors):
        if 'error' in errors and isinstance(errors['error'], dict):
            if 'errors' in errors['error']:
                for error in errors['error']['errors']:
                    if 'mensaje' in error and error['mensaje'] == 'ERROR SECUENCIAL REGISTRADO':
                        return True
        return False

    def create_receipt_error(self, errors, change_status=True):
        try:
            receipt_error = ReceiptError()
            receipt_error.receipt_id = self.receipt_id
            receipt_error.stage = errors['stage']
            receipt_error.receipt_number_full = self.receipt_number_full
            if type(errors) is str:
                receipt_error.errors = {'error': errors}
            else:
                receipt_error.errors = errors
            receipt_error.environment_type = self.environment_type
            receipt_error.save()
        except:
            pass
        finally:
            if self.check_sequential_error(errors=errors) and change_status:
                self.status = INVOICE_STATUS[4][0]
                self.edit()
                self.receipt.sequence = self.receipt.sequence + 1
                self.receipt.save()

    def generate_receipt_number(self, increase=True):
        if isinstance(self.receipt.sequence, str):
            self.receipt.sequence = int(self.receipt.sequence)
        number = self.receipt.sequence + 1 if increase else self.receipt.sequence
        return f'{number:09d}'

    def generate_receipt_number_full(self):
        if self.receipt_id is None:
            self.receipt = Receipt.objects.get(voucher_type=self.voucher_type_code, establishment_code=self.company.establishment_code, issuing_point_code=self.company.issuing_point_code)
        self.receipt_number = self.generate_receipt_number()
        return self.get_receipt_number_full()

    def get_receipt_number_full(self):
        return f'{self.receipt.establishment_code}-{self.receipt.issuing_point_code}-{self.receipt_number}'

    def create_authorized_pdf(self):
        try:
            pdf_file = PDFCreator(template_name=self.receipt_template_name).create(context={'object': self})
            with tempfile.NamedTemporaryFile(delete=True) as file_temp:
                file_temp.write(pdf_file)
                file_temp.flush()
                self.authorized_pdf.save(name=f'{self.receipt.get_name_file()}-{self.receipt_number_full}.pdf', content=File(file_temp))
        except:
            pass

    def generate_electronic_invoice_document(self):
        sri = SRI()
        response = sri.create_xml(self)
        if response['resp']:
            response = sri.firm_xml(instance=self, xml=response['xml'])
            if response['resp']:
                response = sri.validate_xml(instance=self, xml=response['xml'])
                if response['resp']:
                    response = sri.authorize_xml(instance=self)
                    index = 1
                    while not response['resp'] and index < 3:
                        time.sleep(1)
                        response = sri.authorize_xml(instance=self)
                        index += 1
                    return response
        return response

    def get_client_from_model(self):
        return self.customer if isinstance(self, Invoice) else self.invoice.customer if isinstance(self, CreditNote) else None


#envio facturas
    def send_invoice_files_to_customer(self):
        response = {'resp': True}
        try:
            customer = self.get_client_from_model()

            message = MIMEMultipart('alternative')
            message['Subject'] = f'Factura electrónica – {self.receipt_number_full}'
            message['From'] = formataddr(("OptimusPos Facturación", settings.EMAIL_HOST_USER))
            message['To'] = customer.user.email

            # --------- HTML Responsive ------------
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body {{
                margin:0;
                padding:0;
                background:#f6f8fa;
                font-family:'Segoe UI',Roboto,Arial,sans-serif;
                color:#333;
                }}
                .container {{
                max-width:600px;
                margin:20px auto;
                background:#ffffff;
                border-radius:12px;
                box-shadow:0 4px 12px rgba(0,0,0,0.1);
                overflow:hidden;
                }}
                .header {{
                background:linear-gradient(135deg,#4e73df,#2e59d9);
                color:#fff;
                text-align:center;
                padding:30px 20px;
                }}
                .header h1 {{
                margin:0;
                font-size:28px;
                letter-spacing:0.5px;
                }}
                .content {{
                padding:25px 20px;
                }}
                .content h2 {{
                margin-top:0;
                color:#2e59d9;
                }}
                .info-table {{
                width:100%;
                border-collapse:collapse;
                margin:20px 0;
                }}
                .info-table td {{
                padding:10px;
                border-top:1px solid #e1e4e8;
                }}
                .btn {{
                display:inline-block;
                margin-top:20px;
                background:#2e59d9;
                color:#fff !important;
                text-decoration:none;
                padding:12px 24px;
                border-radius:6px;
                font-weight:600;
                }}
                .footer {{
                text-align:center;
                padding:20px;
                font-size:12px;
                color:#888;
                }}
                @media screen and (max-width: 600px) {{
                .header h1 {{ font-size:24px; }}
                .content h2 {{ font-size:20px; }}
                }}
            </style>
            </head>
            <body>
            <div class="container">
                <div class="header">
                <h1>OptimusPos Facturación</h1>
                </div>
                <div class="content">
                <h2>Hola {customer.user.names.title()}</h2>
                <p>
                    Gracias por confiar en <strong>{self.company.commercial_name}</strong>. 
                    Adjuntamos su documento electrónico en formato <strong>PDF</strong> y <strong>XML</strong>.
                </p>
                <table class="info-table">
                    <tr><td><strong>Documento:</strong></td><td>{self.receipt.name} {self.receipt_number_full}</td></tr>
                    <tr><td><strong>Fecha:</strong></td><td>{self.formatted_date_joined()}</td></tr>
                    <tr><td><strong>Monto:</strong></td><td>${float(round(self.total_amount, 2))}</td></tr>
                    <tr><td><strong>Código de acceso:</strong></td><td>{self.access_code}</td></tr>
                    <tr><td><strong>Autorización:</strong></td><td>{self.access_code}</td></tr>
                </table>
                <p>
                    Puede descargar los archivos directamente desde este correo o desde su cuenta en nuestro sistema.
                </p>
                
                </div>
                <div class="footer">
                © {self.company.commercial_name} – Todos los derechos reservados
                </div>
            </div>
            </body>
            </html>
            """
            message.attach(MIMEText(html_content, 'html'))

            # -------- Adjuntar archivos --------
            pdf_file = self.create_invoice_pdf()
            pdf_part = MIMEApplication(pdf_file, _subtype='pdf')
            pdf_part.add_header('Content-Disposition', 'attachment',
                                filename=f'{self.access_code}.pdf')
            message.attach(pdf_part)

            with open(f'{settings.BASE_DIR}{self.get_authorized_xml()}', 'rb') as f:
                xml_part = MIMEApplication(f.read())
                xml_part.add_header('Content-Disposition', 'attachment',
                                    filename=f'{self.access_code}.xml')
                message.attach(xml_part)

            # -------- Envío --------
            server = smtplib.SMTP_SSL(settings.EMAIL_HOST, 465)
            server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
            server.sendmail(settings.EMAIL_HOST_USER, [customer.user.email], message.as_string())
            server.quit()

        except Exception as e:
            response = {'resp': False, 'error': str(e)}
        return response

    def receipt_number_is_null(self):
        return self.receipt_number_full is None or self.receipt_number is None

    def save_sequence_number(self):
        self.receipt.sequence = int(self.receipt_number)
        self.receipt.save()

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        if self.pk is None and not self.receipt_number_is_null():
            self.save_sequence_number()
        super(ElecBillingBase, self).save()

    def edit(self):
        super(ElecBillingBase, self).save()


class ElecBillingDetailBase(models.Model):
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.IntegerField(default=0)
    price = models.DecimalField(max_digits=9, decimal_places=4, default=0.00)
    price_with_tax = models.DecimalField(max_digits=9, decimal_places=4, default=0.00)
    subtotal = models.DecimalField(max_digits=9, decimal_places=4, default=0.00)
    tax = models.DecimalField(max_digits=9, decimal_places=4, default=0.00)
    total_tax = models.DecimalField(max_digits=9, decimal_places=4, default=0.00)
    discount = models.DecimalField(max_digits=9, decimal_places=4, default=0.00)
    total_discount = models.DecimalField(max_digits=9, decimal_places=4, default=0.00)
    total_amount = models.DecimalField(max_digits=9, decimal_places=4, default=0.00)

    @property
    def tax_rate(self):
        return self.tax * 100

    @property
    def discount_rate(self):
        return self.discount * 100

    def as_dict(self):
        item = model_to_dict(self)
        item['product'] = self.product.as_dict()
        item['tax'] = float(self.tax)
        item['price'] = float(self.price)
        item['price_with_tax'] = float(self.price_with_tax)
        item['subtotal'] = float(self.subtotal)
        item['tax'] = float(self.tax)
        item['total_tax'] = float(self.total_tax)
        item['discount'] = float(self.discount)
        item['total_discount'] = float(self.total_discount)
        item['total_amount'] = float(self.total_amount)
        return item

    class Meta:
        abstract = True


class Invoice(ElecBillingBase):
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, verbose_name='Cliente')
    employee = models.ForeignKey(User, null=True, blank=True, on_delete=models.PROTECT, verbose_name='Empleado')
    payment_type = models.CharField(choices=PAYMENT_TYPE, max_length=50, default=PAYMENT_TYPE[0][0], verbose_name='Forma de pago')
    payment_method = models.CharField(choices=INVOICE_PAYMENT_METHOD, max_length=50, default=INVOICE_PAYMENT_METHOD[5][0], verbose_name='Método de pago')
    time_limit = models.IntegerField(default=31, verbose_name='Plazo')
    end_credit = models.DateField(default=datetime.now, verbose_name='Fecha limite de crédito')
    cash = models.DecimalField(max_digits=9, decimal_places=2, default=0.00, verbose_name='Efectivo recibido')
    change = models.DecimalField(max_digits=9, decimal_places=2, default=0.00, verbose_name='Cambio')
    is_draft_invoice = models.BooleanField(default=False, verbose_name='Factura borrador')

    def __str__(self):
        return self.get_full_name()

    @property
    def subtotal_without_taxes(self):
        return float(self.invoicedetail_set.filter().aggregate(result=Coalesce(Sum('subtotal'), 0.00, output_field=FloatField()))['result'])

    def get_full_name(self):
        return f'{self.receipt_number_full} / {self.customer.get_full_name()})'

    def calculate_detail(self):
        for detail in self.invoicedetail_set.filter():
            detail.price = float(detail.price)
            detail.tax = float(self.tax)
            detail.price_with_tax = detail.price + (detail.price * detail.tax)
            detail.subtotal = detail.price * detail.quantity
            detail.total_discount = detail.subtotal * float(detail.discount)
            detail.total_tax = (detail.subtotal - detail.total_discount) * detail.tax
            detail.total_amount = detail.subtotal - detail.total_discount
            detail.save()

    def calculate_invoice(self):
        self.subtotal_without_tax = float(self.invoicedetail_set.filter(product__has_tax=False).aggregate(result=Coalesce(Sum('total_amount'), 0.00, output_field=FloatField()))['result'])
        self.subtotal_with_tax = float(self.invoicedetail_set.filter(product__has_tax=True).aggregate(result=Coalesce(Sum('total_amount'), 0.00, output_field=FloatField()))['result'])
        self.total_tax = round(self.invoicedetail_set.filter(product__has_tax=True).aggregate(result=Coalesce(Sum('total_tax'), 0.00, output_field=FloatField()))['result'], 2)
        self.total_discount = float(self.invoicedetail_set.filter().aggregate(result=Coalesce(Sum('total_discount'), 0.00, output_field=FloatField()))['result'])
        self.total_amount = round(self.subtotal, 2) + float(self.total_tax)
        self.save()

    def recalculate_invoice(self):
        self.calculate_detail()
        self.calculate_invoice()

    def create_xml_document(self):
        access_key = SRI().create_access_key(self)
        root = ElementTree.Element('factura', id="comprobante", version="1.0.0")
        # infoTributaria
        xml_tax_info = ElementTree.SubElement(root, 'infoTributaria')
        ElementTree.SubElement(xml_tax_info, 'ambiente').text = str(self.company.environment_type)
        ElementTree.SubElement(xml_tax_info, 'tipoEmision').text = str(self.company.emission_type)
        ElementTree.SubElement(xml_tax_info, 'razonSocial').text = self.company.company_name
        ElementTree.SubElement(xml_tax_info, 'nombreComercial').text = self.company.commercial_name
        ElementTree.SubElement(xml_tax_info, 'ruc').text = self.company.ruc
        ElementTree.SubElement(xml_tax_info, 'claveAcceso').text = access_key
        ElementTree.SubElement(xml_tax_info, 'codDoc').text = self.receipt.voucher_type
        ElementTree.SubElement(xml_tax_info, 'estab').text = self.receipt.establishment_code
        ElementTree.SubElement(xml_tax_info, 'ptoEmi').text = self.receipt.issuing_point_code
        ElementTree.SubElement(xml_tax_info, 'secuencial').text = self.receipt_number
        ElementTree.SubElement(xml_tax_info, 'dirMatriz').text = self.company.main_address
        if not self.company.is_popular_regime:
            ElementTree.SubElement(xml_tax_info, 'contribuyenteRimpe').text = self.company.regimen_rimpe
        if self.company.retention_agent == RETENTION_AGENT[0][0]:
            ElementTree.SubElement(xml_tax_info, 'agenteRetencion').text = '1'
        # infoFactura
        xml_info_invoice = ElementTree.SubElement(root, 'infoFactura')
        ElementTree.SubElement(xml_info_invoice, 'fechaEmision').text = datetime.now().strftime('%d/%m/%Y')
        ElementTree.SubElement(xml_info_invoice, 'dirEstablecimiento').text = self.company.establishment_address
        ElementTree.SubElement(xml_info_invoice, 'obligadoContabilidad').text = self.company.obligated_accounting
        ElementTree.SubElement(xml_info_invoice, 'tipoIdentificacionComprador').text = self.customer.identification_type
        ElementTree.SubElement(xml_info_invoice, 'razonSocialComprador').text = self.customer.user.names
        ElementTree.SubElement(xml_info_invoice, 'identificacionComprador').text = self.customer.dni
        ElementTree.SubElement(xml_info_invoice, 'direccionComprador').text = self.customer.address
        ElementTree.SubElement(xml_info_invoice, 'totalSinImpuestos').text = f'{self.subtotal:.2f}'
        ElementTree.SubElement(xml_info_invoice, 'totalDescuento').text = f'{self.total_discount:.2f}'
        # totalConImpuestos
        xml_total_with_taxes = ElementTree.SubElement(xml_info_invoice, 'totalConImpuestos')
        # totalImpuesto
        if self.subtotal_without_tax != 0.0000:
            subtotal_without_tax = ElementTree.SubElement(xml_total_with_taxes, 'totalImpuesto')
            ElementTree.SubElement(subtotal_without_tax, 'codigo').text = str(TAX_CODES[0][0])
            ElementTree.SubElement(subtotal_without_tax, 'codigoPorcentaje').text = '0'
            ElementTree.SubElement(subtotal_without_tax, 'baseImponible').text = f'{self.subtotal_without_tax:.2f}'
            ElementTree.SubElement(subtotal_without_tax, 'valor').text = '0.00'
        if self.subtotal_with_tax != 0.0000:
            subtotal_with_tax = ElementTree.SubElement(xml_total_with_taxes, 'totalImpuesto')
            ElementTree.SubElement(subtotal_with_tax, 'codigo').text = str(TAX_CODES[0][0])
            ElementTree.SubElement(subtotal_with_tax, 'codigoPorcentaje').text = str(self.company.tax_percentage)
            ElementTree.SubElement(subtotal_with_tax, 'baseImponible').text = f'{self.subtotal_with_tax:.2f}'
            ElementTree.SubElement(subtotal_with_tax, 'valor').text = f'{self.total_tax:.2f}'
        ElementTree.SubElement(xml_info_invoice, 'propina').text = '0.00'
        ElementTree.SubElement(xml_info_invoice, 'importeTotal').text = f'{self.total_amount:.2f}'
        ElementTree.SubElement(xml_info_invoice, 'moneda').text = 'DOLAR'
        # pagos
        xml_payments = ElementTree.SubElement(xml_info_invoice, 'pagos')
        xml_payment = ElementTree.SubElement(xml_payments, 'pago')
        ElementTree.SubElement(xml_payment, 'formaPago').text = self.payment_method
        ElementTree.SubElement(xml_payment, 'total').text = f'{self.total_amount:.2f}'
        ElementTree.SubElement(xml_payment, 'plazo').text = str(self.time_limit)
        ElementTree.SubElement(xml_payment, 'unidadTiempo').text = 'dias'
        # detalles
        xml_details = ElementTree.SubElement(root, 'detalles')
        for detail in self.invoicedetail_set.all():
            xml_detail = ElementTree.SubElement(xml_details, 'detalle')
            ElementTree.SubElement(xml_detail, 'codigoPrincipal').text = detail.product.code
            ElementTree.SubElement(xml_detail, 'descripcion').text = detail.product.name
            ElementTree.SubElement(xml_detail, 'cantidad').text = f'{detail.quantity:.2f}'
            ElementTree.SubElement(xml_detail, 'precioUnitario').text = f'{detail.price:.2f}'
            ElementTree.SubElement(xml_detail, 'descuento').text = f'{detail.total_discount:.2f}'
            ElementTree.SubElement(xml_detail, 'precioTotalSinImpuesto').text = f'{detail.total_amount:.2f}'
            xml_taxes = ElementTree.SubElement(xml_detail, 'impuestos')
            xml_tax = ElementTree.SubElement(xml_taxes, 'impuesto')
            ElementTree.SubElement(xml_tax, 'codigo').text = str(TAX_CODES[0][0])
            if detail.product.has_tax:
                ElementTree.SubElement(xml_tax, 'codigoPorcentaje').text = str(self.company.tax_percentage)
                ElementTree.SubElement(xml_tax, 'tarifa').text = f'{detail.tax_rate:.2f}'
                ElementTree.SubElement(xml_tax, 'baseImponible').text = f'{detail.total_amount:.2f}'
                ElementTree.SubElement(xml_tax, 'valor').text = f'{detail.total_tax:.2f}'
            else:
                ElementTree.SubElement(xml_tax, 'codigoPorcentaje').text = "0"
                ElementTree.SubElement(xml_tax, 'tarifa').text = "0"
                ElementTree.SubElement(xml_tax, 'baseImponible').text = f'{detail.total_amount:.2f}'
                ElementTree.SubElement(xml_tax, 'valor').text = "0"
        return ElementTree.tostring(root, xml_declaration=True, encoding='utf-8').decode('utf-8').replace("'", '"'), access_key

    def create_invoice_pdf(self):
        template_name = 'invoice/invoice_pdf.html'
        return PDFCreator(template_name=template_name).create(context={'object': self})

    def as_dict(self):
        item = super().as_dict()
        item['text'] = self.get_full_name()
        item['customer'] = self.customer.as_dict()
        item['employee'] = self.employee.as_dict() if self.employee else dict()
        item['payment_method'] = {'id': self.payment_method, 'name': self.get_payment_method_display()}
        item['payment_type'] = {'id': self.payment_type, 'name': self.get_payment_type_display()}
        item['end_credit'] = self.end_credit.strftime('%Y-%m-%d')
        item['cash'] = float(self.cash)
        item['change'] = float(self.change)
        return item

    class Meta:
        verbose_name = 'Factura'
        verbose_name_plural = 'Facturas'
        default_permissions = ()
        permissions = (
            ('view_invoice_admin', 'Can view Factura'),
            ('add_invoice_admin', 'Can add Factura'),
            ('change_invoice_admin', 'Can update Factura'),
            ('delete_invoice_admin', 'Can delete Factura'),
            ('view_invoice_customer', 'Can view Factura | Cliente'),
            ('print_invoice', 'Can print Factura'),
        )
        ordering = ['id']


class InvoiceDetail(ElecBillingDetailBase):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE)
    # company derivada de invoice.company (no duplicamos por ahora)

    def __str__(self):
        return self.product.name

    def deduct_product_stock(self):
        if (not self.invoice.is_draft_invoice and self.invoice.create_electronic_invoice) or self.invoice.receipt.is_ticket:
            if self.product.is_inventoried:
                self.product.stock -= self.quantity
                self.product.save()

    def as_dict(self):
        return super().as_dict()

    class Meta:
        verbose_name = 'Detalle de Factura'
        verbose_name_plural = 'Detalle de Facturas'
        default_permissions = ()
        ordering = ['id']


class AccountReceivable(models.Model):
    company = models.ForeignKey('pos.Company', null=True, blank=True, related_name='accounts_receivable', on_delete=models.CASCADE, verbose_name='Compañía')
    invoice = models.ForeignKey(Invoice, on_delete=models.PROTECT)
    date_joined = models.DateField(default=datetime.now)
    end_date = models.DateField(default=datetime.now)
    debt = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)
    balance = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.get_full_name()

    def formatted_date_joined(self):
        return self.date_joined.strftime('%Y-%m-%d')

    def get_full_name(self):
        return f"{self.invoice.customer.user.names} ({self.invoice.customer.dni}) / {self.formatted_date_joined()} / ${f'{self.debt:.2f}'}"

    def validate_debt(self):
        try:
            balance = self.accountreceivablepayment_set.aggregate(result=Coalesce(Sum('amount'), 0.00, output_field=FloatField()))['result']
            self.balance, self.active = float(self.debt) - float(balance), (float(self.debt) - float(balance)) > 0.00
            self.save()
        except:
            pass

    def as_dict(self):
        item = model_to_dict(self)
        item['text'] = self.get_full_name()
        item['invoice'] = self.invoice.as_dict()
        item['date_joined'] = self.date_joined.strftime('%Y-%m-%d')
        item['end_date'] = self.end_date.strftime('%Y-%m-%d')
        item['debt'] = float(self.debt)
        item['balance'] = float(self.balance)
        return item

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        if not self.pk:
            self.balance = self.debt
        super(AccountReceivable, self).save()

    class Meta:
        verbose_name = 'Cuenta por cobrar'
        verbose_name_plural = 'Cuentas por cobrar'
        default_permissions = ()
        permissions = (
            ('view_account_receivable', 'Can view Cuenta por cobrar'),
            ('add_account_receivable', 'Can add Cuenta por cobrar'),
            ('delete_account_receivable', 'Can delete Cuenta por cobrar'),
        )


class AccountReceivablePayment(models.Model):
    company = models.ForeignKey('pos.Company', null=True, blank=True, related_name='accounts_receivable_payments', on_delete=models.CASCADE, verbose_name='Compañía')
    account_receivable = models.ForeignKey(AccountReceivable, on_delete=models.CASCADE, verbose_name='Cuenta por cobrar')
    date_joined = models.DateField(default=datetime.now, verbose_name='Fecha de registro')
    description = models.CharField(max_length=500, null=True, blank=True, help_text='Ingrese una descripción', verbose_name='Detalles')
    amount = models.DecimalField(max_digits=9, decimal_places=2, default=0.00, verbose_name='Monto')

    def __str__(self):
        return self.account_receivable.id

    def as_dict(self):
        item = model_to_dict(self, exclude=['ctas_collect'])
        item['date_joined'] = self.date_joined.strftime('%Y-%m-%d')
        item['amount'] = float(self.amount)
        return item

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        if not self.description:
            self.description = 's/n'
        super(AccountReceivablePayment, self).save()
        self.account_receivable.validate_debt()

    def delete(self, using=None, keep_parents=False):
        account_receivable = self.account_receivable
        super(AccountReceivablePayment, self).delete()
        account_receivable.validate_debt()

    class Meta:
        verbose_name = 'Detalle de una Cuenta por cobrar'
        verbose_name_plural = 'Detalles de unas Cuentas por cobrar'
        default_permissions = ()


class CreditNote(ElecBillingBase):
    invoice = models.ForeignKey(Invoice, on_delete=models.PROTECT, verbose_name='Factura')
    motive = models.CharField(max_length=300, null=True, blank=True, help_text='Ingrese una descripción', verbose_name='Motivo')

    def __str__(self):
        return self.motive

    @property
    def subtotal_without_taxes(self):
        return float(self.creditnotedetail_set.filter().aggregate(result=Coalesce(Sum('subtotal'), 0.00, output_field=FloatField()))['result'])

    def calculate_detail(self):
        for detail in self.creditnotedetail_set.filter():
            detail.price = float(detail.price)
            detail.tax = float(self.tax)
            detail.price_with_tax = detail.price + (detail.price * detail.tax)
            detail.subtotal = detail.price * detail.quantity
            detail.total_discount = detail.subtotal * float(detail.discount)
            detail.total_tax = (detail.subtotal - detail.total_discount) * detail.tax
            detail.total_amount = detail.subtotal - detail.total_discount
            detail.save()

    def calculate_invoice(self):
        self.subtotal_without_tax = float(self.creditnotedetail_set.filter(product__has_tax=False).aggregate(result=Coalesce(Sum('total_amount'), 0.00, output_field=FloatField()))['result'])
        self.subtotal_with_tax = float(self.creditnotedetail_set.filter(product__has_tax=True).aggregate(result=Coalesce(Sum('total_amount'), 0.00, output_field=FloatField()))['result'])
        self.total_tax = round(self.creditnotedetail_set.filter(product__has_tax=True).aggregate(result=Coalesce(Sum('total_tax'), 0.00, output_field=FloatField()))['result'], 2)
        self.total_discount = float(self.creditnotedetail_set.filter().aggregate(result=Coalesce(Sum('total_discount'), 0.00, output_field=FloatField()))['result'])
        self.total_amount = round(self.subtotal, 2) + round(self.total_tax, 2)
        self.save()

    def recalculate_invoice(self):
        self.calculate_detail()
        self.calculate_invoice()

    def create_xml_document(self):
        access_key = SRI().create_access_key(self)
        root = ElementTree.Element('notaCredito', id="comprobante", version="1.1.0")
        # infoTributaria
        xml_tax_info = ElementTree.SubElement(root, 'infoTributaria')
        ElementTree.SubElement(xml_tax_info, 'ambiente').text = str(self.company.environment_type)
        ElementTree.SubElement(xml_tax_info, 'tipoEmision').text = str(self.company.emission_type)
        ElementTree.SubElement(xml_tax_info, 'razonSocial').text = self.company.company_name
        ElementTree.SubElement(xml_tax_info, 'nombreComercial').text = self.company.commercial_name
        ElementTree.SubElement(xml_tax_info, 'ruc').text = self.company.ruc
        ElementTree.SubElement(xml_tax_info, 'claveAcceso').text = access_key
        ElementTree.SubElement(xml_tax_info, 'codDoc').text = self.receipt.voucher_type
        ElementTree.SubElement(xml_tax_info, 'estab').text = self.receipt.establishment_code
        ElementTree.SubElement(xml_tax_info, 'ptoEmi').text = self.receipt.issuing_point_code
        ElementTree.SubElement(xml_tax_info, 'secuencial').text = self.receipt_number
        ElementTree.SubElement(xml_tax_info, 'dirMatriz').text = self.company.main_address
        if not self.company.is_popular_regime:
            ElementTree.SubElement(xml_tax_info, 'contribuyenteRimpe').text = self.company.regimen_rimpe
        if self.company.retention_agent == RETENTION_AGENT[0][0]:
            ElementTree.SubElement(xml_tax_info, 'agenteRetencion').text = '1'
        # infoNotaCredito
        xml_info_invoice = ElementTree.SubElement(root, 'infoNotaCredito')
        ElementTree.SubElement(xml_info_invoice, 'fechaEmision').text = datetime.now().strftime('%d/%m/%Y')
        ElementTree.SubElement(xml_info_invoice, 'dirEstablecimiento').text = self.company.establishment_address
        ElementTree.SubElement(xml_info_invoice, 'tipoIdentificacionComprador').text = self.invoice.customer.identification_type
        ElementTree.SubElement(xml_info_invoice, 'razonSocialComprador').text = self.invoice.customer.user.names
        ElementTree.SubElement(xml_info_invoice, 'identificacionComprador').text = self.invoice.customer.dni
        if not self.company.special_taxpayer == '000':
            ElementTree.SubElement(xml_info_invoice, 'contribuyenteEspecial').text = self.company.special_taxpayer
        ElementTree.SubElement(xml_info_invoice, 'obligadoContabilidad').text = self.company.obligated_accounting
        ElementTree.SubElement(xml_info_invoice, 'rise').text = 'Contribuyente Régimen Simplificado RISE'
        ElementTree.SubElement(xml_info_invoice, 'codDocModificado').text = self.invoice.receipt.voucher_type
        ElementTree.SubElement(xml_info_invoice, 'numDocModificado').text = self.invoice.receipt_number_full
        ElementTree.SubElement(xml_info_invoice, 'fechaEmisionDocSustento').text = self.invoice.date_joined.strftime('%d/%m/%Y')
        ElementTree.SubElement(xml_info_invoice, 'totalSinImpuestos').text = f'{self.subtotal:.2f}'
        ElementTree.SubElement(xml_info_invoice, 'valorModificacion').text = f'{self.total_amount:.2f}'
        ElementTree.SubElement(xml_info_invoice, 'moneda').text = 'DOLAR'
        # totalConImpuestos
        xml_total_with_taxes = ElementTree.SubElement(xml_info_invoice, 'totalConImpuestos')
        # totalImpuesto
        if self.subtotal_without_tax != 0.0000:
            xml_total_tax = ElementTree.SubElement(xml_total_with_taxes, 'totalImpuesto')
            ElementTree.SubElement(xml_total_tax, 'codigo').text = str(TAX_CODES[0][0])
            ElementTree.SubElement(xml_total_tax, 'codigoPorcentaje').text = '0'
            ElementTree.SubElement(xml_total_tax, 'baseImponible').text = f'{self.subtotal_without_tax:.2f}'
            ElementTree.SubElement(xml_total_tax, 'valor').text = f'{0:.2f}'
        if self.subtotal_with_tax != 0.0000:
            xml_total_tax2 = ElementTree.SubElement(xml_total_with_taxes, 'totalImpuesto')
            ElementTree.SubElement(xml_total_tax2, 'codigo').text = str(TAX_CODES[0][0])
            ElementTree.SubElement(xml_total_tax2, 'codigoPorcentaje').text = str(self.company.tax_percentage)
            ElementTree.SubElement(xml_total_tax2, 'baseImponible').text = f'{self.subtotal_with_tax:.2f}'
            ElementTree.SubElement(xml_total_tax2, 'valor').text = f'{self.total_tax:.2f}'
        ElementTree.SubElement(xml_info_invoice, 'motivo').text = self.motive
        # detalles
        xml_details = ElementTree.SubElement(root, 'detalles')
        for detail in self.creditnotedetail_set.all():
            xml_detail = ElementTree.SubElement(xml_details, 'detalle')
            ElementTree.SubElement(xml_detail, 'codigoInterno').text = detail.product.code
            ElementTree.SubElement(xml_detail, 'descripcion').text = detail.product.name
            ElementTree.SubElement(xml_detail, 'cantidad').text = f'{detail.quantity:.2f}'
            ElementTree.SubElement(xml_detail, 'precioUnitario').text = f'{detail.price:.2f}'
            ElementTree.SubElement(xml_detail, 'descuento').text = f'{detail.total_discount:.2f}'
            ElementTree.SubElement(xml_detail, 'precioTotalSinImpuesto').text = f'{detail.total_amount:.2f}'
            xml_taxes = ElementTree.SubElement(xml_detail, 'impuestos')
            xml_tax = ElementTree.SubElement(xml_taxes, 'impuesto')
            ElementTree.SubElement(xml_tax, 'codigo').text = str(TAX_CODES[0][0])
            if detail.product.has_tax:
                ElementTree.SubElement(xml_tax, 'codigoPorcentaje').text = str(self.company.tax_percentage)
                ElementTree.SubElement(xml_tax, 'tarifa').text = f'{detail.tax_rate:.2f}'
                ElementTree.SubElement(xml_tax, 'baseImponible').text = f'{detail.total_amount:.2f}'
                ElementTree.SubElement(xml_tax, 'valor').text = f'{detail.total_tax:.2f}'
            else:
                ElementTree.SubElement(xml_tax, 'codigoPorcentaje').text = "0"
                ElementTree.SubElement(xml_tax, 'tarifa').text = "0"
                ElementTree.SubElement(xml_tax, 'baseImponible').text = f'{detail.total_amount:.2f}'
                ElementTree.SubElement(xml_tax, 'valor').text = "0"
        # infoAdicional
        xml_additional_info = ElementTree.SubElement(root, 'infoAdicional')
        if self.invoice.customer.address:
            ElementTree.SubElement(xml_additional_info, 'campoAdicional', nombre='dirCliente').text = self.invoice.customer.address
        if self.invoice.customer.mobile:
            ElementTree.SubElement(xml_additional_info, 'campoAdicional', nombre='telfCliente').text = self.invoice.customer.mobile
        ElementTree.SubElement(xml_additional_info, 'campoAdicional', nombre='Observacion').text = f'NOTA_CREDITO # {self.receipt_number}'
        return ElementTree.tostring(root, xml_declaration=True, encoding='UTF-8').decode('UTF-8').replace("'", '"'), access_key

    def create_invoice_pdf(self):
        template_name = 'credit_note/invoice_pdf.html'
        return PDFCreator(template_name=template_name).create(context={'object': self})

    def return_product_stock(self):
        for detail in self.creditnotedetail_set.filter(product__is_inventoried=True):
            detail.product.stock += detail.quantity
            detail.product.save()

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        if self.pk and self.status == INVOICE_STATUS[1][0]:
            self.return_product_stock()
        super(CreditNote, self).save()

    def as_dict(self):
        item = super().as_dict()
        item['invoice'] = self.invoice.as_dict()
        item['motive'] = self.motive
        return item

    class Meta:
        verbose_name = 'Nota de Crédito'
        verbose_name_plural = 'Notas de Crédito'
        default_permissions = ()
        permissions = (
            ('view_credit_note_admin', 'Can view Nota de Crédito'),
            ('add_credit_note_admin', 'Can add Nota de Crédito'),
            ('delete_credit_note_admin', 'Can delete Nota de Crédito'),
            ('view_credit_note_customer', 'Can view Nota de Crédito | Cliente'),
            ('print_credit_note', 'Can print Nota de Crédito'),
        )
        ordering = ['id']


class CreditNoteDetail(ElecBillingDetailBase):
    credit_note = models.ForeignKey(CreditNote, on_delete=models.CASCADE)
    invoice_detail = models.ForeignKey(InvoiceDetail, on_delete=models.CASCADE)
    # company derivada de credit_note.company

    def __str__(self):
        return self.product.name

    def as_dict(self):
        return super().as_dict()

    class Meta:
        verbose_name = 'Detalle Devolución Ventas'
        verbose_name_plural = 'Detalle Devoluciones Ventas'
        default_permissions = ()
        ordering = ['id']


class Quotation(TransactionSummary):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, verbose_name='Cliente')
    employee = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Empleado')
    active = models.BooleanField(default=True, verbose_name='Activo')

    def __str__(self):
        return f'{self.formatted_number} = {self.customer.get_full_name()}'

    @property
    def subtotal_without_taxes(self):
        return float(self.quotationdetail_set.filter().aggregate(result=Coalesce(Sum('subtotal'), 0.00, output_field=FloatField()))['result'])

    @property
    def formatted_number(self):
        return f'{self.id:08d}'

    @property
    def validate_stock(self):
        return not self.quotationdetail_set.filter(product__is_inventoried=True, product__stock__lt=F('quantity')).exists()

    def send_quotation_by_email(self):
        try:
            print(f"🔍 Iniciando envío de proforma por email...")
            print(f"   - Servidor SMTP: {settings.EMAIL_HOST}:{settings.EMAIL_PORT}")
            print(f"   - Usuario SMTP: {settings.EMAIL_HOST_USER}")
            
            company = Company.objects.first()
            message = MIMEMultipart('alternative')
            message['Subject'] = f'Proforma {self.formatted_number} - {self.customer.get_full_name()}'
            message['From'] = settings.EMAIL_HOST_USER  # Usar variable de entorno
            message['To'] = self.customer.user.email
            
            print(f"   - Destinatario: {self.customer.user.email}")
            
            content = f'Estimado(a)\n\n{self.customer.user.names.upper()}\n\n'
            content += f'La cotización solicitada ha sido enviada a su correo electrónico para su revisión.\n\n'
            part = MIMEText(content)
            message.attach(part)
            
            print(f"   - Generando PDF...")
            context = {'quotation': self}
            pdf_creator = PDFCreator(template_name='quotation/invoice_pdf.html')
            pdf_file = pdf_creator.create(context=context)
            part = MIMEApplication(pdf_file, _subtype='pdf')
            part.add_header('Content-Disposition', 'attachment', filename=f'{self.formatted_number}.pdf')
            message.attach(part)
            
            print(f"   - Conectando al servidor SMTP...")
            server = smtplib.SMTP_SSL(settings.EMAIL_HOST, 465)
            server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
            server.sendmail(settings.EMAIL_HOST_USER, message['To'], message.as_string())
            server.quit()
            
            print(f"✅ Email enviado exitosamente a: {message['To']}")
            
        except Exception as e:
            print(f"❌ ERROR enviando email de proforma: {str(e)}")
            print(f"   - Configuración SMTP: {settings.EMAIL_HOST}:{settings.EMAIL_PORT}")
            print(f"   - Usuario: {settings.EMAIL_HOST_USER}")
            print(f"   - Destinatario: {self.customer.user.email}")
            raise e

    def calculate_detail(self):
        for detail in self.quotationdetail_set.filter():
            detail.price = float(detail.price)
            detail.tax = float(self.tax)
            detail.price_with_tax = detail.price + (detail.price * detail.tax)
            detail.subtotal = detail.price * detail.quantity
            detail.total_discount = detail.subtotal * float(detail.discount)
            detail.total_tax = (detail.subtotal - detail.total_discount) * detail.tax
            detail.total_amount = detail.subtotal - detail.total_discount
            detail.save()

    def calculate_invoice(self):
        self.subtotal_without_tax = float(self.quotationdetail_set.filter(product__has_tax=False).aggregate(result=Coalesce(Sum('total_amount'), 0.00, output_field=FloatField()))['result'])
        self.subtotal_with_tax = float(self.quotationdetail_set.filter(product__has_tax=True).aggregate(result=Coalesce(Sum('total_amount'), 0.00, output_field=FloatField()))['result'])
        self.total_tax = round(self.quotationdetail_set.filter(product__has_tax=True).aggregate(result=Coalesce(Sum('total_tax'), 0.00, output_field=FloatField()))['result'], 2)
        self.total_discount = float(self.quotationdetail_set.filter().aggregate(result=Coalesce(Sum('total_discount'), 0.00, output_field=FloatField()))['result'])
        self.total_amount = round(self.subtotal, 2) + float(self.total_tax)
        self.save()

    def recalculate_invoice(self):
        self.calculate_detail()
        self.calculate_invoice()

    def create_invoice(self, is_draft_invoice=False):
        data = dict()
        with transaction.atomic():
            details = [detail for detail in self.quotationdetail_set.all()]
            invoice = Invoice()
            invoice.date_joined = datetime.now().date()
            invoice.company = self.company
            invoice.environment_type = invoice.company.environment_type
            invoice.receipt = Receipt.objects.get(voucher_type=VOUCHER_TYPE[0][0], establishment_code=invoice.company.establishment_code, issuing_point_code=invoice.company.issuing_point_code)
            invoice.receipt_number = invoice.generate_receipt_number()
            invoice.receipt_number_full = invoice.get_receipt_number_full()
            invoice.employee_id = self.employee_id
            invoice.customer_id = self.customer_id
            invoice.tax = invoice.company.tax_rate
            invoice.cash = float(invoice.total_amount)
            invoice.is_draft_invoice = is_draft_invoice
            invoice.create_electronic_invoice = not is_draft_invoice
            invoice.save()
            for quotation_detail in details:
                product = quotation_detail.product
                invoice_detail = InvoiceDetail.objects.create(
                    invoice_id=invoice.id,
                    product_id=product.id,
                    quantity=quotation_detail.quantity,
                    price=quotation_detail.price,
                    discount=quotation_detail.discount,
                )
                invoice_detail.deduct_product_stock()
            invoice.recalculate_invoice()
            if not invoice.is_draft_invoice:
                data = invoice.generate_electronic_invoice_document()
                if not data['resp']:
                    transaction.set_rollback(True)
        if 'error' in data:
            invoice.create_receipt_error(errors=data, change_status=False)
        return data

    def as_dict(self):
        item = super().as_dict()
        item['number'] = self.formatted_number
        item['customer'] = self.customer.as_dict()
        item['employee'] = self.employee.as_dict()
        return item

    class Meta:
        verbose_name = 'Proforma'
        verbose_name_plural = 'Proformas'
        default_permissions = ()
        permissions = (
            ('view_quotation', 'Can view Proforma'),
            ('add_quotation', 'Can add Proforma'),
            ('change_quotation', 'Can change Proforma'),
            ('delete_quotation', 'Can delete Proforman'),
            ('print_quotation', 'Can print Proforma'),
        )


class QuotationDetail(ElecBillingDetailBase):
    quotation = models.ForeignKey(Quotation, on_delete=models.CASCADE)
    # company derivada de quotation.company

    def __str__(self):
        return self.quotation.__str__()

    def as_dict(self):
        return super().as_dict()

    class Meta:
        verbose_name = 'Proforma Detalle'
        verbose_name_plural = 'Proforma Detalles'
        default_permissions = ()


class ReceiptError(models.Model):
    date_joined = models.DateField(default=datetime.now, verbose_name='Fecha de registro')
    time_joined = models.DateTimeField(default=datetime.now, verbose_name='Hora de registro')
    environment_type = models.PositiveIntegerField(choices=ENVIRONMENT_TYPE, default=ENVIRONMENT_TYPE[0][0], verbose_name='Tipo de entorno')
    receipt_number_full = models.CharField(max_length=50, verbose_name='Número de comprobante')
    receipt = models.ForeignKey(Receipt, on_delete=models.CASCADE, verbose_name='Tipo de Comprobante')
    stage = models.CharField(max_length=20, choices=VOUCHER_STAGE, default=VOUCHER_STAGE[0][0], verbose_name='Etapa')
    errors = models.JSONField(default=dict, verbose_name='Errores')

    def __str__(self):
        return self.stage

    def as_dict(self):
        item = model_to_dict(self)
        item['date_joined'] = self.date_joined.strftime('%Y-%m-%d')
        item['time_joined'] = self.time_joined.strftime('%Y-%m-%d %H:%M')
        item['environment_type'] = {'id': self.environment_type, 'name': self.get_environment_type_display()}
        item['receipt'] = self.receipt.as_dict()
        item['stage'] = {'id': self.stage, 'name': self.get_stage_display()}
        return item

    class Meta:
        verbose_name = 'Error del Comprobante'
        verbose_name_plural = 'Errores de los Comprobantes'
        default_permissions = ()
        permissions = (
            ('view_receipt_error', 'Can view Error del Comprobante'),
            ('delete_receipt_error', 'Can delete Error del Comprobante'),
        )
        ordering = ['id']
