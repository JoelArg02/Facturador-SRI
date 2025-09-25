from django.utils.deprecation import MiddlewareMixin

from core.pos.models import Company


class ActiveCompanyMiddleware(MiddlewareMixin):
    """
    Determina la compañía activa para el usuario autenticado.
    Ahora: relación uno a uno (user.company). Si el usuario es superuser (super admin) puede ver todas.
    """
    def process_request(self, request):
        user = getattr(request, 'user', None)
        if user and user.is_authenticated:
            if not hasattr(request, 'company'):
                # Super admin (is_superuser) no fuerza una compañía concreta; puede seleccionar luego.
                if user.is_superuser:
                    request.company = None
                else:
                    company = getattr(user, 'company', None)
                    if company is None:
                        # fallback: primera compañía libre sólo si staff (evitar acceso indebido)
                        if user.is_staff:
                            company = Company.objects.filter(owner__isnull=True).first() or Company.objects.first()
                    request.company = company
        return None
