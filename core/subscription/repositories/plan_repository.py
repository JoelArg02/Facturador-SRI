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
