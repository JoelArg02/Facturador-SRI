from django import forms
from django.db.models import Q

from core.pos.models import Receipt, Product


class ReportForm(forms.Form):
    date_range = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'form-control',
        'autocomplete': 'off'
    }), label='Buscar por rango de fechas')

    receipt = forms.ModelChoiceField(widget=forms.Select(attrs={
        'class': 'form-control select2',
        'style': 'width: 100%;'
    }), queryset=Receipt.objects.none(), label='Seleccionar Tipo de Comprobante')

    product = forms.ModelChoiceField(widget=forms.SelectMultiple(attrs={
        'class': 'form-control select2',
    }), queryset=Product.objects.none(), label='Producto')

    def __init__(self, *args, **kwargs):
        company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)
        # Cargar queryset según compañía si está disponible
        if company is not None:
            self.fields['receipt'].queryset = Receipt.objects.filter(company=company)
            self.fields['product'].queryset = Product.objects.filter(company=company)
        else:
            self.fields['receipt'].queryset = Receipt.objects.all()
            self.fields['product'].queryset = Product.objects.all()

