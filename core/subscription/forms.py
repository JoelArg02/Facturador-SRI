from django import forms
from django.contrib.auth import get_user_model

from .models import Subscription


class SubscriptionForm(forms.ModelForm):
    class Meta:
        model = Subscription
        fields = ['user', 'plan', 'start_date', 'end_date', 'is_active']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        User = get_user_model()
        self.fields['user'].label = 'Propietario'
        self.fields['user'].help_text = 'Selecciona el usuario propietario de la compañía.'
        self.fields['user'].queryset = (
            User.objects.filter(company__isnull=False)
            .select_related('company')
            .order_by('names', 'username')
        )
        self.fields['user'].empty_label = 'Seleccione un propietario'

        def _label_from_instance(user):
            company = getattr(user, 'company', None)
            company_name = company.commercial_name if company else 'Sin compañía asignada'
            display_name = user.get_full_name() or user.username
            return f'{display_name} · {company_name}'

        self.fields['user'].label_from_instance = _label_from_instance
        self.fields['plan'].label = 'Plan'
        self.fields['start_date'].label = 'Fecha de inicio'
        self.fields['end_date'].label = 'Fecha de fin'
        self.fields['end_date'].required = False
        self.fields['is_active'].label = 'Activa'

        # Mostrar compañía asociada en choices
        self.fields['user'].widget.attrs.setdefault('class', 'form-control')
        self.fields['plan'].widget.attrs.setdefault('class', 'form-control')
        self.fields['start_date'].widget.attrs.setdefault('class', 'form-control')
        self.fields['end_date'].widget.attrs.setdefault('class', 'form-control')

    def save(self, commit=True):
        subscription = super().save(commit=False)
        if commit:
            subscription.save()
        return subscription
