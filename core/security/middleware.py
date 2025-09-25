from django.shortcuts import redirect
from django.urls import reverse
from django.utils.deprecation import MiddlewareMixin

from core.pos.models import Company


class ActiveCompanyMiddleware(MiddlewareMixin):
    def process_request(self, request):
        user = getattr(request, 'user', None)
        if user and user.is_authenticated:
            # No interferir si estamos en la pantalla de suscripción requerida para evitar loops
            try:
                subscription_required_url = reverse('subscription_required')
            except Exception:
                subscription_required_url = None

            # Prioridad: si el usuario no tiene plan (el otro middleware hará la redirección) no forzamos onboarding aquí
            if subscription_required_url and request.path == subscription_required_url:
                return None

            # Flujo original de onboarding solo si no hay compañías y el usuario no es superuser
            if not Company.objects.exists() and not user.is_superuser:
                onboarding_url = reverse('company_onboarding')
                if request.path not in (onboarding_url,) and not request.path.startswith('/static') and not request.path.startswith('/media'):
                    # Si aún no pasa por subscription_required (ej: primer login), dejamos que subscription middleware actúe primero
                    return redirect(onboarding_url)
            if not hasattr(request, 'company'):
                if user.is_superuser:
                    request.company = None
                else:
                    company = getattr(user, 'company', None)
                    if company is None:
                        if user.is_staff:
                            company = Company.objects.filter(owner__isnull=True).first() or Company.objects.first()
                    request.company = company
        return None
