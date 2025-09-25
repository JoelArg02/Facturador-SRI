from django import forms
from core.pos.models import Quotation, Customer
from core.security.form_handlers.base import BaseModelForm
from core.security.form_handlers.helpers import update_form_fields_attributes

class QuotationForm(BaseModelForm):
    search = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Ingrese un nombre o código de producto'
    }), label='Buscador de productos')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        update_form_fields_attributes(self, exclude_fields=['search'])
        self.fields['customer'].queryset = Customer.objects.none()
        for field_name in ['subtotal_without_tax', 'subtotal_with_tax', 'tax', 'total_tax', 'total_discount', 'total_amount']:
            self.fields[field_name].disabled = True

    class Meta:
        model = Quotation
        fields = '__all__'
        exclude = ['company', 'employee']