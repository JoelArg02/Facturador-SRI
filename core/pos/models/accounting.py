from django.db import models
from django.db.models.functions import Coalesce
from django.db.models import Sum, FloatField
from django.forms import model_to_dict
from .company import Company
from .purchase import Purchase

class AccountPayable(models.Model):
    company = models.ForeignKey(Company, null=True, blank=True, related_name='accounts_payable', on_delete=models.CASCADE, verbose_name='Compañía')
    purchase = models.ForeignKey(Purchase, on_delete=models.PROTECT)
    date_joined = models.DateField(default=__import__('datetime').datetime.now)
    end_date = models.DateField(default=__import__('datetime').datetime.now)
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
        except Exception:
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
    def save(self, *args, **kwargs):
        if not self.pk:
            self.balance = self.debt
        super().save(*args, **kwargs)
    class Meta:
        verbose_name = 'Cuenta por pagar'
        verbose_name_plural = 'Cuentas por pagar'
        default_permissions = ()
        permissions = (
            ('view_account_payable', 'Can view Cuenta por pagar'),
            ('add_account_payable', 'Can add Cuenta por pagar'),
            ('delete_account_payable', 'Can delete Cuenta por pagar'),
        )

class AccountPayablePayment(models.Model):
    company = models.ForeignKey(Company, null=True, blank=True, related_name='accounts_payable_payments', on_delete=models.CASCADE, verbose_name='Compañía')
    account_payable = models.ForeignKey(AccountPayable, on_delete=models.CASCADE, verbose_name='Cuenta por pagar')
    date_joined = models.DateField(default=__import__('datetime').datetime.now, verbose_name='Fecha de registro')
    description = models.CharField(max_length=500, null=True, blank=True, verbose_name='Detalles')
    amount = models.DecimalField(max_digits=9, decimal_places=2, default=0.00, verbose_name='Monto')
    def __str__(self):
        return str(self.account_payable_id)
    def as_dict(self):
        item = model_to_dict(self, exclude=['debts_pay'])
        item['date_joined'] = self.date_joined.strftime('%Y-%m-%d')
        item['amount'] = float(self.amount)
        return item
    def save(self, *args, **kwargs):
        if not self.description:
            self.description = 's/n'
        super().save(*args, **kwargs)
        self.account_payable.validate_debt()
    def delete(self, using=None, keep_parents=False):
        account_payable = self.account_payable
        super().delete()
        account_payable.validate_debt()
    class Meta:
        verbose_name = 'Pago de una Cuenta por pagar'
        verbose_name_plural = 'Pago de unas Cuentas por pagar'
        default_permissions = ()

class AccountReceivable(models.Model):
    company = models.ForeignKey(Company, null=True, blank=True, related_name='accounts_receivable', on_delete=models.CASCADE, verbose_name='Compañía')
    invoice = models.ForeignKey('pos.Invoice', on_delete=models.PROTECT)
    date_joined = models.DateField(default=__import__('datetime').datetime.now)
    end_date = models.DateField(default=__import__('datetime').datetime.now)
    debt = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)
    balance = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)
    active = models.BooleanField(default=True)
    def __str__(self):
        return self.get_full_name()
    def formatted_date_joined(self):
        return self.date_joined.strftime('%Y-%m-%d')
    def get_full_name(self):
        return f"{self.invoice.customer.user.names} ({self.invoice.customer.dni}) / {self.formatted_date_joined()} / ${f'{self.debt:.2f}'}"
    def validate_debt(self):
        try:
            balance = self.accountreceivablepayment_set.aggregate(result=Coalesce(Sum('amount'), 0.00, output_field=FloatField()))['result']
            self.balance = float(self.debt) - float(balance)
            self.active = self.balance > 0.00
            self.save()
        except Exception:
            pass
    def as_dict(self):
        item = model_to_dict(self)
        item['text'] = self.get_full_name()
        item['invoice'] = self.invoice.as_dict()
        item['date_joined'] = self.date_joined.strftime('%Y-%m-%d')
        item['end_date'] = self.end_date.strftime('%Y-%m-%d')
        item['debt'] = float(self.debt)
        item['balance'] = float(self.balance)
        return item
    def save(self, *args, **kwargs):
        if not self.pk:
            self.balance = self.debt
        super().save(*args, **kwargs)
    class Meta:
        verbose_name = 'Cuenta por cobrar'
        verbose_name_plural = 'Cuentas por cobrar'
        default_permissions = ()
        permissions = (
            ('view_account_receivable', 'Can view Cuenta por cobrar'),
            ('add_account_receivable', 'Can add Cuenta por cobrar'),
            ('delete_account_receivable', 'Can delete Cuenta por cobrar'),
        )

class AccountReceivablePayment(models.Model):
    company = models.ForeignKey(Company, null=True, blank=True, related_name='accounts_receivable_payments', on_delete=models.CASCADE, verbose_name='Compañía')
    account_receivable = models.ForeignKey(AccountReceivable, on_delete=models.CASCADE, verbose_name='Cuenta por cobrar')
    date_joined = models.DateField(default=__import__('datetime').datetime.now, verbose_name='Fecha de registro')
    description = models.CharField(max_length=500, null=True, blank=True, verbose_name='Detalles')
    amount = models.DecimalField(max_digits=9, decimal_places=2, default=0.00, verbose_name='Monto')
    def __str__(self):
        return str(self.account_receivable_id)
    def as_dict(self):
        item = model_to_dict(self, exclude=['ctas_collect'])
        item['date_joined'] = self.date_joined.strftime('%Y-%m-%d')
        item['amount'] = float(self.amount)
        return item
    def save(self, *args, **kwargs):
        if not self.description:
            self.description = 's/n'
        super().save(*args, **kwargs)
        self.account_receivable.validate_debt()
    def delete(self, using=None, keep_parents=False):
        account_receivable = self.account_receivable
        super().delete()
        account_receivable.validate_debt()
    class Meta:
        verbose_name = 'Detalle de una Cuenta por cobrar'
        verbose_name_plural = 'Detalles de unas Cuentas por cobrar'
        default_permissions = ()
