from django import forms
from core.pos.models import Invoice, Customer
from core.pos.choices import VOUCHER_TYPE
from core.security.form_handlers.base import BaseModelForm
from core.security.form_handlers.helpers import update_form_fields_attributes

class InvoiceForm(BaseModelForm):
    search = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Ingrese un nombre o código de producto'
    }), label='Buscador de productos')

    def __init__(self, *args, **kwargs):
        disabled_fields = kwargs.pop('disabled_fields', [])
        fields_disable_default = ['receipt_number', 'subtotal_without_tax', 'subtotal_with_tax', 'tax', 'total_tax', 'total_discount', 'total_amount', 'change']
        super().__init__(*args, **kwargs)
        update_form_fields_attributes(self, exclude_fields=['search'])
        self.fields['customer'].queryset = Customer.objects.none()
        self.fields['receipt'].choices = tuple((code, label) for code, label in VOUCHER_TYPE if code != VOUCHER_TYPE[1][0])
        disabled_fields.extend(fields_disable_default)
        for field_name in disabled_fields:
            self.fields[field_name].disabled = True

    class Meta:
        model = Invoice
        fields = '__all__'
        exclude = [
            'company', 'employee', 'payment_method', 'time_limit', 'time_joined', 'environment_type', 'access_code', 'authorized_date',
            'authorized_xml', 'authorized_pdf', 'status'
        ]