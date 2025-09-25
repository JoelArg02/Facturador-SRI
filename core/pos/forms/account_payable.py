from django import forms
from core.pos.models import AccountPayablePayment, AccountPayable
from core.security.form_handlers.base import BaseModelForm
from core.security.form_handlers.helpers import update_form_fields_attributes

class AccountPayablePaymentForm(BaseModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        update_form_fields_attributes(self, exclude_fields=['description'])
        self.fields['amount'].widget.attrs['autofocus'] = True
        self.fields['account_payable'].queryset = AccountPayable.objects.none()

    class Meta:
        model = AccountPayablePayment
        fields = '__all__'
        widgets = {
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'autocomplete': 'off',
                'rows': 3,
                'cols': 3,
                'placeholder': 'Ingrese una descripción'
            }),
        }