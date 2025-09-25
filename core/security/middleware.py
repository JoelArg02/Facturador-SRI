from django.shortcuts import redirect
from django.urls import reverse
from django.utils.deprecation import MiddlewareMixin

from core.pos.models import Company


class ActiveCompanyMiddleware(MiddlewareMixin):
    def process_request(self, request):
        user = getattr(request, 'user', None)
        if user and user.is_authenticated:
            # Redirección obligatoria si no hay compañías creadas todavía y el usuario no es superuser
            if not Company.objects.exists() and not user.is_superuser:
                onboarding_url = reverse('company_onboarding')
                # Evitar bucle infinito: no redirigir si ya está en la vista de onboarding o es una petición a static/media
                if request.path != onboarding_url and not request.path.startswith('/static') and not request.path.startswith('/media'):
                    return redirect(onboarding_url)
            if not hasattr(request, 'company'):
                # Super admin (is_superuser) no fuerza una compañía concreta; puede seleccionar luego.
                if user.is_superuser:
                    request.company = None
                else:
                    company = getattr(user, 'company', None)
                    if company is None:
                        if user.is_staff:
                            company = Company.objects.filter(owner__isnull=True).first() or Company.objects.first()
                    request.company = company
        return None
