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
            except Exception as e:
                print("[ActiveCompanyMiddleware] Error imprimiendo usuario:", e)
        else:
            print("[ActiveCompanyMiddleware] Usuario no autenticado o no existe.")

        if not user or not user.is_authenticated:
            return None

        # Rutas que no requieren verificación de empresa
        excluded_paths = ['/static', '/media', '/subscription', '/login', '/logout']
        if any(request.path.startswith(path) for path in excluded_paths):
            return None

        active_subscription = get_active_subscription(user)
        
        # Si no hay suscripción activa, asignar empresa disponible y continuar
        if not active_subscription:
            if not hasattr(request, 'company'):
                company = getattr(user, 'company', None)
                if company is None and user.is_staff:
                    company = Company.objects.filter(owner__isnull=True).first() or Company.objects.first()
                request.company = company
            return None

        # Si hay suscripción activa, verificar el onboarding
        try:
            onboarding_url = reverse('company_onboarding')
        except Exception:
            onboarding_url = None

        # Verificar si el usuario necesita completar el onboarding
        user_company = getattr(user, 'company', None)
        needs_onboarding = (
            onboarding_url
            and user.groups.filter(name='Administrador').exists()
            and not user_company
        )

        # Si necesita onboarding y no está ya en la página de onboarding
        if needs_onboarding and request.path != onboarding_url:
            return redirect(onboarding_url)

        # Asignar empresa al request
        if not hasattr(request, 'company'):
            company = user_company
            if company is None and user.is_staff:
                company = Company.objects.filter(owner__isnull=True).first() or Company.objects.first()
            request.company = company

        return None
