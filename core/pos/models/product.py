from io import BytesIO

import barcode
from barcode import writer
from django.core.files.base import ContentFile
from django.db import models
from django.forms import model_to_dict

from config import settings


class Product(models.Model):
    company = models.ForeignKey('pos.Company', null=True, blank=True, related_name='products', on_delete=models.CASCADE, verbose_name='Compañía')
    name = models.CharField(max_length=150, help_text='Ingrese un nombre', verbose_name='Nombre')
    code = models.CharField(max_length=50, unique=True, help_text='Ingrese un código', verbose_name='Código')
    description = models.CharField(max_length=500, null=True, blank=True, help_text='Ingrese una descripción', verbose_name='Descripción')
    category = models.ForeignKey('pos.Category', on_delete=models.PROTECT, verbose_name='Categoría')
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
        except Exception:  # pragma: no cover - fallback silencioso
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

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        self.generate_barcode()
        super().save(force_insert=force_insert, force_update=force_update, using=using, update_fields=update_fields)

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
