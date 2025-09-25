from django.shortcuts import redirect
from django.urls import reverse
from django.utils.deprecation import MiddlewareMixin

from core.pos.models import Company
from core.subscription.models import get_active_subscription

class ActiveCompanyMiddleware(MiddlewareMixin):
    def process_request(self, request):
        user = getattr(request, 'user', None)

        if not user or not user.is_authenticated:
            return None

        # 1️⃣ Solo continuar si el usuario TIENE una suscripción activa
        active_subscription = get_active_subscription(user)
        if not active_subscription:
            # Dejar que SubscriptionRequiredMiddleware maneje el caso
            if not hasattr(request, 'company'):
                company = getattr(user, 'company', None)
                if company is None and user.is_staff:
                    company = Company.objects.filter(owner__isnull=True).first() or Company.objects.first()
                request.company = company
            return None

        # 2️⃣ Con suscripción activa, comprobar onboarding
        try:
            onboarding_url = reverse('company_onboarding')
        except Exception:
            onboarding_url = None

        if (
            onboarding_url
            and user.groups.filter(name='Administrador').exists()
            and not getattr(user, 'company_id', None)
        ):
            if (
                request.path != onboarding_url
                and not request.path.startswith('/static')
                and not request.path.startswith('/media')
                and not request.path.startswith('/subscription')
            ):
                return redirect(onboarding_url)

        if not hasattr(request, 'company'):
            company = getattr(user, 'company', None)
            if company is None and user.is_staff:
                company = Company.objects.filter(owner__isnull=True).first() or Company.objects.first()
            request.company = company

        return None
