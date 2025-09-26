from django.db import models
from django.forms import model_to_dict


class Category(models.Model):
    company = models.ForeignKey('pos.Company', null=True, blank=True, related_name='categories', on_delete=models.CASCADE, verbose_name='Compañía')
    name = models.CharField(max_length=50, help_text='Ingrese un nombre', verbose_name='Nombre')

    def __str__(self):
        return self.name

    def as_dict(self):
        item = model_to_dict(self)
        return item

    class Meta:
        verbose_name = 'Categoria'
        verbose_name_plural = 'Categorias'
        constraints = [
            models.UniqueConstraint(fields=['company', 'name'], name='uniq_category_company_name')
        ]
