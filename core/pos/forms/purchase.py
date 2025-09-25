from django import forms
from core.pos.models import Purchase, Provider
from core.security.form_handlers.base import BaseModelForm
from core.security.form_handlers.helpers import update_form_fields_attributes

class PurchaseForm(BaseModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        update_form_fields_attributes(self, exclude_fields=['search'])
        self.fields['provider'].queryset = Provider.objects.none()
        for field_name in ['subtotal', 'tax', 'total_tax', 'total_amount']:
            self.fields[field_name].disabled = True

    class Meta:
        model = Purchase
        fields = '__all__'

    search = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Ingrese un nombre o código de producto'
    }), label='Buscador de productos')