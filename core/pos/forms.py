from django import forms

from .models import *
from core.user.models import User  # Import explícito para evitar NameError en CustomerUserForm
from .choices import (
    VOUCHER_TYPE,
    INVOICE_STATUS,
    IDENTIFICATION_TYPE,
    PAYMENT_TYPE,
)

# Reexport de constantes para compatibilidad con importaciones existentes en vistas
__all__ = [
    'CompanyForm', 'ProviderForm', 'CategoryForm', 'ProductForm', 'PurchaseForm',
    'AccountPayablePaymentForm', 'CustomerForm', 'CustomerUserForm', 'ReceiptForm',
    'ExpenseTypeForm', 'ExpenseForm', 'PromotionForm', 'InvoiceForm',
    'AccountReceivablePaymentForm', 'QuotationForm', 'CreditNoteForm',
    # Constantes
    'VOUCHER_TYPE', 'INVOICE_STATUS', 'IDENTIFICATION_TYPE', 'PAYMENT_TYPE'
]
from ..security.form_handlers.base import BaseModelForm
from ..security.form_handlers.helpers import update_form_fields_attributes


class CompanyForm(BaseModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        update_form_fields_attributes(self)

    class Meta:
        model = Company
        fields = '__all__'


class ProviderForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        update_form_fields_attributes(self)
        self.fields['name'].widget.attrs['autofocus'] = True

    class Meta:
        model = Provider
        fields = '__all__'

    def save(self, commit=True):
        data = {}
        if self.is_valid():
            instance = super().save()
            data = instance.as_dict()
        else:
            data['error'] = self.errors
        return data


class CategoryForm(BaseModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        update_form_fields_attributes(self)

    class Meta:
        model = Category
        fields = '__all__'


class ProductForm(BaseModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        update_form_fields_attributes(self, exclude_fields=['price', 'pvp', 'description'])

    class Meta:
        model = Product
        fields = '__all__'
        widgets = {
            'description': forms.Textarea(attrs={'placeholder': 'Ingrese una descripción', 'rows': 3, 'cols': 3}),
            'price': forms.TextInput(),
            'pvp': forms.TextInput(),
        }
        exclude = ['stock', 'barcode']


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


class CustomerForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        update_form_fields_attributes(self)
        # Campos heredados de TransactionSummary que no deben mostrarse en la creación/edición de Cliente
        hidden_summary_fields = [
            'date_joined', 'subtotal_without_tax', 'subtotal_with_tax', 'tax',
            'total_tax', 'total_discount', 'total_amount'
        ]
        for f in hidden_summary_fields:
            if f in self.fields:
                self.fields[f].widget = forms.HiddenInput()
                # Opcional: limpiar required si aplica
                self.fields[f].required = False

    class Meta:
        model = Customer
        # Listar explícitamente solo los campos que interesan al usuario final
        fields = [
            'user', 'mobile', 'address', 'business_name', 'commercial_name',
            'tradename', 'ruc', 'dni', 'is_business', 'is_credit_authorized', 'credit_limit'
        ]
        widgets = {
            'credit_limit': forms.NumberInput(attrs={'step': '0.01'})
        }


class CustomerUserForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        update_form_fields_attributes(self)
        self.fields['names'].widget.attrs['autofocus'] = True

    class Meta:
        model = User
        fields = 'names', 'email', 'image'
        exclude = ['username', 'groups', 'is_active', 'is_password_change', 'is_staff', 'user_permissions', 'date_joined', 'last_login', 'is_superuser', 'password_reset_token']


class ReceiptForm(BaseModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        update_form_fields_attributes(self)

    class Meta:
        model = Receipt
        fields = '__all__'


class ExpenseTypeForm(BaseModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        update_form_fields_attributes(self)

    class Meta:
        model = ExpenseType
        fields = '__all__'


class ExpenseForm(BaseModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        update_form_fields_attributes(self, exclude_fields=['description', 'amount'])

    class Meta:
        model = Expense
        fields = '__all__'
        widgets = {
            'description': forms.Textarea(attrs={'placeholder': 'Ingrese una descripción', 'rows': 3, 'cols': '3'}),
            'amount': forms.TextInput()
        }


class PromotionForm(BaseModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        update_form_fields_attributes(self)
        self.fields['date_range'].widget.attrs['autofocus'] = True

    class Meta:
        model = Promotion
        fields = '__all__'
        exclude = ['active']

    date_range = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'form-control',
        'autocomplete': 'off'
    }), label='Fecha de inicio y finalización')


class InvoiceForm(BaseModelForm):
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

    search = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Ingrese un nombre o código de producto'
    }), label='Buscador de productos')


class AccountReceivablePaymentForm(BaseModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        update_form_fields_attributes(self, exclude_fields=['description'])
        self.fields['amount'].widget.attrs['autofocus'] = True
        self.fields['account_receivable'].queryset = AccountReceivable.objects.none()

    class Meta:
        model = AccountReceivablePayment
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


class QuotationForm(BaseModelForm):
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

    search = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Ingrese un nombre o código de producto'
    }), label='Buscador de productos')


class CreditNoteForm(forms.ModelForm):
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

    select_all = forms.BooleanField(widget=forms.CheckboxInput(attrs={
        'class': 'form-check-input'
    }), label='Seleccionar todo')
