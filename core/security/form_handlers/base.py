from django import forms


class BaseModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        first_field = next(iter(self.fields))
        self.fields[first_field].widget.attrs['autofocus'] = True

    def save(self, commit=True):
        # Mantener compatibilidad: si es válido devolver instancia del modelo;
        # si NO es válido devolver dict con errores (comportamiento previo usado en algunos lugares).
        if self.is_valid():
            instance = super().save(commit=commit)
            return instance
        data = {'error': ''}
        for field, errors in self.errors.items():
            data['error'] += errors[0]
        for error in self.non_field_errors():
            data['error'] += error
        return data
