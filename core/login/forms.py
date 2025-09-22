from django import forms

from core.user.models import User


class ResetPasswordForm(forms.Form):
    username = forms.CharField(widget=forms.TextInput(attrs={
        'placeholder': 'Ingrese un username',
        'class': 'form-control',
        'autocomplete': 'off'
    }), required=True, label='Usuario')

    def clean(self):
        cleaned = super().clean()
        if User.objects.filter(username=cleaned['username']).first():
            return cleaned
        raise forms.ValidationError('El usuario solicitado no existe')

    def get_user(self):
        return User.objects.get(username=self.cleaned_data['username'])


class UpdatePasswordForm(forms.Form):
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'placeholder': 'Ingrese un password',
        'class': 'form-control',
        'autocomplete': 'off'
    }), required=True, label='Password')

    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={
        'placeholder': 'Repita el password',
        'class': 'form-control',
        'autocomplete': 'off'
    }), required=True, label='Confirmación de password')

    def clean(self):
        cleaned = super().clean()
        password = cleaned['password']
        confirm_password = cleaned['confirm_password']
        if password == confirm_password:
            return cleaned
        raise forms.ValidationError('Las contraseñas ingresadas deben coincidir')
