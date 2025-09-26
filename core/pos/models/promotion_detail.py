import math

from django.db import models
from django.forms import model_to_dict


class PromotionDetail(models.Model):
    company = models.ForeignKey('pos.Company', null=True, blank=True, related_name='promotion_details', on_delete=models.CASCADE, verbose_name='Compañía')
    promotion = models.ForeignKey('pos.Promotion', on_delete=models.CASCADE)
    product = models.ForeignKey('pos.Product', on_delete=models.PROTECT)
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

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        self.total_discount = self.calculate_total_discount()
        self.final_price = float(self.current_price) - float(self.total_discount)
        super().save(force_insert=force_insert, force_update=force_update, using=using, update_fields=update_fields)

    class Meta:
        verbose_name = 'Detalle Promoción'
        verbose_name_plural = 'Detalle de Promociones'
        default_permissions = ()
