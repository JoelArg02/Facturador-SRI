from django import forms
from django.forms import model_to_dict
from crum import get_current_request


class BaseModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        first_field = next(iter(self.fields))
        self.fields[first_field].widget.attrs['autofocus'] = True

    def save(self, commit=True):
        if self.is_valid():
            instance = super().save(commit=False)

            if hasattr(instance, 'company') and getattr(instance, 'company', None) is None:
                try:
                    request = get_current_request()
                    if request is not None:
                        company = getattr(request, 'company', None) or getattr(getattr(request, 'user', None), 'company', None)
                        if company is not None and not getattr(getattr(request, 'user', None), 'is_superuser', False):
                            setattr(instance, 'company', company)
                except Exception:
                    pass

            if commit:
                instance.save()

            if hasattr(instance, 'as_dict') and callable(getattr(instance, 'as_dict')):
                try:
                    return instance.as_dict()
                except Exception:
                    pass

            try:
                return model_to_dict(instance)
            except Exception:
                return {'id': getattr(instance, 'pk', None)}

        return {'error': self.errors}

    def save_instance(self, commit=True):
        """
        Igual que save(), pero retorna la instancia del modelo en lugar de un dict.
        Útil para vistas genéricas (Create/UpdateView) que esperan un objeto modelo.
        """
        if not self.is_valid():
            raise ValueError(self.errors.as_json())

        instance = super().save(commit=False)

        # Asegurar asignación de company como en save()
        if hasattr(instance, 'company') and getattr(instance, 'company', None) is None:
            try:
                request = get_current_request()
                if request is not None:
                    company = getattr(request, 'company', None) or getattr(getattr(request, 'user', None), 'company', None)
                    if company is not None and not getattr(getattr(request, 'user', None), 'is_superuser', False):
                        setattr(instance, 'company', company)
            except Exception:
                pass

        if commit:
            instance.save()
        return instance
