import json

from django.db import transaction
from django.db.models import Q
from django.forms import model_to_dict
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView, DeleteView, ListView

from core.security.forms import GroupForm, Group, GroupModule, Module, Permission
from core.security.mixins import GroupPermissionMixin


class GroupListView(GroupPermissionMixin, ListView):
    template_name = 'group/list.html'
    model = Group
    permission_required = 'view_group'

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST['action']
        try:
            if action == 'search':
                data = []
                for i in self.model.objects.all():
                    data.append(model_to_dict(i, exclude=['permissions']))
            elif action == 'search_permissions':
                data = []
                group = self.model.objects.get(pk=request.POST['id'])
                for i in group.permissions.all():
                    data.append(model_to_dict(i))
            elif action == 'search_modules':
                data = []
                group = self.model.objects.get(pk=request.POST['id'])
                for i in group.groupmodule_set.all():
                    data.append(i.module.as_dict())
            else:
                data['error'] = 'No ha seleccionado ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Listado de {self.model._meta.verbose_name_plural.title()}'
        context['create_url'] = reverse_lazy('group_create')
        return context


class GroupCreateView(GroupPermissionMixin, CreateView):
    model = Group
    template_name = 'group/create.html'
    form_class = GroupForm
    success_url = reverse_lazy('group_list')
    permission_required = 'add_group'

    def post(self, request, *args, **kwargs):
        action = request.POST['action']
        data = {}
        try:
            if action == 'add':
                with transaction.atomic():
                    group = Group.objects.create(name=request.POST['name'])
                    modules_data = json.loads(request.POST['items'])
                    modules = {int(module['id']): module for module in modules_data}
                    group_modules = [
                        GroupModule(group_id=group.id, module_id=module_id)
                        for module_id in modules.keys()
                    ]
                    GroupModule.objects.bulk_create(group_modules)
                    permissions = [
                        Permission.objects.get(pk=int(permission['id']))
                        for module in modules_data
                        for permission in module['permissions']
                    ]
                    group.permissions.add(*permissions)
            elif action == 'search_permissions':
                data = [
                    {
                        **module.as_dict(),
                        'checked': 0,
                        'permissions': [
                            {**permission, 'checked': 0} for permission in module.as_dict().get('permissions', [])
                        ]
                    }
                    for module in Module.objects.all()
                ]
            elif action == 'validate_data':
                field = request.POST['field']
                filters = Q()
                if field == 'name':
                    filters &= Q(name__iexact=request.POST['name'])
                data['valid'] = not self.model.objects.filter(filters).exists() if filters.children else True
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


class GroupUpdateView(GroupPermissionMixin, UpdateView):
    model = Group
    template_name = 'group/create.html'
    form_class = GroupForm
    success_url = reverse_lazy('group_list')
    permission_required = 'change_group'

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        action = request.POST['action']
        data = {}
        try:
            if action == 'edit':
                with transaction.atomic():
                    group = self.get_object()
                    group.name = request.POST['name']
                    group.save()
                    group.groupmodule_set.all().delete()
                    group.permissions.clear()
                    modules_data = json.loads(request.POST['items'])
                    modules = {int(module['id']): module for module in modules_data}
                    group_modules = [
                        GroupModule(group_id=group.id, module_id=module_id)
                        for module_id in modules.keys()
                    ]
                    GroupModule.objects.bulk_create(group_modules)
                    permissions = [
                        Permission.objects.get(pk=int(permission['id']))
                        for module in modules_data
                        for permission in module['permissions']
                    ]
                    group.permissions.add(*permissions)
            elif action == 'search_permissions':
                group = self.object
                data = [
                    {
                        **module.as_dict(),
                        'checked': 1 if group.groupmodule_set.filter(module_id=module.id).exists() else 0,
                        'permissions': [
                            {**permission, 'checked': 1 if group.permissions.filter(id=int(permission['id'])).exists() else 0}
                            for permission in module.as_dict().get('permissions', [])
                        ]
                    }
                    for module in Module.objects.all()
                ]
            elif action == 'validate_data':
                field = request.POST['field']
                filters = Q()
                if field == 'name':
                    filters &= Q(name__iexact=request.POST['name'])
                data['valid'] = not self.model.objects.filter(filters).exclude(id=self.object.id).exists() if filters.children else True
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


class GroupDeleteView(GroupPermissionMixin, DeleteView):
    model = Group
    template_name = 'delete.html'
    success_url = reverse_lazy('group_list')
    permission_required = 'delete_group'

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
