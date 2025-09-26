from datetime import datetime

from django.db import models
from django.forms import model_to_dict


class Promotion(models.Model):
    company = models.ForeignKey('pos.Company', null=True, blank=True, related_name='promotions', on_delete=models.CASCADE, verbose_name='Compañía')
    start_date = models.DateField(default=datetime.now)
    end_date = models.DateField(default=datetime.now)
    active = models.BooleanField(default=True)

    def __str__(self):
        return str(self.id)

    def as_dict(self):
        item = model_to_dict(self)
        item['start_date'] = self.start_date.strftime('%Y-%m-%d')
        item['end_date'] = self.end_date.strftime('%Y-%m-%d')
        return item

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        self.active = self.end_date > self.start_date
        super().save(force_insert=force_insert, force_update=force_update, using=using, update_fields=update_fields)

    class Meta:
        verbose_name = 'Promoción'
        verbose_name_plural = 'Promociones'
