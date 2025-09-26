from datetime import datetime

from django.db import models
from django.db.models import FloatField, Sum
from django.db.models.functions import Coalesce
from django.forms import model_to_dict


class AccountPayable(models.Model):
    company = models.ForeignKey('pos.Company', null=True, blank=True, related_name='accounts_payable', on_delete=models.CASCADE, verbose_name='Compañía')
    purchase = models.ForeignKey('pos.Purchase', on_delete=models.PROTECT)
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
            self.balance = float(self.debt) - float(balance)
            self.active = self.balance > 0.00
            self.save()
        except Exception:  # pragma: no cover
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

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        if not self.pk:
            self.balance = self.debt
        super().save(force_insert=force_insert, force_update=force_update, using=using, update_fields=update_fields)

    class Meta:
        verbose_name = 'Cuenta por pagar'
        verbose_name_plural = 'Cuentas por pagar'
        default_permissions = ()
        permissions = (
            ('view_account_payable', 'Can view Cuenta por pagar'),
            ('add_account_payable', 'Can add Cuenta por pagar'),
            ('delete_account_payable', 'Can delete Cuenta por pagar'),
        )
