from datetime import datetime

from django.db import models
from django.forms import model_to_dict


class AccountReceivablePayment(models.Model):
    company = models.ForeignKey('pos.Company', null=True, blank=True, related_name='accounts_receivable_payments', on_delete=models.CASCADE, verbose_name='Compañía')
    account_receivable = models.ForeignKey('pos.AccountReceivable', on_delete=models.CASCADE, verbose_name='Cuenta por cobrar')
    date_joined = models.DateField(default=datetime.now, verbose_name='Fecha de registro')
    description = models.CharField(max_length=500, null=True, blank=True, help_text='Ingrese una descripción', verbose_name='Detalles')
    amount = models.DecimalField(max_digits=9, decimal_places=2, default=0.00, verbose_name='Monto')

    def __str__(self):
        return str(self.account_receivable_id)

    def as_dict(self):
        item = model_to_dict(self, exclude=['ctas_collect'])
        item['date_joined'] = self.date_joined.strftime('%Y-%m-%d')
        item['amount'] = float(self.amount)
        return item

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        if not self.description:
            self.description = 's/n'
        super().save(force_insert=force_insert, force_update=force_update, using=using, update_fields=update_fields)
        self.account_receivable.validate_debt()

    def delete(self, using=None, keep_parents=False):
        account_receivable = self.account_receivable
        super().delete(using=using, keep_parents=keep_parents)
        account_receivable.validate_debt()

    class Meta:
        verbose_name = 'Detalle de una Cuenta por cobrar'
        verbose_name_plural = 'Detalles de unas Cuentas por cobrar'
        default_permissions = ()
