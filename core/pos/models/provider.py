from django.db import models
from django.forms import model_to_dict


class Provider(models.Model):
    company = models.ForeignKey('pos.Company', null=True, blank=True, related_name='providers', on_delete=models.CASCADE, verbose_name='Compañía')
    name = models.CharField(max_length=50, unique=True, help_text='Ingrese un nombre', verbose_name='Nombre')
    ruc = models.CharField(max_length=13, unique=True, help_text='Ingrese un RUC', verbose_name='RUC')
    mobile = models.CharField(max_length=10, unique=True, help_text='Ingrese un número de teléfono celular', verbose_name='Teléfono celular')
    address = models.CharField(max_length=500, null=True, blank=True, help_text='Ingrese una dirección', verbose_name='Dirección')
    email = models.CharField(max_length=50, unique=True, help_text='Ingrese un email', verbose_name='Email')

    def __str__(self):
        return self.get_full_name()

    def get_full_name(self):
        return f'{self.name} ({self.ruc})'

    def as_dict(self):
        item = model_to_dict(self)
        item['text'] = self.get_full_name()
        return item

    class Meta:
        verbose_name = 'Proveedor'
        verbose_name_plural = 'Proveedores'
