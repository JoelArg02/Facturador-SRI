from decimal import Decimal
from django import forms
from core.pos.choices import TAX_PERCENTAGE_VALUE_MAP
from core.pos.models import Company
from core.security.form_handlers.base import BaseModelForm
from core.security.form_handlers.helpers import update_form_fields_attributes

class CompanyForm(BaseModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        update_form_fields_attributes(self)

    class Meta:
        model = Company
        fields = '__all__'

class CompanyOnboardingForm(forms.ModelForm):
    """Formulario reducido para creación inicial obligatoria de la Compañía (sin campos SMTP)."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
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
        if 'description' in self.fields:
            self.fields['description'].widget.attrs['rows'] = 2
        if 'tax' in self.fields:
            self.fields['tax'].widget.attrs['step'] = '0.01'

    def clean(self):
        cleaned_data = super().clean()
        # Validación de RUC básico
        ruc = cleaned_data.get('ruc')
        if ruc and len(ruc) not in (10, 13):
            raise forms.ValidationError('El RUC debe tener 10 o 13 dígitos')

        # Mapear IVA desde porcentaje seleccionado
        tax_percentage = cleaned_data.get('tax_percentage')
        mapped_tax = TAX_PERCENTAGE_VALUE_MAP.get(tax_percentage)
        if mapped_tax is not None:
            cleaned_data['tax'] = Decimal(str(mapped_tax))
        else:
            # Default 15% si no viene
            cleaned_data['tax'] = Decimal(str(cleaned_data.get('tax') or 15))
            cleaned_data['tax_percentage'] = cleaned_data.get('tax_percentage') or 15

        # Defaults de entorno
        cleaned_data['environment_type'] = 2  # Producción
        cleaned_data['emission_type'] = 1     # Normal

        # Dirección de establecimiento por defecto igual a la principal
        if not cleaned_data.get('establishment_address'):
            cleaned_data['establishment_address'] = cleaned_data.get('main_address', '')

        # Contribuyente especial opcional (vacío por defecto)
        if not cleaned_data.get('special_taxpayer'):
            cleaned_data['special_taxpayer'] = ''

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        # Asegurar valores por defecto de negocio
        instance.environment_type = 2
        instance.emission_type = 1

        # Sincronizar tax con tax_percentage
        if hasattr(instance, 'tax_percentage') and instance.tax_percentage:
            instance.tax = Decimal(str(instance.tax_percentage))
        else:
            instance.tax = Decimal('15')
            if hasattr(instance, 'tax_percentage'):
                instance.tax_percentage = 15

        # Códigos por defecto
        if not getattr(instance, 'establishment_code', None):
            instance.establishment_code = '001'
        if not getattr(instance, 'issuing_point_code', None):
            instance.issuing_point_code = '001'

        # Dirección de establecimiento fallback
        if not getattr(instance, 'establishment_address', None):
            instance.establishment_address = getattr(instance, 'main_address', '')

        # Contribuyente especial vacío por defecto
        instance.special_taxpayer = instance.special_taxpayer or ''

        # Campos opcionales
        if not getattr(instance, 'website', None):
            instance.website = ''
        if hasattr(instance, 'electronic_signature_key') and not instance.electronic_signature_key:
            instance.electronic_signature_key = ''

        if commit:
            instance.save()
        return instance

    class Meta:
        model = Company
        fields = [
            'ruc', 'company_name', 'commercial_name', 'main_address', 'establishment_address',
            'establishment_code', 'issuing_point_code', 'special_taxpayer', 'obligated_accounting',
            'image', 'environment_type', 'emission_type', 'retention_agent', 'regimen_rimpe', 'mobile',
            'phone', 'email', 'website', 'description', 'tax', 'tax_percentage', 'electronic_signature',
            'electronic_signature_key'
        ]
        widgets = {'description': forms.Textarea()}