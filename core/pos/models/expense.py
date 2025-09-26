from datetime import datetime

from django.db import models
from django.forms import model_to_dict


class Expense(models.Model):
    company = models.ForeignKey('pos.Company', null=True, blank=True, related_name='expenses', on_delete=models.CASCADE, verbose_name='Compañía')
    expense_type = models.ForeignKey('pos.ExpenseType', on_delete=models.PROTECT, verbose_name='Tipo de Gasto')
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

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        if not self.description:
            self.description = 's/n'
        super().save(force_insert=force_insert, force_update=force_update, using=using, update_fields=update_fields)

    class Meta:
        verbose_name = 'Gasto'
        verbose_name_plural = 'Gastos'
