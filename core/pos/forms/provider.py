from django import forms
from crum import get_current_request
from core.pos.models import Provider
from core.security.form_handlers.base import BaseModelForm
from core.security.form_handlers.helpers import update_form_fields_attributes

class ProviderForm(BaseModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        update_form_fields_attributes(self)
        self.fields['name'].widget.attrs['autofocus'] = True

    class Meta:
        model = Provider
        fields = '__all__'

    def clean(self):
        cleaned = super().clean()
        company = cleaned.get('company')
        try:
            request = get_current_request()
        except Exception:
            request = None

        if company is None and request is not None:
            user = getattr(request, 'user', None)
            is_super = getattr(user, 'is_superuser', False)
            if not is_super:
                company = getattr(request, 'company', None) or getattr(user, 'company', None)
                if company is not None:
                    cleaned['company'] = company

        if cleaned.get('company') is None:
            self.add_error('company', 'Debe seleccionar la compañía.')
        return cleaned