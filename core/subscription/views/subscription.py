import json
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.utils import timezone

from core.subscription.models import Subscription, Plan
from core.security.mixins import GroupPermissionMixin
from core.pos.models import Company


class SubscriptionListView(GroupPermissionMixin, ListView):
    model = Subscription
    template_name = 'subscription/subscription/list.html'
    permission_required = 'view_subscription'

    def get_queryset(self):
        qs = super().get_queryset().select_related('company', 'plan')
        return qs

    def serialize(self, s: Subscription):
        return {
            'id': s.id,
            'company': s.company.commercial_name,
            'company_id': s.company_id,
            'plan': s.plan.name,
            'plan_id': s.plan_id,
            'start_date': s.start_date.isoformat(),
            'end_date': s.end_date.isoformat() if s.end_date else None,
            'is_active': s.is_active,
            'expired': s.expired,
            'days_left': s.days_left,
        }

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST.get('action')
        try:
            if action == 'search':
                data = [self.serialize(s) for s in self.get_queryset()]
            elif action == 'delete':
                pk = request.POST.get('id')
                obj = Subscription.objects.get(pk=pk)
                obj.delete()
                data = {'success': True}
            else:
                data['error'] = 'Acción inválida'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data, default=str), content_type='application/json')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Suscripciones'
        ctx['create_url'] = reverse_lazy('subscription_create')
        return ctx


class SubscriptionCreateView(GroupPermissionMixin, CreateView):
    model = Subscription
    fields = ['company', 'plan', 'start_date', 'end_date', 'is_active']
    template_name = 'subscription/subscription/form.html'
    success_url = reverse_lazy('subscription_list')
    permission_required = 'add_subscription'

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST.get('action')
        try:
            if action == 'add':
                form = self.get_form()
                if form.is_valid():
                    obj = form.save()
                    data = {'id': obj.id, 'object': SubscriptionListView.serialize(self, obj)}
                else:
                    data['error'] = form.errors
            else:
                data['error'] = 'Acción inválida'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data, default=str), content_type='application/json')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Crear Suscripción'
        ctx['action'] = 'add'
        return ctx


class SubscriptionUpdateView(GroupPermissionMixin, UpdateView):
    model = Subscription
    fields = ['company', 'plan', 'start_date', 'end_date', 'is_active']
    template_name = 'subscription/subscription/form.html'
    success_url = reverse_lazy('subscription_list')
    permission_required = 'change_subscription'

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST.get('action')
        try:
            if action == 'edit':
                form = self.get_form()
                if form.is_valid():
                    obj = form.save()
                    data = {'id': obj.id, 'object': SubscriptionListView.serialize(self, obj)}
                else:
                    data['error'] = form.errors
            else:
                data['error'] = 'Acción inválida'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data, default=str), content_type='application/json')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Editar Suscripción'
        ctx['action'] = 'edit'
        return ctx


class SubscriptionDeleteView(GroupPermissionMixin, DeleteView):
    model = Subscription
    template_name = 'delete.html'
    success_url = reverse_lazy('subscription_list')
    permission_required = 'delete_subscription'

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            self.get_object().delete()
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Eliminar Suscripción'
        ctx['list_url'] = self.success_url
        return ctx
