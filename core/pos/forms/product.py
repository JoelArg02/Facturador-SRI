from django import forms
from crum import get_current_request
from core.pos.models import Product, Category
from core.security.form_handlers.base import BaseModelForm
from core.security.form_handlers.helpers import update_form_fields_attributes


class ProductForm(BaseModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        update_form_fields_attributes(self, exclude_fields=['price', 'pvp', 'description'])
        try:
            request = get_current_request()
            user = getattr(request, 'user', None)
            is_superuser = getattr(user, 'is_superuser', False)
            current_company = (
                getattr(request, 'company', None)
                or getattr(getattr(request, 'user', None), 'company', None)
                or getattr(self.instance, 'company', None)
            )
            if 'category' in self.fields:
                if not is_superuser:
                    if current_company:
                        self.fields['category'].queryset = Category.objects.filter(company=current_company)
                    else:
                        self.fields['category'].queryset = Category.objects.none()
                else:
                    self.fields['category'].queryset = Category.objects.all()
        except Exception:
            pass
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