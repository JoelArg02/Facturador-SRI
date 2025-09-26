from datetime import datetime

from django.db import models
from django.forms import model_to_dict


class TransactionSummary(models.Model):
    company = models.ForeignKey('pos.Company', on_delete=models.CASCADE)
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
        value = self.date_joined
        if isinstance(value, str):
            value = datetime.strptime(value, '%Y-%m-%d')
        return value.strftime('%Y-%m-%d')

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
