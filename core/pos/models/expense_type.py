from django.db import models
from django.forms import model_to_dict


class ExpenseType(models.Model):
    company = models.ForeignKey('pos.Company', null=True, blank=True, related_name='expense_types', on_delete=models.CASCADE, verbose_name='Compañía')
    name = models.CharField(max_length=50, unique=True, help_text='Ingrese un nombre', verbose_name='Nombre')

    def __str__(self):
        return self.name

    def as_dict(self):
        return model_to_dict(self)

    class Meta:
        verbose_name = 'Tipo de Gasto'
        verbose_name_plural = 'Tipos de Gastos'
        default_permissions = ()
        permissions = (
            ('view_expense_type', 'Can view Tipo de Gasto'),
            ('add_expense_type', 'Can add Tipo de Gasto'),
            ('change_expense_type', 'Can change Tipo de Gasto'),
            ('delete_expense_type', 'Can delete Tipo de Gasto'),
        )
