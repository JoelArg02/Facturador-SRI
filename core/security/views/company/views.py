import json

from django.http import HttpResponse
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView, DeleteView, ListView

from core.pos.models import Company
from core.security.forms import CompanyAdminForm
from core.security.mixins import GroupPermissionMixin


class CompanyAdminListView(GroupPermissionMixin, ListView):
    template_name = 'company/list.html'
    model = Company
    permission_required = 'view_company'

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST['action']
        try:
            if action == 'search':
                data = []
                for item in self.model.objects.select_related('owner').all():
                    info = item.as_dict()
                    info['owner_name'] = item.owner.get_full_name() if item.owner else ''
                    info['owner_username'] = item.owner.username if item.owner else ''
                    data.append(info)
            else:
                data['error'] = 'No ha seleccionado ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Listado de {self.model._meta.verbose_name_plural}'
        context['create_url'] = reverse_lazy('company_admin_create')
        return context


class CompanyAdminCreateView(GroupPermissionMixin, CreateView):
    model = Company
    template_name = 'company/create.html'
    form_class = CompanyAdminForm
    success_url = reverse_lazy('company_admin_list')
    permission_required = 'add_company'

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST['action']
        try:
            if action == 'add':
                data = self.get_form().save()
                # Si el formulario devuelve una instancia del modelo, convertirla a dict serializable
                if isinstance(data, Company):
                    data = data.as_dict()
            else:
                data['error'] = 'No ha seleccionado ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context['title'] = f'Creación de una {self.model._meta.verbose_name}'
        context['list_url'] = self.success_url
        context['action'] = 'add'
        return context


class CompanyAdminUpdateView(GroupPermissionMixin, UpdateView):
    model = Company
    template_name = 'company/create.html'
    form_class = CompanyAdminForm
    success_url = reverse_lazy('company_admin_list')
    permission_required = 'change_company'

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST['action']
        try:
            if action == 'edit':
                data = self.get_form().save()
                # Si el formulario devuelve una instancia del modelo, convertirla a dict serializable
                if isinstance(data, Company):
                    data = data.as_dict()
            else:
                data['error'] = 'No ha seleccionado ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context['title'] = f'Edición de una {self.model._meta.verbose_name}'
        context['list_url'] = self.success_url
        context['action'] = 'edit'
        return context


class CompanyAdminDeleteView(GroupPermissionMixin, DeleteView):
    model = Company
    template_name = 'delete.html'
    success_url = reverse_lazy('company_admin_list')
    permission_required = 'delete_company'

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            self.get_object().delete()
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Eliminación de una {self.model._meta.verbose_name}'
        context['list_url'] = self.success_url
        return context
