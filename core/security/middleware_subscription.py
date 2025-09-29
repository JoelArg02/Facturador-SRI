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

        if not user or not user.is_authenticated:
            return None

        try:
            is_client = user.groups.filter(name='Cliente').exists()
        except Exception:
            is_client = False

        if user.is_superuser:
            return None

        if is_client:
            dashboard_url = reverse('dashboard')
            if request.path == reverse('subscription_required'):
                return redirect(dashboard_url)
            return None

        path = request.path

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
