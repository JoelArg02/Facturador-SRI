import json
import smtplib
from datetime import date, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from django.http import HttpResponse, HttpResponseForbidden, HttpResponseRedirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, TemplateView, View
from django.contrib.auth import logout
from django.conf import settings

from core.subscription.forms import SubscriptionForm
from core.subscription.models import Subscription, Plan
from core.subscription.repositories.plan_repository import PlanRepository
from core.security.mixins import GroupPermissionMixin
from core.subscription.services import count_for


def send_subscription_email(user, subscription):
    """Función auxiliar para envío de emails (implementar según necesidades)"""
    # TODO: Implementar envío de email
    pass


def get_usage(company, plan):
    """Función auxiliar para obtener uso actual del plan"""
    if not company:
        return {}
    
    # Obtener conteos usando el servicio existente
    usage = {
        'invoices': count_for(company, 'invoice'),
        'clients': count_for(company, 'client'),
        'products': count_for(company, 'product'),
        'employees': count_for(company, 'employee'),
    }
    
    # Agregar límites del plan si están definidos
    if hasattr(plan, 'max_invoices'):
        usage['max_invoices'] = plan.max_invoices
    if hasattr(plan, 'max_clients'):
        usage['max_clients'] = plan.max_clients
    
    return usage


def get_all_subscriptions():
    """Función independiente para obtener todas las suscripciones."""
    try:
        subscriptions = (
            Subscription.objects
            .select_related('user__company', 'plan', 'user')
            .prefetch_related('user__groups')
            .order_by('-created_at')
        )
        
        result = []
        for s in subscriptions:
            try:
                company = s.company
                admin_name = s.user.get_full_name() or s.user.username
                admin_groups = ', '.join([g.name for g in s.user.groups.all()[:2]])
                
                subscription_data = {
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
                    'usage': get_usage(company, s.plan),
                    'start_date': s.start_date.isoformat() if s.start_date else None,
                    'end_date': s.end_date.isoformat() if s.end_date else None,
                    'is_active': s.is_active,
                    'expired': s.expired,
                    'days_left': s.days_left,
                }
                result.append(subscription_data)
            except Exception as e:
                print(f"Error serializando suscripción {s.id}: {e}")
                continue
                
        return result
    except Exception as e:
        print(f"Error obteniendo suscripciones: {e}")
        return []


def get_usage(company, plan: Plan):
    """Calcula el uso actual de recursos para una compañía y plan."""
    metrics = {
        'invoice': ('Facturas', plan.max_invoices, 'pos.Invoice'),
        'customer': ('Clientes', plan.max_customers, 'pos.Customer'),
        'product': ('Productos', plan.max_products, 'pos.Product'),
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


def send_subscription_email(user, subscription):
    """Envía correo de notificación de activación de suscripción."""
    if not user.email:
        return

    try:
        plan = subscription.plan
        company = subscription.company
        
        message = MIMEMultipart('alternative')
        message['Subject'] = f'Plan {plan.name} activado - Facturador SRI'
        message['From'] = settings.EMAIL_HOST_USER
        message['To'] = user.email

        # Texto plano
        text_content = f"""
Hola {user.get_full_name() or user.username},

¡Su plan {plan.name} ha sido activado exitosamente!

Características de su plan:
- Máximo de facturas: {plan.max_invoices if plan.max_invoices else 'Ilimitadas'}
- Máximo de clientes: {plan.max_customers if plan.max_customers else 'Ilimitados'}
- Máximo de productos: {plan.max_products if plan.max_products else 'Ilimitados'}
- Duración: {plan.period_days} días
- Precio: ${plan.price}

Vigencia: {subscription.start_date} hasta {subscription.end_date}

¡Gracias por confiar en nosotros!
"""

        # HTML con diseño
        html_content = f"""
<html>
<body style="font-family:Arial, sans-serif; background:#f4f4f7; padding:20px;">
    <table style="max-width:600px; margin:auto; background:#ffffff; border-radius:8px; overflow:hidden; box-shadow:0 2px 6px rgba(0,0,0,0.1);">
        <tr>
            <td style="background:#10b981; color:#fff; padding:20px; text-align:center;">
                <h2 style="margin:0;">✅ Plan Activado</h2>
            </td>
        </tr>
        <tr>
            <td style="padding:30px; color:#2d3748;">
                <p style="font-size:16px;">Hola <strong>{user.get_full_name() or user.username}</strong>,</p>
                <p style="font-size:16px;">¡Su plan <strong>{plan.name}</strong> ha sido activado exitosamente!</p>
                
                <div style="background:#f7fafc; padding:20px; border-radius:8px; margin:20px 0;">
                    <h3 style="color:#2d3748; margin-top:0;">Características de su plan:</h3>
                    <ul style="list-style:none; padding:0;">
                        <li style="padding:8px 0; border-bottom:1px solid #e2e8f0;">
                            <strong>Facturas:</strong> {plan.max_invoices if plan.max_invoices else 'Ilimitadas'}
                        </li>
                        <li style="padding:8px 0; border-bottom:1px solid #e2e8f0;">
                            <strong>Clientes:</strong> {plan.max_customers if plan.max_customers else 'Ilimitados'}
                        </li>
                        <li style="padding:8px 0; border-bottom:1px solid #e2e8f0;">
                            <strong>Productos:</strong> {plan.max_products if plan.max_products else 'Ilimitados'}
                        </li>
                        <li style="padding:8px 0; border-bottom:1px solid #e2e8f0;">
                            <strong>Duración:</strong> {plan.period_days} días
                        </li>
                        <li style="padding:8px 0;">
                            <strong>Precio:</strong> ${plan.price}
                        </li>
                    </ul>
                </div>
                
                <p style="font-size:16px; background:#ebf8ff; padding:15px; border-radius:8px; border-left:4px solid #3182ce;">
                    <strong>Vigencia:</strong> {subscription.start_date} hasta {subscription.end_date}
                </p>
                
                <p style="font-size:16px;">¡Gracias por confiar en nosotros!</p>
            </td>
        </tr>
        <tr>
            <td style="background:#edf2f7; color:#4a5568; padding:15px; text-align:center; font-size:12px;">
                © 2025 OptimusPos - Todos los derechos reservados.
            </td>
        </tr>
    </table>
</body>
</html>
        """

        message.attach(MIMEText(text_content, 'plain'))
        message.attach(MIMEText(html_content, 'html'))

        # Envío por SSL en puerto 465
        server = smtplib.SMTP_SSL(settings.EMAIL_HOST, 465)
        server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
        server.sendmail(settings.EMAIL_HOST_USER, [user.email], message.as_string())
        server.quit()

    except Exception:
        # Se silencian errores de correo para no interrumpir el flujo
        pass


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
            'usage': get_usage(company, s.plan),
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
                print("DEBUG: Ejecutando búsqueda de suscripciones...")
                data = get_all_subscriptions()
                print(f"DEBUG: Se encontraron {len(data)} suscripciones")
            elif action == 'delete':
                pk = request.POST.get('id')
                obj = Subscription.objects.get(pk=pk)
                obj.delete()
                data = {'success': True}
            else:
                data['error'] = 'Acción inválida'
        except Exception as e:
            print(f"DEBUG: Error en SubscriptionListView.post: {e}")
            data['error'] = str(e)
        
        print(f"DEBUG: Respuesta final: {data}")
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
        action = request.POST.get('action')
        
        # Si no es una petición AJAX, usar el comportamiento estándar de CreateView
        if not request.headers.get('X-Requested-With') == 'XMLHttpRequest' and action != 'add':
            return super().post(request, *args, **kwargs)
        
        # Manejo AJAX para peticiones con action=add
        data = {}
        try:
            if not request.user.is_superuser:
                return HttpResponseForbidden(json.dumps({'error': 'Acceso restringido a super administradores.'}), content_type='application/json')
            if action == 'add':
                form = self.get_form()
                if form.is_valid():
                    obj = form.save()
                    # Enviar correo de notificación si la suscripción está activa
                    if obj.is_active:
                        send_subscription_email(obj.user, obj)
                    
                    # Si es petición AJAX, devolver JSON
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        # Serializar objeto para respuesta
                        company = obj.company
                        admin_name = obj.user.get_full_name() or obj.user.username
                        admin_groups = ', '.join([g.name for g in obj.user.groups.all()[:2]])
                        serialized_obj = {
                            'id': obj.id,
                            'owner': {
                                'id': obj.user_id,
                                'name': admin_name,
                                'username': obj.user.username,
                                'email': getattr(obj.user, 'email', ''),
                                'groups': admin_groups,
                            },
                            'company': {
                                'id': getattr(company, 'id', None),
                                'name': getattr(company, 'commercial_name', 'Sin asignar'),
                                'ruc': getattr(company, 'ruc', ''),
                            },
                            'plan': {
                                'id': obj.plan_id,
                                'name': obj.plan.name,
                            },
                            'usage': get_usage(company, obj.plan),
                            'start_date': obj.start_date.isoformat(),
                            'end_date': obj.end_date.isoformat() if obj.end_date else None,
                            'is_active': obj.is_active,
                            'expired': obj.expired,
                            'days_left': obj.days_left,
                        }
                        data = {'id': obj.id, 'object': serialized_obj}
                        return HttpResponse(json.dumps(data, default=str), content_type='application/json')
                    else:
                        # Si no es AJAX, redireccionar
                        return HttpResponseRedirect(self.success_url)
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

    def get(self, request, *args, **kwargs):
        # Si es petición AJAX para modal, devolver datos de la suscripción
        # Detectar AJAX por cabecera o Accept header
        is_ajax = (
            request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 
            'application/json' in request.headers.get('Accept', '') or
            request.GET.get('format') == 'json'
        )
        if is_ajax:
            subscription = self.get_object()
            available_plans = PlanRepository.get_plans_for_update(subscription.plan_id)
            
            data = {
                'subscription': {
                    'id': subscription.id,
                    'user_name': subscription.user.get_full_name() or subscription.user.username,
                    'plan': {
                        'id': subscription.plan.id,
                        'name': subscription.plan.name,
                        'price': float(subscription.plan.price)
                    },
                    'is_active': subscription.is_active,
                    'start_date': subscription.start_date.isoformat(),
                    'end_date': subscription.end_date.isoformat() if subscription.end_date else None,
                    'expired': subscription.expired,
                    'days_left': subscription.days_left
                },
                'available_plans': [
                    {
                        'id': plan.id,
                        'name': plan.name,
                        'price': float(plan.price),
                        'max_invoices': plan.max_invoices,
                        'max_customers': plan.max_customers,
                        'max_products': plan.max_products,
                        'period_days': plan.period_days
                    }
                    for plan in available_plans
                ]
            }
            return HttpResponse(json.dumps(data, default=str), content_type='application/json')
        
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST.get('action')
        try:
            if not request.user.is_superuser:
                return HttpResponseForbidden(json.dumps({'error': 'Acceso restringido a super administradores.'}), content_type='application/json')
            
            subscription = self.get_object()
            
            if action == 'change_plan':
                new_plan_id = request.POST.get('new_plan_id')
                new_plan = PlanRepository.get_plan_by_id(new_plan_id)
                
                if not new_plan:
                    data['error'] = 'Plan no encontrado o inactivo'
                else:
                    old_plan_name = subscription.plan.name
                    subscription.plan = new_plan
                    # Recalcular fecha de fin basada en el nuevo plan
                    if subscription.start_date:
                        subscription.end_date = subscription.start_date + timedelta(days=new_plan.period_days)
                    subscription.save()
                    
                    data['success'] = f'Plan cambiado de {old_plan_name} a {new_plan.name}'
                    data['subscription'] = self._serialize_subscription(subscription)
                    
            elif action == 'suspend':
                subscription.is_active = False
                subscription.canceled_at = timezone.now()
                subscription.save()
                
                data['success'] = 'Suscripción suspendida correctamente'
                data['subscription'] = self._serialize_subscription(subscription)
                
            elif action == 'reactivate':
                subscription.is_active = True
                subscription.canceled_at = None
                subscription.save()
                
                data['success'] = 'Suscripción reactivada correctamente'
                data['subscription'] = self._serialize_subscription(subscription)
                
            elif action == 'edit':
                # Comportamiento original para edición completa
                old_instance = self.get_object()
                was_active = old_instance.is_active
                form = self.get_form()
                if form.is_valid():
                    obj = form.save()
                    # Enviar correo si se activó la suscripción (no estaba activa antes)
                    if obj.is_active and not was_active:
                        send_subscription_email(obj.user, obj)
                    
                    data['success'] = 'Suscripción actualizada correctamente'
                    data['subscription'] = self._serialize_subscription(obj)
                else:
                    data['error'] = form.errors
            else:
                data['error'] = 'Acción inválida'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data, default=str), content_type='application/json')
    
    def _serialize_subscription(self, subscription):
        """Helper para serializar una suscripción"""
        company = subscription.company
        admin_name = subscription.user.get_full_name() or subscription.user.username
        admin_groups = ', '.join([g.name for g in subscription.user.groups.all()[:2]])
        return {
            'id': subscription.id,
            'owner': {
                'id': subscription.user_id,
                'name': admin_name,
                'username': subscription.user.username,
                'email': getattr(subscription.user, 'email', ''),
                'groups': admin_groups,
            },
            'company': {
                'id': getattr(company, 'id', None),
                'name': getattr(company, 'commercial_name', 'Sin asignar'),
                'ruc': getattr(company, 'ruc', ''),
            },
            'plan': {
                'id': subscription.plan_id,
                'name': subscription.plan.name,
            },
            'usage': get_usage(company, subscription.plan),
            'start_date': subscription.start_date.isoformat(),
            'end_date': subscription.end_date.isoformat() if subscription.end_date else None,
            'is_active': subscription.is_active,
            'expired': subscription.expired,
            'days_left': subscription.days_left,
        }

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Editar Suscripción'
        ctx['action'] = 'edit'
        return ctx


class SubscriptionRequiredView(TemplateView):
    template_name = 'subscription/subscription/required.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        ctx['title'] = 'Suscripción requerida'
        ctx['user_has_company'] = bool(getattr(user, 'company_id', None))
        ctx['plans_url'] = reverse_lazy('plan_list')
        ctx['contact_email'] = 'soporte@example.com'
        ctx['plans'] = PlanRepository.list_public_plans()
        return ctx


class SubscriptionLogoutView(View):
    """Vista especial de logout que limpia la memoria del navegador y redirije"""
    
    def get(self, request):
        # Forzar logout completo borrando datos de sesión
        if hasattr(request, 'session'):
            request.session.flush()  # Borra completamente la sesión
        
        # Logout estándar de Django
        logout(request)
        
        # Crear respuesta con JavaScript para forzar limpieza y redirección
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Cerrando sesión...</title>
            <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
            <meta http-equiv="Pragma" content="no-cache">
            <meta http-equiv="Expires" content="0">
        </head>
        <body>
            <div style="text-align:center; padding:50px; font-family:Arial;">
                <h3>Cerrando sesión...</h3>
                <p>Redirigiendo...</p>
            </div>
            <script>
                // Limpiar almacenamiento local y de sesión
                if (typeof(Storage) !== "undefined") {
                    localStorage.clear();
                    sessionStorage.clear();
                }
                
                // Limpiar caché si es posible
                if ('caches' in window) {
                    caches.keys().then(function(names) {
                        names.forEach(function(name) {
                            caches.delete(name);
                        });
                    });
                }
                
                // Redireccionar después de limpiar
                setTimeout(function() {
                    window.location.replace('/login/');
                }, 1000);
                
                // Prevenir que se pueda volver atrás
                history.pushState(null, null, window.location.href);
                window.onpopstate = function () {
                    window.location.replace('/login/');
                };
            </script>
        </body>
        </html>
        """
        
        response = HttpResponse(html_content, content_type='text/html')
        
        # Headers de limpieza de caché
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        response['Clear-Site-Data'] = '"cache", "storage", "executionContexts"'
        response['X-Frame-Options'] = 'DENY'
        
        return response


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
