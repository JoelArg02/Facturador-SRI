from datetime import datetime
from django.db import models
from django.forms import model_to_dict
from core.pos.choices import IDENTIFICATION_TYPE
from core.user.models import User

class Customer(models.Model):
    company = models.ForeignKey('pos.Company', null=True, blank=True, related_name='customers', on_delete=models.CASCADE, verbose_name='Compañía')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='customers')
    dni = models.CharField(max_length=13, help_text='Ingrese un número de cédula o RUC', verbose_name='Número de cédula o RUC')
    mobile = models.CharField(max_length=10, null=True, blank=True, help_text='Ingrese un teléfono', verbose_name='Teléfono')
    birthdate = models.DateField(default=datetime.now, verbose_name='Fecha de nacimiento')
    address = models.CharField(max_length=500, null=True, blank=True, help_text='Ingrese una dirección', verbose_name='Dirección')
    identification_type = models.CharField(max_length=30, choices=IDENTIFICATION_TYPE, default=IDENTIFICATION_TYPE[0][0], verbose_name='Tipo de identificación')

    def __str__(self):
        return self.get_full_name()

    @property
    def identification(self):
        return self.dni or ''

    def get_full_name(self):
        user_name = getattr(self.user, 'names', 'Sin nombre')
        return f'{user_name} ({self.identification})'

    def formatted_birthdate(self):
        return self.birthdate.strftime('%d/%m/%Y') if self.birthdate else ''

    def as_dict(self):
        item = model_to_dict(self)
        item['text'] = self.get_full_name()
        if getattr(self, 'user', None):
            try:
                item['user'] = self.user.as_dict()
            except Exception:
                item['user'] = {'id': self.user.id, 'names': getattr(self.user, 'names', '')}
        else:
            item['user'] = {'id': None, 'names': ''}
        item['birthdate'] = self.formatted_birthdate()
        item['identification'] = self.identification
        item['identification_type'] = {'id': self.identification_type, 'name': self.get_identification_type_display()}
        return item

    @property
    def send_email_invoice(self):
        return True

    class Meta:
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'
        constraints = [
            models.UniqueConstraint(fields=['company', 'dni'], name='unique_customer_per_company')
        ]
