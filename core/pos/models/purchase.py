from django.db import models
from django.db.models.functions import Coalesce
from django.db.models import Sum, FloatField
from django.forms import model_to_dict
from core.pos.choices import PAYMENT_TYPE
from .company import Company
from .catalog import Provider, Product

class Purchase(models.Model):
    company = models.ForeignKey(Company, null=True, blank=True, related_name='purchases', on_delete=models.CASCADE, verbose_name='Compañía')
    number = models.CharField(max_length=8, unique=True, help_text='Ingrese un número de factura', verbose_name='Número de factura')
    provider = models.ForeignKey(Provider, on_delete=models.PROTECT, verbose_name='Proveedor')
    payment_type = models.CharField(max_length=50, choices=PAYMENT_TYPE, default=PAYMENT_TYPE[0][0], verbose_name='Tipo de pago')
    date_joined = models.DateField(default=__import__('datetime').datetime.now, verbose_name='Fecha de registro')
    end_credit = models.DateField(default=__import__('datetime').datetime.now, verbose_name='Fecha de plazo de crédito')
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
        self.calculate_detail(); self.calculate_invoice()
    def delete(self, using=None, keep_parents=False):
        try:
            for i in self.purchasedetail_set.all():
                i.product.stock -= i.quantity
                i.product.save()
        except Exception:
            pass
        super().delete()
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
    company = models.ForeignKey(Company, null=True, blank=True, related_name='purchase_details', on_delete=models.CASCADE, verbose_name='Compañía')
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
