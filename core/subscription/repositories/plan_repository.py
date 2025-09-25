from core.subscription.models import Plan


class PlanRepository:
    """Repositorio para consultas de planes"""
    
    @staticmethod
    def list_public_plans():
        """Obtiene los planes públicos disponibles (activos)"""
        return Plan.objects.filter(active=True).order_by('price', 'name')
    
    @staticmethod
    def get_plan_by_id(plan_id):
        """Obtiene un plan por su ID"""
        try:
            return Plan.objects.get(id=plan_id, active=True)
        except Plan.DoesNotExist:
            return None
    
    @staticmethod
    def get_cheapest_plan():
        """Obtiene el plan más económico disponible"""
        return Plan.objects.filter(active=True).order_by('price').first()
    
    @staticmethod
    def get_plans_for_update(current_plan_id=None):
        """Obtiene planes disponibles para actualización, excluyendo el actual"""
        queryset = Plan.objects.filter(active=True).order_by('price', 'name')
        if current_plan_id:
            queryset = queryset.exclude(id=current_plan_id)
        return queryset
    
    @staticmethod
    def get_all_plans():
        """Obtiene todos los planes (activos e inactivos) para administración"""
        return Plan.objects.all().order_by('active', 'price', 'name')
    
    @staticmethod
    def get_plans_by_price_range(min_price=None, max_price=None):
        """Obtiene planes dentro de un rango de precios"""
        queryset = Plan.objects.filter(active=True)
        if min_price is not None:
            queryset = queryset.filter(price__gte=min_price)
        if max_price is not None:
            queryset = queryset.filter(price__lte=max_price)
        return queryset.order_by('price', 'name')
