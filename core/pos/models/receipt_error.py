from datetime import datetime

from django.db import models
from django.forms import model_to_dict

from core.pos.choices import ENVIRONMENT_TYPE, VOUCHER_STAGE


class ReceiptError(models.Model):
    date_joined = models.DateField(default=datetime.now, verbose_name='Fecha de registro')
    time_joined = models.DateTimeField(default=datetime.now, verbose_name='Hora de registro')
    environment_type = models.PositiveIntegerField(choices=ENVIRONMENT_TYPE, default=ENVIRONMENT_TYPE[0][0], verbose_name='Tipo de entorno')
    receipt_number_full = models.CharField(max_length=50, verbose_name='Número de comprobante')
    receipt = models.ForeignKey('pos.Receipt', on_delete=models.CASCADE, verbose_name='Tipo de Comprobante')
    stage = models.CharField(max_length=20, choices=VOUCHER_STAGE, default=VOUCHER_STAGE[0][0], verbose_name='Etapa')
    errors = models.JSONField(default=dict, verbose_name='Errores')

    def __str__(self):
        return self.stage

    def as_dict(self):
        item = model_to_dict(self)
        item['date_joined'] = self.date_joined.strftime('%Y-%m-%d')
        item['time_joined'] = self.time_joined.strftime('%Y-%m-%d %H:%M')
        item['environment_type'] = {'id': self.environment_type, 'name': self.get_environment_type_display()}
        item['receipt'] = self.receipt.as_dict()
        item['stage'] = {'id': self.stage, 'name': self.get_stage_display()}
        return item

    class Meta:
        verbose_name = 'Error del Comprobante'
        verbose_name_plural = 'Errores de los Comprobantes'
        default_permissions = ()
        permissions = (
            ('view_receipt_error', 'Can view Error del Comprobante'),
            ('delete_receipt_error', 'Can delete Error del Comprobante'),
        )
        ordering = ['id']
