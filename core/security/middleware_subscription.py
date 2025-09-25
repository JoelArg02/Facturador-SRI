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
        user = getattr(request, 'user', None)
        if user and user.is_authenticated:
            try:
                user_dict = model_to_dict(user, fields=[f.name for f in user._meta.fields])
                user_dict['groups'] = list(user.groups.values_list('name', flat=True))
                print("Usuario completo:", json.dumps(user_dict, indent=4, default=str))
                print(f"Usuario: {user.username}, Path: {request.path}")
            except Exception as e:
                print("Error imprimiendo usuario:", e)
        else:
            print("Usuario no autenticado o no existe.")

        if not user or not user.is_authenticated:
            return None
        if user.is_superuser:
            return None

        path = request.path

        # Verificar prefijos exentos
        for prefix in self.EXEMPT_PREFIXES:
            if path.startswith(prefix):
                return None

        try:
            match = request.resolver_match
            if match and match.url_name in self.EXEMPT_URL_NAMES:
                return None
        except Exception:
            pass

        try:
            subscription_required_url = reverse('subscription_required')
            if path == subscription_required_url:
                return None
        except Exception:
            pass

        active_subscription = get_active_subscription(user)

        if not active_subscription:
            try:
                return redirect('subscription_required')
            except Exception:
                return None

        return None
