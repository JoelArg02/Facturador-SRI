from django import forms
from core.pos.models import Product
from core.security.form_handlers.base import BaseModelForm
from core.security.form_handlers.helpers import update_form_fields_attributes


class ProductForm(BaseModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        update_form_fields_attributes(self, exclude_fields=['price', 'pvp', 'description'])
        # Ocultamos el campo company en el formulario (se asigna en la vista)
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

    def clean_code(self):
        code = self.cleaned_data.get('code')
        if code:
            code = code.strip()
        return code

    def save(self, commit=True):
        """Devuelve siempre la instancia del modelo (o None si inválido)."""
        if not self.is_valid():
            return None
        instance = forms.ModelForm.save(self, commit=False)
        if commit:
            instance.save()
        return instance