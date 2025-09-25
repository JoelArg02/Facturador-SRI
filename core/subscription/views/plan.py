import json
from django.http import HttpResponse
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView

from core.subscription.models import Plan
from core.security.mixins import GroupPermissionMixin


class PlanListView(GroupPermissionMixin, ListView):
    model = Plan
    template_name = 'subscription/plan/list.html'
    permission_required = 'view_plan'

    def serialize(self, obj: Plan):
        return {
            'id': obj.id,
            'name': obj.name,
            'description': obj.description or '',
            'max_invoices': obj.max_invoices,
            'max_customers': obj.max_customers,
            'max_products': obj.max_products,
            'price': float(obj.price),
            'period_days': obj.period_days,
            'active': obj.active,
        }

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST.get('action')
        try:
            if action == 'search':
                data = [self.serialize(p) for p in self.get_queryset()]
            elif action == 'delete':
                pk = request.POST.get('id')
                obj = Plan.objects.get(pk=pk)
                obj.delete()
                data = {'success': True}
            else:
                data['error'] = 'Acción no válida'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data, default=str), content_type='application/json')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Planes'
        ctx['create_url'] = reverse_lazy('plan_create')
        return ctx


class PlanCreateView(GroupPermissionMixin, CreateView):
    model = Plan
    fields = ['name', 'description', 'max_invoices', 'max_customers', 'max_products', 'price', 'period_days', 'active']
    template_name = 'subscription/plan/form.html'
    success_url = reverse_lazy('plan_list')
    permission_required = 'add_plan'
    def serialize(self, obj: Plan):
        return PlanListView.serialize(self, obj)

    def post(self, request, *args, **kwargs):
        # Determinar si es AJAX (modal) o flujo normal (vista completa)
        action = request.POST.get('action')
        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest' or action == 'add'
        if not is_ajax:
            # Delegamos en CreateView para validación estándar; form_valid agregará mensaje
            return super().post(request, *args, **kwargs)
        form = self.get_form()
        if form.is_valid():
            self.object = form.save()
            data = {'success': True, 'object': self.serialize(self.object)}
        else:
            data = {'error': form.errors}
        return HttpResponse(json.dumps(data, default=str), content_type='application/json')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Plan "{self.object.name}" creado correctamente.')
        return response

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Crear Plan'
        ctx['action'] = 'add'
        return ctx


class PlanUpdateView(GroupPermissionMixin, UpdateView):
    model = Plan
    fields = ['name', 'description', 'max_invoices', 'max_customers', 'max_products', 'price', 'period_days', 'active']
    template_name = 'subscription/plan/form.html'
    success_url = reverse_lazy('plan_list')
    permission_required = 'change_plan'
    def serialize(self, obj: Plan):
        return PlanListView.serialize(self, obj)

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action')
        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest' or action == 'edit'
        if not is_ajax:
            return super().post(request, *args, **kwargs)
        form = self.get_form()
        if form.is_valid():
            self.object = form.save()
            data = {'success': True, 'object': self.serialize(self.object)}
        else:
            data = {'error': form.errors}
        return HttpResponse(json.dumps(data, default=str), content_type='application/json')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Plan "{self.object.name}" actualizado correctamente.')
        return response

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Editar Plan'
        ctx['action'] = 'edit'
        return ctx


class PlanDeleteView(GroupPermissionMixin, DeleteView):
    model = Plan
    template_name = 'delete.html'
    success_url = reverse_lazy('plan_list')
    permission_required = 'delete_plan'

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            self.get_object().delete()
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Eliminar Plan'
        ctx['list_url'] = self.success_url
        return ctx
