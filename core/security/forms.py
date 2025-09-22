from django import forms

from core.security.form_handlers.base import BaseModelForm
from core.security.form_handlers.helpers import update_form_fields_attributes
from .models import *


class ModuleTypeForm(BaseModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        update_form_fields_attributes(self)

    class Meta:
        model = ModuleType
        fields = '__all__'


class ModuleForm(BaseModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        update_form_fields_attributes(self, exclude_fields=['module_type', 'permissions'])

    class Meta:
        model = Module
        fields = '__all__'
        widgets = {
            'permissions': forms.SelectMultiple(attrs={'class': 'form-control select2', 'multiple': 'multiple', 'style': 'width:100%'}),
        }


class GroupForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        update_form_fields_attributes(self)
        self.fields['name'].widget.attrs.update({'placeholder': 'Ingrese un nombre'})

    class Meta:
        model = Group
        fields = '__all__'


class DashboardForm(BaseModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        update_form_fields_attributes(self)

    class Meta:
        model = Dashboard
        fields = '__all__'
