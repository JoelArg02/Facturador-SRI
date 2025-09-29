import json

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import UpdateView

from config import settings
from core.pos.forms.company import CompanyOnboardingForm
from core.pos.models import Company


class MyCompanyEditView(LoginRequiredMixin, UpdateView):
    """Vista independiente para que el dueño edite o cree su Compañía.

    - No usa mixins de permisos/grupos del módulo POS.
    - Si el usuario no tiene compañía, se crea una en memoria y se permite guardar.
    - Excluye campos SMTP (el formulario CompanyOnboardingForm ya no los incluye).
    - Protege el owner para que siempre sea el usuario autenticado (no superuser).
    """

    template_name = 'company/owner_edit.html'
    model = Company
    form_class = CompanyOnboardingForm
    success_url = settings.LOGIN_REDIRECT_URL

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Mi empresa'
        context['list_url'] = self.success_url
        context['action'] = 'create_or_edit'
        return context

    def get_object(self, queryset=None):
        company = getattr(self.request.user, 'owned_company', None)
        if company is None:
            # Devolver instancia sin guardar para permitir creación en la misma vista
            return Company()
        return company

    def dispatch(self, request, *args, **kwargs):
        print('[MyCompanyEditView] START dispatch')
        owned = getattr(request.user, 'owned_company', None)
        print(f"[MyCompanyEditView] owned_company.id={getattr(owned,'id',None)} owner_id={getattr(owned,'owner_id',None)} user.id={getattr(request.user,'id',None)}")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        # Blindar owner y relacionar company al usuario si aún no existe
        instance = form.save(commit=False)
        if not getattr(self.request.user, 'is_superuser', False):
            instance.owner = self.request.user
        instance.save()

        # Asegurar relación inversa user.company si el modelo User la tiene
        user = self.request.user
        if hasattr(user, 'company_id') and not user.company_id:
            user.company = instance
            user.save(update_fields=['company'])

        return redirect(self.get_success_url())

    def post(self, request, *args, **kwargs):
        """Mismo contrato AJAX que el UpdateView de POS: maneja create_or_edit y load_certificate."""
        data = {}
        action = request.POST.get('action')
        try:
            if action == 'create_or_edit':
                instance = self.get_object()
                form = self.form_class(request.POST, request.FILES, instance=instance if instance.pk else None)
                if form.is_valid():
                    # Reutiliza form_valid para aplicar owner y vínculos
                    response = self.form_valid(form)
                    # Devolver datos mínimos; el BaseModelForm de onboarding no retorna as_dict
                    data = {'success': True, 'redirect': self.get_success_url()}
                else:
                    data['error'] = form.errors
            else:
                # Degradar a comportamiento normal
                return super().post(request, *args, **kwargs)
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')
