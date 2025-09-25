import json

from django.http import HttpResponse, HttpResponseForbidden
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView

from core.subscription.forms import SubscriptionForm
from core.subscription.models import Subscription, Plan
from core.security.mixins import GroupPermissionMixin
from core.subscription.services import count_for


class SubscriptionListView(GroupPermissionMixin, ListView):
    model = Subscription
    template_name = 'subscription/subscription/list.html'
    permission_required = 'view_subscription'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            return HttpResponseForbidden('Solo el super administrador puede acceder a las suscripciones globales.')
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related('user__company', 'plan')
            .order_by('user__username')
        )

    def get_usage(self, company, plan: Plan):
        metrics = {
            'invoice': ('Facturas', plan.max_invoices, 'core.pos.Invoice'),
            'customer': ('Clientes', plan.max_customers, 'core.pos.Customer'),
            'product': ('Productos', plan.max_products, 'core.pos.Product'),
        }
        usage = {}
        for key, (label, limit, model_label) in metrics.items():
            used = count_for(company, model_label) if company else 0
            if not limit:
                display = f'{used} / ∞'
                percent = None
            else:
                percent = round((used / limit) * 100, 2)
                display = f'{used} / {limit}'
            usage[key] = {
                'label': label,
                'used': used,
                'limit': limit,
                'percent': percent,
                'display': display,
            }
        return usage

    def serialize(self, s: Subscription):
        company = s.company
        admin_name = s.user.get_full_name() or s.user.username
        admin_groups = ', '.join([g.name for g in s.user.groups.all()[:2]])
        return {
            'id': s.id,
            'owner': {
                'id': s.user_id,
                'name': admin_name,
                'username': s.user.username,
                'email': getattr(s.user, 'email', ''),
                'groups': admin_groups,
            },
            'company': {
                'id': getattr(company, 'id', None),
                'name': getattr(company, 'commercial_name', 'Sin asignar'),
                'ruc': getattr(company, 'ruc', ''),
            },
            'plan': {
                'id': s.plan_id,
                'name': s.plan.name,
            },
            'usage': self.get_usage(company, s.plan),
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
            if not request.user.is_superuser:
                return HttpResponseForbidden(json.dumps({'error': 'Acceso restringido a super administradores.'}), content_type='application/json')
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
    form_class = SubscriptionForm
    template_name = 'subscription/subscription/form.html'
    success_url = reverse_lazy('subscription_list')
    permission_required = 'add_subscription'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            return HttpResponseForbidden('Solo el super administrador puede crear suscripciones.')
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST.get('action')
        try:
            if not request.user.is_superuser:
                return HttpResponseForbidden(json.dumps({'error': 'Acceso restringido a super administradores.'}), content_type='application/json')
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
    form_class = SubscriptionForm
    template_name = 'subscription/subscription/form.html'
    success_url = reverse_lazy('subscription_list')
    permission_required = 'change_subscription'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            return HttpResponseForbidden('Solo el super administrador puede editar suscripciones.')
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST.get('action')
        try:
            if not request.user.is_superuser:
                return HttpResponseForbidden(json.dumps({'error': 'Acceso restringido a super administradores.'}), content_type='application/json')
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

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            return HttpResponseForbidden('Solo el super administrador puede eliminar suscripciones.')
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            if not request.user.is_superuser:
                return HttpResponseForbidden(json.dumps({'error': 'Acceso restringido a super administradores.'}), content_type='application/json')
            self.get_object().delete()
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Eliminar Suscripción'
        ctx['list_url'] = self.success_url
        return ctx
