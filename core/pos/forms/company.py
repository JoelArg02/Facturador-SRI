from django import forms
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