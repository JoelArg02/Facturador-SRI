from django.shortcuts import redirect
from django.urls import reverse
from django.utils.deprecation import MiddlewareMixin

from core.subscription.models import get_active_subscription


class SubscriptionRequiredMiddleware(MiddlewareMixin):
    """Redirige a una página si el usuario autenticado (no superuser) no tiene suscripción activa.

    Evita loops y no intercepta:
    - Rutas de autenticación /login/ /logout/
    - Rutas de planes / suscripciones ya que ahí puede contratar
    - Página de aviso propia
    - Recursos estáticos / media / admin
    """

    EXEMPT_PREFIXES = (
        '/static', '/media', '/admin', '/login', '/logout', '/subscription/logout',
    )
    EXEMPT_URL_NAMES = {
        'subscription_required', 'subscription_list', 'plan_list', 'subscription_create',
        'subscription_update', 'subscription_delete', 'plan_create', 'plan_update', 'plan_delete',
        'logout', 'subscription_logout'
    }

    def process_view(self, request, view_func, view_args, view_kwargs):
        user = getattr(request, 'user', None)
        if not user or not user.is_authenticated:
            return None
        if user.is_superuser:
            return None

        path = request.path
        if any(path.startswith(p) for p in self.EXEMPT_PREFIXES):
            return None

        # Resolver nombre de la vista para exclusiones
        try:
            match = request.resolver_match
            if match and match.url_name in self.EXEMPT_URL_NAMES:
                return None
        except Exception:
            pass

        # Evitar loop directo
        try:
            if path == reverse('subscription_required'):
                return None
        except Exception:
            pass

        # Si no hay suscripción activa -> redirigir
        if not get_active_subscription(user):
            try:
                return redirect('subscription_required')
            except Exception:
                return None
        return None
