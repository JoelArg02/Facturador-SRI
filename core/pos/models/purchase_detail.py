from django.db import models
from django.forms import model_to_dict


class PurchaseDetail(models.Model):
    company = models.ForeignKey('pos.Company', null=True, blank=True, related_name='purchase_details', on_delete=models.CASCADE, verbose_name='Compañía')
    purchase = models.ForeignKey('pos.Purchase', on_delete=models.CASCADE)
    product = models.ForeignKey('pos.Product', on_delete=models.PROTECT)
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
