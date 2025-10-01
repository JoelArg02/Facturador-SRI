from django import forms
from django.db.models import Q
from core.pos.models import Customer
from core.user.models import User
from core.security.form_handlers.helpers import update_form_fields_attributes

class CustomerForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):

        self.company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)
        update_form_fields_attributes(self)
        if self.instance and self.instance.pk:
            if self.instance.ruc:
                self.fields['dni'].initial = self.instance.ruc
            elif self.instance.dni:
                self.fields['dni'].initial = self.instance.dni
        if 'credit_limit' in self.fields:
            self.fields['credit_limit'].widget.attrs['step'] = '0.01'
    dni = forms.CharField(label='Identificación', required=True, widget=forms.TextInput(attrs={
        'placeholder': 'Ingrese Cédula (10) o RUC (13)',
        'maxlength': '13'
    }))

    class Meta:
        model = Customer
        fields = [
            # 'user' removido: se asigna automáticamente en la vista de creación
            # Nota: El campo de formulario 'dni' NO debe estar en Meta.fields para evitar
            # que ModelForm intente asignarlo al modelo antes de normalizarlo (10 -> dni, 13 -> ruc).
            'mobile', 'address', 'business_name', 'commercial_name', 'tradename',
            'is_business', 'is_credit_authorized', 'credit_limit'
        ]
        widgets = {
            'address': forms.Textarea(attrs={'rows': 2}),
        }

    

    def clean_dni(self):
        value = (self.cleaned_data.get('dni') or '').strip()
        if not value.isdigit():
            raise forms.ValidationError('La identificación debe ser numérica.')
        if len(value) not in (10, 13):
            raise forms.ValidationError('La identificación debe tener 10 dígitos (Cédula) o 13 dígitos (RUC).')
        return value

    def clean(self):
        cleaned = super().clean()
        value = cleaned.get('dni')
        if not value:
            return cleaned
        # Restringir por compañía si está disponible
        company_filter = Q()
        if self.company is not None:
            company_filter &= Q(company=self.company)
        if len(value) == 10:
            qs = Customer.objects.filter(company_filter, dni=value)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                self.add_error('dni', 'Ya existe un cliente con esa cédula.')
        elif len(value) == 13:
            qs = Customer.objects.filter(company_filter, ruc=value)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                self.add_error('dni', 'Ya existe un cliente con ese RUC.')
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        value = self.cleaned_data['dni']
        if len(value) == 10:
            instance.dni = value
            instance.ruc = None
            instance.is_business = False if 'is_business' in self.cleaned_data else instance.is_business
        elif len(value) == 13:
            instance.ruc = value
            instance.is_business = True
            instance.dni = None
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
        fields = 'names', 'email', 'image'
        exclude = ['username', 'groups', 'is_active', 'is_password_change', 'is_staff', 'user_permissions', 'date_joined', 'last_login', 'is_superuser', 'password_reset_token']