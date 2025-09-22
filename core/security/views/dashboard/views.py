import json

from django.http import HttpResponse
from django.views.generic import UpdateView

from config import settings
from core.security.forms import Dashboard, DashboardForm
from core.security.mixins import GroupModuleMixin


class DashboardUpdateView(GroupModuleMixin, UpdateView):
    model = Dashboard
    template_name = 'dashboard/create.html'
    form_class = DashboardForm
    success_url = settings.LOGIN_REDIRECT_URL

    def get_object(self, queryset=None):
        return Dashboard.objects.first() or Dashboard()

    def get_form(self, form_class=None):
        form = super(DashboardUpdateView, self).get_form(form_class)
        instance = self.get_object()
        if instance.pk:
            form.instance = instance
        return form

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST['action']
        try:
            if action == 'edit':
                data = self.get_form().save()
            else:
                data['error'] = 'No ha seleccionado ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context['title'] = f'Actualización del {self.model._meta.verbose_name}'
        context['list_url'] = self.success_url
        context['action'] = 'edit'
        return context
