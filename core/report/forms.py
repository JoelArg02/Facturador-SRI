from django import forms

from core.pos.models import Receipt, Product


class ReportForm(forms.Form):
    date_range = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'form-control',
        'autocomplete': 'off'
    }), label='Buscar por rango de fechas')

    receipt = forms.ModelChoiceField(widget=forms.Select(attrs={
        'class': 'form-control select2',
        'style': 'width: 100%;'
    }), queryset=Receipt.objects.all(), label='Seleccionar Tipo de Comprobante')

    product = forms.ModelChoiceField(widget=forms.SelectMultiple(attrs={
        'class': 'form-control select2',
    }), queryset=Product.objects.all(), label='Producto')

    def __init__(self, *args, **kwargs):
        # Permitir pasar company desde la vista para limitar datos
        company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)
        if company is not None:
            try:
                self.fields['receipt'].queryset = Receipt.objects.filter(company=company)
            except Exception:
                pass
            try:
                self.fields['product'].queryset = Product.objects.filter(company=company)
            except Exception:
                pass

