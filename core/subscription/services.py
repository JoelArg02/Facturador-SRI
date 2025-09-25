from django.apps import apps

from .models import get_active_subscription


class QuotaExceeded(Exception):
    pass


def count_for(company, model_label: str):
    """Generic counter for a model referenced by app_label.ModelName and filtered by company FK if exists."""
    app_label, model_name = model_label.split('.')
    Model = apps.get_model(app_label, model_name)
    if not hasattr(Model, 'company'):
        # Fallback: try infer via parent relation with company
        # This keeps placeholder behavior; refine in later iterations.
        return Model.objects.none().count()
    return Model.objects.filter(company=company).count()


def ensure_quota(company, kind: str):
    """Ensure company can create a resource of type 'kind' (invoice|customer|product)."""
    subscription = get_active_subscription(company)
    if subscription is None:
        raise QuotaExceeded('No hay una suscripción activa para la compañía.')
    plan = subscription.plan
    limits = {
        'invoice': plan.max_invoices,
        'customer': plan.max_customers,
        'product': plan.max_products,
    }
    model_map = {
        'invoice': 'pos.Invoice',
        'customer': 'pos.Customer',  # Se añadirá FK company en iteraciones siguientes
        'product': 'pos.Product',    # Se añadirá FK company en iteraciones siguientes
    }
    if kind not in limits:
        return True
    limit = limits[kind]
    if limit is None or limit == 0:
        return True
    model_label = f'core.{model_map[kind]}' if not model_map[kind].startswith('core.') else model_map[kind]
    current = count_for(company, model_label)
    if current >= limit:
        raise QuotaExceeded(f'Límite alcanzado para {kind}. ({current}/{limit})')
    return True
