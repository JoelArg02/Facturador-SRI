import json

from django.db.models import Q
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView

from core.pos.forms import Provider, ProviderForm
from core.pos.utilities.sri import SRI
from core.security.mixins import GroupPermissionMixin


class ProviderListView(GroupPermissionMixin, ListView):
    model = Provider
    template_name = 'provider/list.html'
    permission_required = 'view_provider'

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST['action']
        try:
            if action == 'search':
                data = []
                for i in self.model.objects.all():
                    data.append(i.as_dict())
            else:
                data['error'] = 'No ha seleccionado ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Listado de {self.model._meta.verbose_name_plural}'
        context['create_url'] = reverse_lazy('provider_create')
        return context


class ProviderCreateView(GroupPermissionMixin, CreateView):
    model = Provider
    template_name = 'provider/create.html'
    form_class = ProviderForm
    success_url = reverse_lazy('provider_list')
    permission_required = 'add_provider'

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST['action']
        try:
            if action == 'add':
                data = self.get_form().save()
            elif action == 'validate_data':
                field = request.POST['field']
                filters = Q()
                if field == 'name':
                    filters &= Q(name__iexact=request.POST['name'])
                elif field == 'ruc':
                    filters &= Q(ruc__iexact=request.POST['ruc'])
                elif field == 'mobile':
                    filters &= Q(mobile__iexact=request.POST['mobile'])
                elif field == 'email':
                    filters &= Q(email__iexact=request.POST['email'])
                data['valid'] = not self.model.objects.filter(filters).exists() if filters.children else True
            elif action == 'search_ruc_in_sri':
                data = SRI().search_ruc_in_sri(ruc=request.POST['ruc'])
            else:
                data['error'] = 'No ha seleccionado ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context['title'] = f'Creación de un {self.model._meta.verbose_name}'
        context['list_url'] = self.success_url
        context['action'] = 'add'
        return context


class ProviderUpdateView(GroupPermissionMixin, UpdateView):
    model = Provider
    template_name = 'provider/create.html'
    form_class = ProviderForm
    success_url = reverse_lazy('provider_list')
    permission_required = 'change_provider'

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST['action']
        try:
            if action == 'edit':
                data = self.get_form().save()
            elif action == 'validate_data':
                field = request.POST['field']
                filters = Q()
                if field == 'name':
                    filters &= Q(name__iexact=request.POST['name'])
                elif field == 'ruc':
                    filters &= Q(ruc__iexact=request.POST['ruc'])
                elif field == 'mobile':
                    filters &= Q(mobile__iexact=request.POST['mobile'])
                elif field == 'email':
                    filters &= Q(email__iexact=request.POST['email'])
                data['valid'] = not self.model.objects.filter(filters).exclude(id=self.object.id).exists() if filters.children else True
            elif action == 'search_ruc_in_sri':
                data = SRI().search_ruc_in_sri(ruc=request.POST['ruc'])
            else:
                data['error'] = 'No ha seleccionado ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context['title'] = f'Edición de un {self.model._meta.verbose_name}'
        context['list_url'] = self.success_url
        context['action'] = 'edit'
        return context


class ProviderDeleteView(GroupPermissionMixin, DeleteView):
    model = Provider
    template_name = 'delete.html'
    success_url = reverse_lazy('provider_list')
    permission_required = 'delete_provider'

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            self.get_object().delete()
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Eliminación de un {self.model._meta.verbose_name}'
        context['list_url'] = self.success_url
        return context
