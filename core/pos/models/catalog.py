from django.db import models
from django.forms import model_to_dict
from config import settings
from core.pos.choices import (
    PAYMENT_TYPE, IDENTIFICATION_TYPE, VOUCHER_TYPE, TAX_PERCENTAGE,
    TAX_CODES, ENVIRONMENT_TYPE, INVOICE_STATUS, VOUCHER_STAGE
)

from .company import Company

class Provider(models.Model):
    company = models.ForeignKey(Company, null=True, blank=True, related_name='providers', on_delete=models.CASCADE, verbose_name='Compañía')
    name = models.CharField(max_length=50, unique=True, help_text='Ingrese un nombre', verbose_name='Nombre')
    ruc = models.CharField(max_length=13, unique=True, help_text='Ingrese un RUC', verbose_name='RUC')
    mobile = models.CharField(max_length=10, unique=True, help_text='Ingrese un número de teléfono celular', verbose_name='Teléfono celular')
    address = models.CharField(max_length=500, null=True, blank=True, help_text='Ingrese una dirección', verbose_name='Dirección')
    email = models.CharField(max_length=50, unique=True, help_text='Ingrese un email', verbose_name='Email')
    def __str__(self):
        return f'{self.name} ({self.ruc})'
    def as_dict(self):
        item = model_to_dict(self)
        item['text'] = f'{self.name} ({self.ruc})'
        return item
    class Meta:
        verbose_name = 'Proveedor'
        verbose_name_plural = 'Proveedores'

class Category(models.Model):
    company = models.ForeignKey(Company, null=True, blank=True, related_name='categories', on_delete=models.CASCADE, verbose_name='Compañía')
    name = models.CharField(max_length=50, unique=True, help_text='Ingrese un nombre', verbose_name='Nombre')
    def __str__(self):
        return self.name
    def as_dict(self):
        return model_to_dict(self)
    class Meta:
        verbose_name = 'Categoria'
        verbose_name_plural = 'Categorias'

class Product(models.Model):
    company = models.ForeignKey(Company, null=True, blank=True, related_name='products', on_delete=models.CASCADE, verbose_name='Compañía')
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
        return f'{self.name} ({self.code}) ({self.category.name})'
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
            from io import BytesIO
            import barcode
            from django.core.files.base import ContentFile
            image_io = BytesIO()
            barcode.Gs1_128(self.code, writer=barcode.writer.ImageWriter()).write(image_io)
            filename = f'{self.code}.png'
            self.barcode.save(filename, content=ContentFile(image_io.getvalue()), save=False)
        except Exception:
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
    def save(self, *args, **kwargs):
        self.generate_barcode()
        super().save(*args, **kwargs)
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

class Receipt(models.Model):
    company = models.ForeignKey(Company, null=True, blank=True, related_name='receipts', on_delete=models.CASCADE, verbose_name='Compañía')
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
        import unicodedata
        return ''.join((c for c in unicodedata.normalize('NFD', self.name.replace(' ', '_').lower()) if unicodedata.category(c) != 'Mn')).upper()
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
    company = models.ForeignKey(Company, null=True, blank=True, related_name='expense_types', on_delete=models.CASCADE, verbose_name='Compañía')
    name = models.CharField(max_length=50, unique=True, help_text='Ingrese un nombre', verbose_name='Nombre')
    def __str__(self):
        return self.name
    def as_dict(self):
        return model_to_dict(self)
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
    company = models.ForeignKey(Company, null=True, blank=True, related_name='expenses', on_delete=models.CASCADE, verbose_name='Compañía')
    expense_type = models.ForeignKey(ExpenseType, on_delete=models.PROTECT, verbose_name='Tipo de Gasto')
    description = models.CharField(max_length=500, null=True, blank=True, help_text='Ingrese una descripción', verbose_name='Detalles')
    date_joined = models.DateField(default=__import__('datetime').datetime.now, verbose_name='Fecha de Registro')
    amount = models.DecimalField(max_digits=9, decimal_places=2, default=0.00, verbose_name='Monto')
    def __str__(self):
        return self.description
    def as_dict(self):
        item = model_to_dict(self)
        item['expense_type'] = self.expense_type.as_dict()
        item['date_joined'] = self.date_joined.strftime('%Y-%m-%d')
        item['amount'] = float(self.amount)
        return item
    def save(self, *args, **kwargs):
        if not self.description:
            self.description = 's/n'
        super().save(*args, **kwargs)
    class Meta:
        verbose_name = 'Gasto'
        verbose_name_plural = 'Gastos'

class Promotion(models.Model):
    company = models.ForeignKey(Company, null=True, blank=True, related_name='promotions', on_delete=models.CASCADE, verbose_name='Compañía')
    start_date = models.DateField(default=__import__('datetime').datetime.now)
    end_date = models.DateField(default=__import__('datetime').datetime.now)
    active = models.BooleanField(default=True)
    def __str__(self):
        return str(self.id)
    def as_dict(self):
        item = model_to_dict(self)
        item['start_date'] = self.start_date.strftime('%Y-%m-%d')
        item['end_date'] = self.end_date.strftime('%Y-%m-%d')
        return item
    def save(self, *args, **kwargs):
        self.active = self.end_date > self.start_date
        super().save(*args, **kwargs)
    class Meta:
        verbose_name = 'Promoción'
        verbose_name_plural = 'Promociones'

class PromotionDetail(models.Model):
    company = models.ForeignKey(Company, null=True, blank=True, related_name='promotion_details', on_delete=models.CASCADE, verbose_name='Compañía')
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
        import math
        return math.floor(total_dscto * 10 ** 2) / 10 ** 2
    def as_dict(self):
        item = model_to_dict(self, exclude=['promotion'])
        item['product'] = self.product.as_dict()
        item['current_price'] = float(self.current_price)
        item['discount'] = float(self.discount)
        item['total_discount'] = float(self.total_discount)
        item['final_price'] = float(self.final_price)
        return item
    def save(self, *args, **kwargs):
        self.total_discount = self.calculate_total_discount()
        self.final_price = float(self.current_price) - float(self.total_discount)
        super().save(*args, **kwargs)
    class Meta:
        verbose_name = 'Detalle Promoción'
        verbose_name_plural = 'Detalle de Promociones'
        default_permissions = ()

class ReceiptError(models.Model):
    date_joined = models.DateField(default=__import__('datetime').datetime.now, verbose_name='Fecha de registro')
    time_joined = models.DateTimeField(default=__import__('datetime').datetime.now, verbose_name='Hora de registro')
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
