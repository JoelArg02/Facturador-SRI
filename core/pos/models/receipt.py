import unicodedata

from django.db import models
from django.forms import model_to_dict

from core.pos.choices import VOUCHER_TYPE


class Receipt(models.Model):
    company = models.ForeignKey('pos.Company', null=True, blank=True, related_name='receipts', on_delete=models.CASCADE, verbose_name='Compañía')
    voucher_type = models.CharField(max_length=10, choices=VOUCHER_TYPE, verbose_name='Tipo de Comprobante')
    establishment_code = models.CharField(max_length=3, help_text='Ingrese un código del establecimiento emisor', verbose_name='Código del Establecimiento Emisor')
    issuing_point_code = models.CharField(max_length=3, help_text='Ingrese un código del punto de emisión', verbose_name='Código del Punto de Emisión')
    sequence = models.PositiveIntegerField(default=1, verbose_name='Secuencia actual')

    def __str__(self):
        return f'{self.name} - {self.establishment_code} - {self.issuing_point_code}'

    @property
    def is_ticket(self):
        return self.voucher_type == VOUCHER_TYPE[2][0]

    @property
    def name(self):
        return self.get_voucher_type_display()

    def get_name_file(self):
        return self.remove_accents(self.name.replace(' ', '_').lower()).upper()

    def remove_accents(self, text):
        return ''.join((c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn'))

    def get_sequence(self):
        return f'{self.sequence:09d}'

    def as_dict(self):
        item = model_to_dict(self)
        item['name'] = self.name
        item['voucher_type'] = {'id': self.voucher_type, 'name': self.get_voucher_type_display()}
        return item

    class Meta:
        verbose_name = 'Comprobante'
        verbose_name_plural = 'Comprobantes'
