from django.core.management.base import BaseCommand

from core.subscription.models import Plan


DEFAULT_PLANS = [
    {
        'name': 'Starter',
        'description': 'Plan básico para iniciar la facturación',
        'max_invoices': 100,
        'max_customers': 100,
        'max_products': 200,
        'price': 0,
        'period_days': 30,
    },
    {
        'name': 'Pro',
        'description': 'Plan profesional para pymes',
        'max_invoices': 1000,
        'max_customers': 3000,
        'max_products': 5000,
        'price': 29.90,
        'period_days': 30,
    },
    {
        'name': 'Enterprise',
        'description': 'Grandes volúmenes y soporte avanzado',
        'max_invoices': 100000,
        'max_customers': 200000,
        'max_products': 500000,
        'price': 199.00,
        'period_days': 30,
    },
]


class Command(BaseCommand):
    help = 'Crea planes por defecto si no existen'

    def handle(self, *args, **options):
        created = 0
        for data in DEFAULT_PLANS:
            obj, was_created = Plan.objects.get_or_create(name=data['name'], defaults=data)
            if was_created:
                created += 1
        self.stdout.write(self.style.SUCCESS(f'Planes creados: {created}'))
