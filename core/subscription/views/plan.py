import json

from django.contrib import messages
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from core.security.mixins import GroupPermissionMixin
from core.subscription.models import Plan


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
        # Solo tratamos como AJAX si realmente viene el header de XMLHttpRequest.
        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
        if not is_ajax:
            return super().post(request, *args, **kwargs)
        form = self.get_form()
        if form.is_valid():
            self.object = form.save()
            data = {
                'success': True,
                'icon': 'success',
                # Por solicitud del usuario no se enviará mensaje de éxito
                'message': '',
                'redirect': str(self.success_url),
                'object': self.serialize(self.object)
            }
        else:
            data = {
                'success': False,
                'icon': 'error',
                # Por solicitud del usuario no se enviará mensaje de error general
                'message': '',
                'error': form.errors
            }
        return HttpResponse(json.dumps(data, default=str), content_type='application/json')

    def form_valid(self, form):
        response = super().form_valid(form)
        # Se elimina el mensaje flash de éxito
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
        # Asegurar self.object antes de construir formulario
        self.object = self.get_object()
        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
        if not is_ajax:
            return super().post(request, *args, **kwargs)
        form = self.get_form()
        if form.is_valid():
            self.object = form.save()
            data = {
                'success': True,
                'icon': 'success',
                # Por solicitud del usuario no se enviará mensaje de éxito
                'message': '',
                'redirect': str(self.success_url),
                'object': self.serialize(self.object)
            }
        else:
            data = {
                'success': False,
                'icon': 'error',
                # Por solicitud del usuario no se enviará mensaje de error general
                'message': '',
                'error': form.errors
            }
        return HttpResponse(json.dumps(data, default=str), content_type='application/json')

    def form_valid(self, form):
        response = super().form_valid(form)
        # Se elimina el mensaje flash de éxito
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
