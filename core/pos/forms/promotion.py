from django import forms
from core.pos.models import Promotion
from core.security.form_handlers.base import BaseModelForm
from core.security.form_handlers.helpers import update_form_fields_attributes

class PromotionForm(BaseModelForm):
    date_range = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'form-control',
        'autocomplete': 'off'
    }), label='Fecha de inicio y finalización')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        update_form_fields_attributes(self)
        self.fields['date_range'].widget.attrs['autofocus'] = True

    class Meta:
        model = Promotion
        fields = '__all__'
        exclude = ['active']