from django import forms
from core.pos.models import Provider
from core.security.form_handlers.helpers import update_form_fields_attributes

class ProviderForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        update_form_fields_attributes(self)
        self.fields['name'].widget.attrs['autofocus'] = True

    class Meta:
        model = Provider
        fields = '__all__'

    def save(self, commit=True):
        data = {}
        if self.is_valid():
            instance = super().save()
            data = instance.as_dict()
        else:
            data['error'] = self.errors
        return data