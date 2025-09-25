from django import forms
from core.pos.models import CreditNote, Invoice
from core.security.form_handlers.helpers import update_form_fields_attributes

class CreditNoteForm(forms.ModelForm):
    select_all = forms.BooleanField(widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}), label='Seleccionar todo')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        update_form_fields_attributes(self, exclude_fields=['select_all'])
        self.fields['invoice'].queryset = Invoice.objects.none()
        for field_name in ['receipt_number', 'subtotal_without_tax', 'subtotal_with_tax', 'tax', 'total_tax', 'total_discount', 'total_amount']:
            self.fields[field_name].disabled = True

    class Meta:
        model = CreditNote
        fields = '__all__'
        exclude = [
            'company', 'employee', 'time_joined', 'environment_type', 'access_code', 'authorized_date',
            'authorized_xml', 'authorized_pdf', 'status'
        ]