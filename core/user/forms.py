from crum import get_current_request
from django import forms
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.models import Group

from .models import User
from core.security.form_handlers.base import BaseModelForm
from core.security.form_handlers.helpers import update_form_fields_attributes


class UserForm(forms.ModelForm):
    group = forms.ModelChoiceField(
        queryset=Group.objects.all(),  # Se filtrará dinámicamente en __init__
        label="Grupo",
        widget=forms.Select(attrs={'class': 'select2', 'style': 'width:100%'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        update_form_fields_attributes(self, exclude_fields=['password'])
        self.fields['group'].required = True
        self.fields['names'].widget.attrs['autofocus'] = True

        # Filtrado dinámico de grupos: un usuario NO superusuario no debe poder ver/crear superadministradores.
        request = get_current_request()
        if request and not request.user.is_superuser:
            # Heurística: ocultar grupos cuyo nombre contenga 'super' para evitar escalación.
            self.fields['group'].queryset = self.fields['group'].queryset.exclude(name__iregex=r'super')

    class Meta:
        model = User
        fields = ('names', 'username', 'password', 'email', 'group', 'image', 'is_active')
        widgets = {
            'password': forms.PasswordInput(
                render_value=True,
                attrs={'placeholder': 'Ingrese un password'}
            ),
        }
        exclude = [
            'is_password_change', 'is_staff', 'user_permissions', 'date_joined',
            'last_login', 'is_superuser', 'password_reset_token'
        ]

    def update_session(self, user):
        request = get_current_request()
        if user == request.user:
            update_session_auth_hash(request, user)

    def save(self, commit=True):
        data = {}
        try:
            if not self.is_valid():
                data['error'] = self.errors
                return data

            user_form = super().save(commit=False)
            password = self.cleaned_data['password']

            # Actualizar contraseña si es nueva o cambió
            if user_form.pk is None or not user_form.check_password(password):
                user_form.set_password(password)

            # Control de elevación de privilegios:
            selected_group = self.cleaned_data['group']
            is_admin_group = 'admin' in selected_group.name.lower() or 'administrador' in selected_group.name.lower()

            # Solo un superusuario puede crear otro superusuario
            request = get_current_request()
            creating_superuser = selected_group.name.lower() == 'superadmin' or selected_group.name.lower() == 'super administrador'
            if creating_superuser and (not request or not request.user.is_superuser):
                data['error'] = 'No tienes permisos para crear un superadministrador.'
                return data

            # Guardar usuario
            user_form.is_staff = is_admin_group or user_form.is_staff
            if not (request and request.user.is_superuser):
                # Asegurar que no se marque superuser accidentalmente
                user_form.is_superuser = False
            user_form.save()
            user_form.groups.set([selected_group])
            self.update_session(user_form)
        except Exception as e:
            data['error'] = str(e)
        return data


class ProfileForm(BaseModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        update_form_fields_attributes(self)

    class Meta:
        model = User
        fields = ('names', 'username', 'email', 'image')
        exclude = [
            'is_password_change', 'is_active', 'is_staff', 'user_permissions',
            'password', 'date_joined', 'last_login', 'is_superuser',
            'groups', 'password_reset_token'
        ]
