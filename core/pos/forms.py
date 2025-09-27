from django import forms
from crum import get_current_request

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
    # Campos ocultos con valores por defecto
    establishment_address = forms.CharField(widget=forms.HiddenInput(), required=False)
    special_taxpayer = forms.CharField(widget=forms.HiddenInput(), required=False, initial='000')
    environment_type = forms.IntegerField(widget=forms.HiddenInput(), initial=2)
    emission_type = forms.IntegerField(widget=forms.HiddenInput(), initial=1)
    tax = forms.DecimalField(widget=forms.HiddenInput(), required=False, initial=15.0)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Placeholders específicos solicitados
        placeholders = {
            'ruc': 'Ej: 1234567890001',
            'company_name': 'Nombre legal de la empresa',
            'commercial_name': 'Nombre comercial o marca',
            'main_address': 'Dirección principal de la matriz',
            'establishment_code': '001',
            'issuing_point_code': '001', 
            'mobile': 'Ej: 0987654321',
            'phone': 'Ej: 022345678',
            'email': 'contacto@empresa.com',
            'website': 'https://www.empresa.com',
            'description': 'Breve descripción de la empresa',
            'electronic_signature_key': 'Clave de la firma electrónica',
        }
        update_form_fields_attributes(self)
        for name, field in self.fields.items():
            ph = placeholders.get(name)
            if ph:
                field.widget.attrs['placeholder'] = ph
                
        # Ajustes específicos
        if 'description' in self.fields:
            self.fields['description'].widget.attrs['rows'] = 3
            
        # Establecer valores por defecto para campos ocultos
        self.fields['environment_type'].initial = 2  # Producción
        self.fields['emission_type'].initial = 1     # Normal
        self.fields['establishment_address'].initial = ''
        self.fields['special_taxpayer'].initial = '000'  # No es contribuyente especial por defecto
        
        if 'tax_percentage' in self.fields:
            # IVA 15% por defecto
            self.fields['tax_percentage'].initial = 15

    def clean(self):
        cleaned_data = super().clean()
        print(f"[CompanyOnboardingForm] Datos limpiados: {cleaned_data}")
        
        # Validaciones adicionales
        ruc = cleaned_data.get('ruc')
        if ruc and len(ruc) not in [10, 13]:
            raise forms.ValidationError("El RUC debe tener 10 o 13 dígitos")
        
        # Establecer valores automáticos para campos ocultos
        main_address = cleaned_data.get('main_address', '')
        if not cleaned_data.get('establishment_address'):
            cleaned_data['establishment_address'] = main_address
            
        # Special taxpayer por defecto 000 (la mayoría de empresas no son contribuyentes especiales)
        if not cleaned_data.get('special_taxpayer') or cleaned_data.get('special_taxpayer') == '':
            cleaned_data['special_taxpayer'] = '000'
            
        # Asegurar valores por defecto
        cleaned_data['environment_type'] = 2  # Producción
        cleaned_data['emission_type'] = 1     # Normal
        
        # Sincronizar tax con tax_percentage
        tax_percentage = cleaned_data.get('tax_percentage')
        if tax_percentage:
            cleaned_data['tax'] = float(tax_percentage)
        else:
            cleaned_data['tax'] = 15.0  # Default IVA 15%
            cleaned_data['tax_percentage'] = 15
        
        print(f"[CompanyOnboardingForm] Datos después de clean: {cleaned_data}")
        return cleaned_data

    def save(self, commit=True):
        try:
            print("[CompanyOnboardingForm] Iniciando save del formulario")
            instance = super().save(commit=False)
            
            # Asegurar valores por defecto para campos requeridos
            instance.environment_type = 2  # Siempre producción
            instance.emission_type = 1     # Valor por defecto
            
            # Sincronizar tax con tax_percentage (tax debe ser el mismo valor que tax_percentage)
            if hasattr(instance, 'tax_percentage') and instance.tax_percentage:
                instance.tax = float(instance.tax_percentage)
            else:
                instance.tax = 15.0  # Default IVA 15%
                instance.tax_percentage = 15
            
            # Asegurar códigos por defecto
            if not instance.establishment_code:
                instance.establishment_code = '001'
            if not instance.issuing_point_code:
                instance.issuing_point_code = '001'
                
            # Campo establishment_address requerido - usar main_address como fallback
            if not hasattr(instance, 'establishment_address') or not instance.establishment_address:
                instance.establishment_address = instance.main_address
                
            # Special taxpayer siempre vacío por defecto
            instance.special_taxpayer = ''
                
            # Campos opcionales con valores por defecto
            if not instance.website:
                instance.website = ''
            if not instance.electronic_signature_key:
                instance.electronic_signature_key = ''
                
            # Campos de email por defecto (pueden configurarse después)
            if not hasattr(instance, 'email_host_user') or not instance.email_host_user:
                instance.email_host_user = ''
            if not hasattr(instance, 'email_host_password') or not instance.email_host_password:
                instance.email_host_password = ''
            
            print(f"[CompanyOnboardingForm] Instance preparada:")
            print(f"  - RUC: {instance.ruc}")
            print(f"  - Company name: {instance.company_name}")
            print(f"  - Commercial name: {instance.commercial_name}")
            print(f"  - Environment type: {instance.environment_type}")
            print(f"  - Tax: {instance.tax}")
            print(f"  - Tax percentage: {instance.tax_percentage}")
            print(f"  - Special taxpayer: '{instance.special_taxpayer}'")
            print(f"  - Establishment address: {instance.establishment_address}")
            
            if commit:
                instance.save()
                print(f"[CompanyOnboardingForm] Compañía guardada con ID: {instance.id}")
            
            return instance
            
        except Exception as e:
            print(f"[CompanyOnboardingForm] Error en save: {e}")
            import traceback
            traceback.print_exc()
            raise

    class Meta:
        model = Company
        fields = [
            # Información básica (Paso 1)
            'ruc', 'company_name', 'commercial_name', 'image',
            # Dirección y códigos (Paso 2) 
            'main_address', 'establishment_code', 'issuing_point_code',
            # Configuración tributaria (Paso 3)
            'obligated_accounting', 'retention_agent', 'regimen_rimpe', 'tax_percentage',
            # Contacto (Paso 4)
            'mobile', 'phone', 'email', 'website', 'description',
            # Firma electrónica (Paso 5) - opcional
            'electronic_signature', 'electronic_signature_key',
            # Campos ocultos con valores por defecto
            'establishment_address', 'special_taxpayer', 'environment_type', 'emission_type', 'tax'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'ruc': forms.TextInput(attrs={'maxlength': 13, 'pattern': '[0-9]{10,13}'}),
            'establishment_code': forms.TextInput(attrs={'maxlength': 3, 'pattern': '[0-9]{3}', 'value': '001'}),
            'issuing_point_code': forms.TextInput(attrs={'maxlength': 3, 'pattern': '[0-9]{3}', 'value': '001'}),
            'mobile': forms.TextInput(attrs={'maxlength': 10, 'pattern': '[0-9]{10}'}),
            'phone': forms.TextInput(attrs={'maxlength': 9, 'pattern': '[0-9]{7,9}'}),
            'email': forms.EmailInput(),
            'website': forms.URLInput(),
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
        """Guarda y asegura que la compañía sea la del usuario logueado si no se envía en el form.

        Retorna siempre un dict JSON-serializable.
        """
        data = {}
        if not self.is_valid():
            data['error'] = self.errors
            return data

        instance = super().save(commit=False)

        # Autoasignar compañía desde el request si no viene en el formulario
        try:
            request = get_current_request()
            if hasattr(instance, 'company') and getattr(instance, 'company', None) is None and request is not None:
                company = getattr(request, 'company', None) or getattr(getattr(request, 'user', None), 'company', None)
                if company is not None:
                    instance.company = company
        except Exception:
            pass

        if commit:
            instance.save()
        return instance.as_dict()


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
