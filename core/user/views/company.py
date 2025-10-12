import json
import traceback
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import redirect
from django.views.generic import UpdateView
from config import settings
from core.pos.forms.company import CompanyOnboardingForm
from core.pos.models import Company


class MyCompanyEditView(LoginRequiredMixin, UpdateView):
    template_name = 'company/my_company_edit.html'
    model = Company
    form_class = CompanyOnboardingForm
    success_url = settings.LOGIN_REDIRECT_URL

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Mi empresa'
        context['list_url'] = self.success_url
        context['action'] = 'add' if not self.object.pk else 'edit'
        return context

    def get_object(self, queryset=None):
        company = getattr(self.request.user, 'owned_company', None)
        if company is None:
            return Company()
        return company

    def form_valid(self, form):
        instance = form.save(commit=False)
        if not getattr(self.request.user, 'is_superuser', False):
            instance.owner = self.request.user
        instance.save()

        user = self.request.user
        if hasattr(user, 'company_id') and not user.company_id:
            user.company = instance
            user.save(update_fields=['company'])

        return redirect(self.get_success_url())

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        data = {}
        action = request.POST.get('action', '').strip()

        try:
            if action in ['add', 'edit', 'create_or_edit']:
                form = self.form_class(
                    request.POST,
                    request.FILES,
                    instance=self.object if self.object.pk else None
                )

                # Blindar owner
                if not getattr(request.user, 'is_superuser', False):
                    form.instance.owner = request.user

                result = form.save(commit=True)
                instance = None

                # Manejar retorno flexible (instancia o dict)
                if isinstance(result, dict):
                    if 'error' in result and result['error']:
                        raise Exception(result['error'])
                    instance = result.get('instance', None)
                else:
                    instance = result

                if instance is None:
                    raise Exception("El formulario no devolvió una instancia válida de compañía.")

                # Asociar compañía al usuario si aún no la tiene
                user = request.user
                if hasattr(user, 'company_id') and not user.company_id:
                    user.company = instance
                    user.save(update_fields=['company'])

                data = {'success': True, 'id': instance.pk}

            else:
                # Si no viene una acción reconocida → usar flujo estándar
                return super().post(request, *args, **kwargs)

        except Exception as e:
            traceback.print_exc()
            data = {'error': str(e)}

        return HttpResponse(json.dumps(data), content_type='application/json')
