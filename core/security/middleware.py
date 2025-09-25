import json
from django.forms import model_to_dict
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.deprecation import MiddlewareMixin

from core.pos.models import Company
from core.subscription.models import get_active_subscription

class ActiveCompanyMiddleware(MiddlewareMixin):
    def process_request(self, request):
        user = getattr(request, 'user', None)
        if user and user.is_authenticated:
            try:
                user_dict = model_to_dict(user, fields=[f.name for f in user._meta.fields])
                user_dict['groups'] = list(user.groups.values_list('name', flat=True))
            except Exception:
                pass
        else:
            pass

        if not user or not user.is_authenticated:
            return None

        excluded_paths = ['/static', '/media', '/subscription', '/login', '/logout']
        if any(request.path.startswith(path) for path in excluded_paths):
            return None

        active_subscription = get_active_subscription(user)

        if not active_subscription:
            if not hasattr(request, 'company'):
                company = getattr(user, 'company', None)
                if company is None and user.is_staff:
                    company = Company.objects.filter(owner__isnull=True).first() or Company.objects.first()
                request.company = company
            return None

        try:
            onboarding_url = reverse('company_onboarding')
        except Exception:
            onboarding_url = None

        user_company = getattr(user, 'company', None)
        needs_onboarding = (
            onboarding_url
            and user.groups.filter(name='Administrador').exists()
            and not user_company
        )

        if needs_onboarding and request.path != onboarding_url:
            return redirect(onboarding_url)

        if not hasattr(request, 'company'):
            company = user_company
            if company is None and user.is_staff:
                company = Company.objects.filter(owner__isnull=True).first() or Company.objects.first()
            request.company = company

        return None
