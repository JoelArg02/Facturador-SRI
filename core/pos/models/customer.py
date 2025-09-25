from django.db import models
from .billing_base import TransactionSummary

class Customer(TransactionSummary):
    # company opcional sólo para Customer (el campo original en TransactionSummary es requerido)
    company = models.ForeignKey('pos.Company', on_delete=models.CASCADE, null=True, blank=True, help_text='Asignar luego si aplica')
    user = models.OneToOneField('user.User', on_delete=models.CASCADE, verbose_name='Usuario')
    mobile = models.CharField(max_length=10, null=True, blank=True, verbose_name='Celular')
    address = models.CharField(max_length=500, null=True, blank=True, verbose_name='Dirección')
    business_name = models.CharField(max_length=250, null=True, blank=True, verbose_name='Razón Social')
    commercial_name = models.CharField(max_length=250, null=True, blank=True, verbose_name='Nombre Comercial')
    tradename = models.CharField(max_length=200, null=True, blank=True, verbose_name='Nombre Comercial Facturación')
    ruc = models.CharField(max_length=13, null=True, blank=True, unique=True, verbose_name='RUC')
    dni = models.CharField(max_length=10, null=True, blank=True, unique=True, verbose_name='Cédula')
    is_business = models.BooleanField(default=False, verbose_name='Es Empresa')
    is_credit_authorized = models.BooleanField(default=False, verbose_name='Está autorizado para crédito')
    credit_limit = models.DecimalField(default=0.00, decimal_places=2, max_digits=9, verbose_name='Límite de crédito')
    def __str__(self):
        return self.user.get_full_name()
    def as_dict(self):
        item = super().as_dict()
        item['user'] = self.user.toJSON()
        item['business_name'] = self.business_name
        item['tradename'] = self.tradename
        item['dni'] = self.dni
        item['ruc'] = self.ruc
        item['is_business'] = self.is_business
        item['is_credit_authorized'] = self.is_credit_authorized
        item['credit_limit'] = float(self.credit_limit)
        if self.mobile:
            item['mobile'] = self.mobile
        if self.address:
            item['address'] = self.address
        return item
    class Meta:
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'
        default_permissions = ()
        permissions = (
            ('view_customer', 'Can view Cliente'),
            ('add_customer', 'Can add Cliente'),
            ('change_customer', 'Can change Cliente'),
            ('delete_customer', 'Can delete Cliente'),
        )
