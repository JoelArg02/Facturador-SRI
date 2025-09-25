from django.shortcuts import redirect
from django.urls import reverse
from django.utils.deprecation import MiddlewareMixin

from core.subscription.models import get_active_subscription


class SubscriptionRequiredMiddleware(MiddlewareMixin):

    EXEMPT_PREFIXES = (
        '/static', '/media', '/admin', '/login', '/logout', '/subscription/logout',
        '/pos/company/onboarding',  # ✅ NUEVO: Permitir acceso al onboarding sin suscripción
    )
    EXEMPT_URL_NAMES = {
        'subscription_required', 'subscription_list', 'plan_list', 'subscription_create',
        'subscription_update', 'subscription_delete', 'plan_create', 'plan_update', 'plan_delete',
        'logout', 'subscription_logout', 'company_onboarding'  # ✅ NUEVO: Permitir onboarding
    }

    def process_view(self, request, view_func, view_args, view_kwargs):
        user = getattr(request, 'user', None)
        print(f"=== SubscriptionRequiredMiddleware ===")
        print(f"Usuario: {user}, Path: {request.path}")
        
        if not user or not user.is_authenticated:
            print("Usuario no autenticado. Saltando middleware.")
            return None
        if user.is_superuser:
            print("Usuario es superuser. Saltando middleware.")
            return None

        path = request.path
        
        # Verificar prefijos excluidos
        if any(path.startswith(p) for p in self.EXEMPT_PREFIXES):
            print(f"Path {path} está en prefijos excluidos. Saltando.")
            return None

        # Verificar nombres de URL excluidos
        try:
            match = request.resolver_match
            if match and match.url_name in self.EXEMPT_URL_NAMES:
                print(f"URL name '{match.url_name}' está excluida. Saltando.")
                return None
        except Exception as e:
            print(f"Error verificando resolver_match: {e}")

        # Evitar loop directo
        try:
            subscription_required_url = reverse('subscription_required')
            if path == subscription_required_url:
                print("Ya en subscription_required. Saltando.")
                return None
        except Exception as e:
            print(f"Error obteniendo subscription_required URL: {e}")

        # Verificar suscripción activa
        active_subscription = get_active_subscription(user)
        print(f"Suscripción activa para {user}: {active_subscription}")
        
        if not active_subscription:
            print(f"No hay suscripción activa. Redirigiendo a subscription_required.")
            try:
                return redirect('subscription_required')
            except Exception as e:
                print(f"Error redirigiendo: {e}")
                return None
        else:
            print("Suscripción activa encontrada. Continuando.")
        
        print("=== Fin SubscriptionRequiredMiddleware ===")
        return None
