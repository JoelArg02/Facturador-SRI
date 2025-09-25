from django.core.management.base import BaseCommand
from django.db import transaction

from core.pos.models import (
    Company, Provider, Category, Product, Purchase, PurchaseDetail,
    AccountPayable, AccountPayablePayment, Customer, Receipt, ExpenseType,
    Expense, Promotion, PromotionDetail, AccountReceivable,
    AccountReceivablePayment
)


TARGET_MODELS = [
    Provider, Category, Product, Purchase, PurchaseDetail, AccountPayable,
    AccountPayablePayment, Customer, Receipt, ExpenseType, Expense,
    Promotion, PromotionDetail, AccountReceivable, AccountReceivablePayment
]


class Command(BaseCommand):
    help = 'Asigna la compañía existente a los registros que ahora requieren FK company (iteración multi-tenant).'

    def add_arguments(self, parser):
        parser.add_argument('--company-id', type=int, help='ID de la compañía a usar (por defecto la primera).')
        parser.add_argument('--dry-run', action='store_true', help='Solo muestra lo que haría sin guardar cambios.')

    def handle(self, *args, **options):
        company_id = options.get('company_id')
        dry_run = options.get('dry_run')
        company = Company.objects.filter(id=company_id).first() if company_id else Company.objects.first()
        if not company:
            self.stderr.write(self.style.ERROR('No existe una Company para asignar.'))
            return
        self.stdout.write(self.style.WARNING(f'Usando Company id={company.id} ({company.commercial_name})'))
        total = 0
        with transaction.atomic():
            for Model in TARGET_MODELS:
                if 'company' not in [f.name for f in Model._meta.get_fields()]:
                    continue
                qs = Model.objects.filter(company__isnull=True)
                updated = qs.update(company=company)
                total += updated
                self.stdout.write(f'{Model.__name__}: {updated} registros actualizados')
            if dry_run:
                self.stdout.write(self.style.WARNING('Dry-run activado: se revierte la transacción.'))
                transaction.set_rollback(True)
        self.stdout.write(self.style.SUCCESS(f'Total registros afectados: {total}'))
