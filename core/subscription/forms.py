from django import forms
from django.contrib.auth import get_user_model

from .models import Subscription


def get_available_admin_users():
    """Retorna usuarios administradores disponibles para suscripción."""
    User = get_user_model()
    from django.contrib.auth.models import Group
    
    admin_groups = Group.objects.filter(name__in=['Administrador'])
    
    # Mostrar todos los usuarios administradores (con o sin suscripción)
    # En el futuro se puede filtrar por suscripciones activas si se desea
    return (
        User.objects
        .filter(groups__in=admin_groups)
        .distinct()
        .filter(subscriptions__isnull=True)
        .select_related('company')
        .order_by('names', 'username')
    )


class SubscriptionForm(forms.ModelForm):
    class Meta:
        model = Subscription
        fields = ['user', 'plan', 'is_active']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['user'].label = 'Administrador'
        self.fields['user'].help_text = 'Selecciona el usuario administrador.'
        
        # Usar la función personalizada para obtener usuarios disponibles
        self.fields['user'].queryset = get_available_admin_users()
        self.fields['user'].empty_label = 'Seleccione un administrador'

        def _label_from_instance(user):
            company = getattr(user, 'company', None)
            company_name = company.commercial_name if company else 'Sin compañía'
            display_name = user.get_full_name() or user.username
            return f'{display_name} · {company_name}'

        self.fields['user'].label_from_instance = _label_from_instance
        self.fields['plan'].label = 'Plan'
        self.fields['is_active'].label = 'Activa'

        # Mostrar compañía asociada en choices
        self.fields['user'].widget.attrs.setdefault('class', 'form-control')
        self.fields['plan'].widget.attrs.setdefault('class', 'form-control')

    def save(self, commit=True):
        subscription = super().save(commit=False)
        if commit:
            subscription.save()
        return subscription
