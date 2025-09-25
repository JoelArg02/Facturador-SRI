from django import forms

from .models import *
from core.user.models import User  # Import explícito para evitar NameError en CustomerUserForm
from .choices import (
    VOUCHER_TYPE,
    INVOICE_STATUS,
    IDENTIFICATION_TYPE,
    PAYMENT_TYPE,
)

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


class CompanyOnboardingForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Placeholders específicos solicitados
        placeholders = {
            'ruc': 'Ingrese un número de RUC',
            'company_name': 'Ingrese la razón social',
            'commercial_name': 'Ingrese el nombre comercial',
            'main_address': 'Ingrese la dirección del Establecimiento Matriz',
            'establishment_address': 'Ingrese la dirección del Establecimiento Emisor',
            'establishment_code': 'Ingrese el código del Establecimiento Emisor',
            'issuing_point_code': 'Ingrese el código del Punto de Emisión',
            'special_taxpayer': 'Ingrese el número de Resolución del Contribuyente Especial',
            'mobile': 'Ingrese el teléfono celular',
            'phone': 'Ingrese el teléfono convencional',
            'email': 'Ingrese la dirección de correo electrónico',
            'website': 'Ingrese la dirección de la página web',
            'description': 'Ingrese una breve descripción',
            'tax': '0.00',
            'electronic_signature_key': 'Clave de firma electrónica',
        }
        update_form_fields_attributes(self)
        for name, field in self.fields.items():
            ph = placeholders.get(name)
            if ph:
                field.widget.attrs['placeholder'] = ph
        # Ajustes específicos
        if 'description' in self.fields:
            self.fields['description'].widget.attrs['rows'] = 2
        if 'tax' in self.fields:
            self.fields['tax'].widget.attrs['step'] = '0.01'

    class Meta:
        model = Company
        fields = [
            'ruc', 'company_name', 'commercial_name', 'main_address', 'establishment_address',
            'establishment_code', 'issuing_point_code', 'special_taxpayer', 'obligated_accounting',
            'image', 'environment_type', 'emission_type', 'retention_agent', 'regimen_rimpe', 'mobile',
            'phone', 'email', 'website', 'description', 'tax', 'tax_percentage', 'electronic_signature',
            'electronic_signature_key'
        ]
        widgets = {
            'description': forms.Textarea(),
        }


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
        if 'company' in self.fields:
            self.fields['company'].widget = self.fields['company'].hidden_widget()
            self.fields['company'].required = False

    class Meta:
        model = Product
        exclude = ['stock', 'barcode', 'company']
        widgets = {
            'description': forms.Textarea(attrs={'placeholder': 'Ingrese una descripción', 'rows': 3, 'cols': 3}),
            'price': forms.TextInput(),
            'pvp': forms.TextInput(),
        }

    def save(self, commit=True):
        """Devuelve siempre la instancia del modelo (o None si inválido)."""
        if not self.is_valid():
            return None
        # Llamar directamente al save original de ModelForm (saltando BaseModelForm.save)
        instance = forms.ModelForm.save(self, commit=False)
        if commit:
            instance.save()
        return instance

    def clean_code(self):
        code = self.cleaned_data.get('code')
        if code:
            return code.upper()
        return code


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
    # Un solo campo de entrada para Cédula (10) o RUC (13)
    dni = forms.CharField(label='Identificación', required=True, widget=forms.TextInput(attrs={
        'placeholder': 'Ingrese Cédula (10) o RUC (13)',
        'maxlength': '13'
    }))

    class Meta:
        model = Customer
        fields = [
            'user', 'dni', 'mobile', 'address', 'business_name', 'commercial_name', 'tradename',
            'is_business', 'is_credit_authorized', 'credit_limit'
        ]
        widgets = {
            'address': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        update_form_fields_attributes(self)
        if self.instance and self.instance.pk:
            # Pre-cargar en el campo único
            if self.instance.ruc:
                self.fields['dni'].initial = self.instance.ruc
            elif self.instance.dni:
                self.fields['dni'].initial = self.instance.dni
        if 'credit_limit' in self.fields:
            self.fields['credit_limit'].widget.attrs['step'] = '0.01'

    def clean_dni(self):
        value = (self.cleaned_data.get('dni') or '').strip()
        if not value.isdigit():
            raise forms.ValidationError('La identificación debe ser numérica.')
        if len(value) not in (10, 13):
            raise forms.ValidationError('La identificación debe tener 10 dígitos (Cédula) o 13 dígitos (RUC).')
        return value

    def clean(self):
        cleaned = super().clean()
        value = cleaned.get('dni')
        if not value:
            return cleaned
        # Verificar unicidad lógica según longitud
        if len(value) == 10:
            # Cédula: no debe existir otra con mismo dni
            qs = Customer.objects.filter(dni=value)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                self.add_error('dni', 'Ya existe un cliente con esa cédula.')
        elif len(value) == 13:
            qs = Customer.objects.filter(ruc=value)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                self.add_error('dni', 'Ya existe un cliente con ese RUC.')
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        value = self.cleaned_data['dni']
        # Normalizar: asignar al campo correcto y limpiar el otro
        if len(value) == 10:
            instance.dni = value
            instance.ruc = None
            instance.is_business = False if 'is_business' in self.cleaned_data else instance.is_business
        elif len(value) == 13:
            instance.ruc = value
            # Si es RUC asumimos empresa
            instance.is_business = True
            instance.dni = None
        if commit:
            instance.save()
        return instance


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
