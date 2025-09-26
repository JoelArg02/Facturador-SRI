import json

from django.db.models import Q
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView

from core.pos.forms import Category, CategoryForm
from core.security.mixins import GroupPermissionMixin, AutoAssignCompanyMixin


class CategoryListView(GroupPermissionMixin, ListView):
    model = Category
    template_name = 'category/list.html'
    permission_required = 'view_category'

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        # Superuser ve todo; usuarios normales solo sus categorías (o nulas si se usan globales)
        if not user.is_superuser:
            company = getattr(user, 'company', None)
            if company:
                qs = qs.filter(company=company)
            else:
                qs = qs.none()
        return qs

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST['action']
        try:
            if action == 'search':
                data = []
                queryset = self.get_queryset()
                for i in queryset:
                    data.append(i.as_dict())
            else:
                data['error'] = 'No ha seleccionado ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Listado de {self.model._meta.verbose_name_plural}'
        context['create_url'] = reverse_lazy('category_create')
        return context


class CategoryCreateView(AutoAssignCompanyMixin, GroupPermissionMixin, CreateView):
    model = Category
    template_name = 'category/create.html'
    form_class = CategoryForm
    success_url = reverse_lazy('category_list')
    permission_required = 'add_category'

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
                    # Limitar a la compañía del usuario para validar unicidad por compañía
                    company = getattr(request.user, 'company', None)
                    if company:
                        filters &= Q(company=company)
                data['valid'] = not self.model.objects.filter(filters).exists() if filters.children else True
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


class CategoryUpdateView(AutoAssignCompanyMixin, GroupPermissionMixin, UpdateView):
    model = Category
    template_name = 'category/create.html'
    form_class = CategoryForm
    success_url = reverse_lazy('category_list')
    permission_required = 'change_category'

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
                    company = getattr(request.user, 'company', None)
                    if company:
                        filters &= Q(company=company)
                data['valid'] = not self.model.objects.filter(filters).exclude(id=self.object.id).exists() if filters.children else True
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


class CategoryDeleteView(GroupPermissionMixin, DeleteView):
    model = Category
    template_name = 'delete.html'
    success_url = reverse_lazy('category_list')
    permission_required = 'delete_category'

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
