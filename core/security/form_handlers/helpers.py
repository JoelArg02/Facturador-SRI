from datetime import datetime
from django import forms


def update_form_fields_attributes(form, exclude_fields=None):
    if not exclude_fields:
        exclude_fields = []
    for object_field in form.visible_fields():
        if object_field.name in exclude_fields:
            continue
        if isinstance(object_field.field, forms.IntegerField):
            object_field.field.widget = forms.TextInput(attrs={
                'class': 'form-control only-numbers',
                'autocomplete': 'off',
                'placeholder': object_field.help_text
            })
        elif isinstance(object_field.field, forms.DecimalField):
            object_field.field.widget.attrs.update({
                'class': 'form-control only-decimals'
            })
        elif isinstance(object_field.field, (forms.CharField, forms.GenericIPAddressField)):
            object_field.field.widget.attrs.update({
                'class': 'form-control',
                'autocomplete': 'off',
                'placeholder': object_field.help_text
            })
        elif isinstance(object_field.field, (forms.ModelChoiceField, forms.TypedChoiceField, forms.ChoiceField)):
            object_field.field.widget.attrs.update({
                'class': 'form-control select2',
                'style': 'width: 100%;'
            })
        elif isinstance(object_field.field, forms.DateField):
            object_field.field.widget.attrs.update({
                'class': 'form-control',
                'id': object_field.name,
                'value': datetime.now().strftime('%Y-%m-%d'),
                'data-toggle': 'datetimepicker',
                'data-target': f'#{object_field.name}'
            })
            object_field.field.widget.format = '%Y-%m-%d'
        elif isinstance(object_field.field, forms.BooleanField):
            object_field.field.widget.attrs.update({
                'class': 'form-control-checkbox'
            })
        elif isinstance(object_field.field, (forms.ImageField, forms.FileField)):
            object_field.field.widget.attrs.update({
                'class': 'form-control'
            })


def update_field_class(field, name):
    attrs = field.widget.attrs
    class_value = attrs.get('class', '')
    class_value += f' {name}'
    attrs['class'] = class_value
