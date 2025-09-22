from django import forms


class BaseModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        first_field = next(iter(self.fields))
        self.fields[first_field].widget.attrs['autofocus'] = True

    def save(self, commit=True):
        data = {}
        if self.is_valid():
            super().save(commit=commit)
        else:
            data['error'] = ''
            for field, errors in self.errors.items():
                data['error'] += errors[0]
            non_field_errors = self.non_field_errors()
            if non_field_errors:
                for error in non_field_errors:
                    data['error'] += error
        return data
