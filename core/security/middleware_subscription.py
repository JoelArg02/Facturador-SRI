import json
from django.forms import model_to_dict
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.deprecation import MiddlewareMixin

from core.subscription.models import get_active_subscription


class SubscriptionRequiredMiddleware(MiddlewareMixin):

    EXEMPT_PREFIXES = (
        '/static', '/media', '/admin', '/login', '/logout', '/subscription/logout',
        '/pos/company/onboarding',
    )
    EXEMPT_URL_NAMES = {
        'subscription_required', 'subscription_list', 'plan_list', 'subscription_create',
        'subscription_update', 'subscription_delete', 'plan_create', 'plan_update', 'plan_delete',
        'logout', 'subscription_logout', 'company_onboarding'
    }

    def process_view(self, request, view_func, view_args, view_kwargs):
        print(f"[Middleware] Iniciando verificación para path: {request.path}")

        user = getattr(request, 'user', None)

        if not user or not user.is_authenticated:
            print("[Middleware] Usuario no autenticado.")
            return None

        print(f"[Middleware] Usuario autenticado: {user.username}")

        # Verificar grupos
        try:
            all_groups = list(user.groups.values_list('name', flat=True))
            print(f"[Middleware] Grupos del usuario: {all_groups}")
        except Exception as e:
            print(f"[Middleware] Error obteniendo grupos: {e}")
            all_groups = []

        try:
            is_client = user.groups.filter(name='Cliente').exists()
            print(f"[Middleware] ¿Pertenece al grupo 'Cliente'? {is_client}")
        except Exception as e:
            print(f"[Middleware] Error comprobando grupo 'Cliente': {e}")
            is_client = False

        if user.is_superuser:
            print("[Middleware] Usuario es superusuario, se permite el acceso.")
            return None

        # Si es cliente y está en /subscription/required, lo mandamos a /dashboard
        if is_client:
            dashboard_url = reverse('dashboard')  # asegúrate de que el nombre de la URL sea 'dashboard'
            if request.path == reverse('subscription_required'):
                print("[Middleware] Cliente en subscription_required, redirigiendo a /dashboard")
                return redirect(dashboard_url)
            print("[Middleware] Usuario pertenece al grupo 'Cliente', se permite el acceso.")
            return None

        path = request.path
        print(f"[Middleware] Path solicitado: {path}")

        for prefix in self.EXEMPT_PREFIXES:
            if path.startswith(prefix):
                print(f"[Middleware] Path coincide con prefijo exento: {prefix}")
                return None

        try:
            match = request.resolver_match
            if match:
                print(f"[Middleware] URL name: {match.url_name}")
                if match.url_name in self.EXEMPT_URL_NAMES:
                    print("[Middleware] URL exenta por nombre, se permite el acceso.")
                    return None
        except Exception as e:
            print(f"[Middleware] Error al obtener resolver_match: {e}")

        try:
            subscription_required_url = reverse('subscription_required')
            print(f"[Middleware] URL de 'subscription_required': {subscription_required_url}")
            if path == subscription_required_url:
                print("[Middleware] Path es el de 'subscription_required', se permite el acceso.")
                return None
        except Exception as e:
            print(f"[Middleware] Error al resolver 'subscription_required': {e}")

        active_subscription = get_active_subscription(user)
        print(f"[Middleware] Suscripción activa: {bool(active_subscription)}")

        if not active_subscription:
            print("[Middleware] No hay suscripción activa, redirigiendo a 'subscription_required'.")
            try:
                return redirect('subscription_required')
            except Exception as e:
                print(f"[Middleware] Error al redirigir: {e}")
                return None

        print("[Middleware] Suscripción activa encontrada, se permite el acceso.")
        return None
