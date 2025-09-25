from django import forms
from core.pos.models import Product
from core.security.form_handlers.base import BaseModelForm
from core.security.form_handlers.helpers import update_form_fields_attributes


class ProductForm(BaseModelForm):
    """Formulario de Producto sin exponer el campo company al usuario.

    La asignación de company se realiza en la vista/mixin. Este form evita
    validaciones prematuras sobre company (puede venir null hasta form_valid).
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        update_form_fields_attributes(self, exclude_fields=['price', 'pvp', 'description'])
        # Company ahora es obligatorio a nivel de negocio
        if 'company' in self.fields:
            self.fields['company'].required = True

    class Meta:
        model = Product
        fields = '__all__'
        widgets = {
            'description': forms.Textarea(attrs={'placeholder': 'Ingrese una descripción', 'rows': 3, 'cols': 3}),
            'price': forms.TextInput(),
            'pvp': forms.TextInput(),
        }
        exclude = ['stock', 'barcode']

    def clean_code(self):
        code = self.cleaned_data.get('code')
        if code:
            code = code.strip()
        return code

    def save(self, commit=True):
        # Saltamos BaseModelForm.save (que devuelve dict) y usamos directamente ModelForm
        if not self.is_valid():
            # Imitar comportamiento estándar: lanzar excepción o devolver errores
            raise ValueError('El formulario de producto no es válido antes de guardar.')
        instance = forms.ModelForm.save(self, commit=False)
        if commit:
            instance.save()
        return instance