from django.db import models
from django.db.models import Q, UniqueConstraint
from django.forms import model_to_dict

from core.pos.choices import IDENTIFICATION_TYPE
from core.user.models import User


class Customer(models.Model):
    company = models.ForeignKey('pos.Company', null=True, blank=True, related_name='customers', on_delete=models.CASCADE, verbose_name='Compañía')
    # Permitir que un mismo usuario sea cliente de múltiples compañías
    user = models.ForeignKey(User, related_name='customers', on_delete=models.CASCADE)
    # La unicidad se manejará a nivel de (company, dni) y (company, ruc)
    dni = models.CharField(max_length=10, null=True, blank=True, verbose_name='Cédula')
    ruc = models.CharField(max_length=13, null=True, blank=True, verbose_name='RUC')
    mobile = models.CharField(max_length=10, null=True, blank=True, help_text='Ingrese un teléfono', verbose_name='Teléfono')
    address = models.CharField(max_length=500, null=True, blank=True, help_text='Ingrese una dirección', verbose_name='Dirección')
    business_name = models.CharField(max_length=250, null=True, blank=True, verbose_name='Razón Social')
    commercial_name = models.CharField(max_length=250, null=True, blank=True, verbose_name='Nombre Comercial')
    tradename = models.CharField(max_length=200, null=True, blank=True, verbose_name='Nombre Comercial Facturación')
    is_business = models.BooleanField(default=False, verbose_name='Es Empresa')
    is_credit_authorized = models.BooleanField(default=False, verbose_name='Está autorizado para crédito')
    credit_limit = models.DecimalField(max_digits=9, decimal_places=2, default=0.00, verbose_name='Límite de crédito')

    def __str__(self):
        return self.get_full_name()

    @property
    def identification(self):
        return self.ruc or self.dni or ''

    def get_full_name(self):
        return f'{self.user.names} ({self.identification})'

    def formatted_birthdate(self):
        return ''

    def as_dict(self):
        item = model_to_dict(self)
        item['text'] = self.get_full_name()
        item['user'] = self.user.as_dict()
        item['birthdate'] = self.formatted_birthdate()
        ident_type = self.identification_type
        item['identification_type'] = {'id': ident_type, 'name': dict(IDENTIFICATION_TYPE).get(ident_type, ident_type)}
        item['identification'] = self.identification
        item['send_email_invoice'] = True
        credit_limit = item.get('credit_limit')
        if credit_limit is not None:
            try:
                item['credit_limit'] = float(credit_limit)
            except Exception:
                item['credit_limit'] = 0.0
        return item

    @property
    def identification_type(self):
        ident = self.identification
        if len(ident) == 13:
            return '04'
        if len(ident) == 10:
            return '05'
        return '07'

    @property
    def send_email_invoice(self):
        return True

    class Meta:
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'
        constraints = [
            UniqueConstraint(
                fields=['company', 'dni'],
                name='unique_customer_dni_per_company',
                condition=Q(dni__isnull=False) & ~Q(dni='')
            ),
            UniqueConstraint(
                fields=['company', 'ruc'],
                name='unique_customer_ruc_per_company',
                condition=Q(ruc__isnull=False) & ~Q(ruc='')
            ),
        ]
