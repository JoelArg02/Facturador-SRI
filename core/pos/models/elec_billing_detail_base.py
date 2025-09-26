from django.db import models
from django.forms import model_to_dict


class ElecBillingDetailBase(models.Model):
    product = models.ForeignKey('pos.Product', on_delete=models.PROTECT)
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
