from django import forms
from django.db.models import Q
from core.pos.models import Customer
from core.user.models import User
from core.security.form_handlers.helpers import update_form_fields_attributes


class CustomerForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        update_form_fields_attributes(self)

    class Meta:
        model = Customer
        exclude = ['user', 'company']

    def clean_dni(self):
        value = (self.cleaned_data.get('dni') or '').strip()
        if not value.isdigit():
            raise forms.ValidationError('La identificación debe ser numérica.')
        if len(value) not in (10, 13):
            raise forms.ValidationError('La identificación debe tener 10 o 13 dígitos.')
        return value

    def clean(self):
        cleaned_data = super().clean()
        dni = cleaned_data.get('dni')
        if not dni:
            return cleaned_data

        company = getattr(self.request.user, 'company', None) if self.request else None
        filters = Q(dni=dni)
        if company:
            filters &= Q(company=company)

        qs = Customer.objects.filter(filters)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            self.add_error('dni', 'Ya existe un cliente con esta identificación en su compañía.')

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        value = self.cleaned_data.get('dni')
        instance.dni = value.strip() if value else ''
        if self.request:
            instance.company = getattr(self.request.user, 'company', None)
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
        fields = ['names', 'email', 'image']
        exclude = [
            'username', 'groups', 'is_active', 'is_password_change', 'is_staff',
            'user_permissions', 'date_joined', 'last_login', 'is_superuser', 'password_reset_token'
        ]
