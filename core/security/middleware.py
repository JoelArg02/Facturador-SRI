from django.utils.deprecation import MiddlewareMixin

from core.pos.models import Company


class ActiveCompanyMiddleware(MiddlewareMixin):
    """
    Determina la compañía activa para el usuario autenticado.
    Estrategia inicial: si el usuario tiene companies -> la primera.
    Futuro: permitir selección vía sesión o parámetro.
    """
    def process_request(self, request):
        user = getattr(request, 'user', None)
        if user and user.is_authenticated:
            if not hasattr(request, 'company'):
                company = user.companies.first()
                if company is None:
                    # fallback: si existe Company sin owner y el user es staff, podría adoptarla
                    company = Company.objects.first()
                request.company = company
        return None
