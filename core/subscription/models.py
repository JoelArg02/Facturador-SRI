from datetime import timedelta

from django.db import models
from django.utils import timezone

from core.pos.models import Company


class Plan(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name='Nombre')
    description = models.TextField(null=True, blank=True, verbose_name='Descripción')
    max_invoices = models.PositiveIntegerField(default=100, verbose_name='Máx. Facturas')
    max_customers = models.PositiveIntegerField(default=100, verbose_name='Máx. Clientes')
    max_products = models.PositiveIntegerField(default=200, verbose_name='Máx. Productos')
    price = models.DecimalField(max_digits=9, decimal_places=2, default=0, verbose_name='Precio')
    period_days = models.PositiveIntegerField(default=30, verbose_name='Duración (días)')
    active = models.BooleanField(default=True, verbose_name='Activo')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Plan'
        verbose_name_plural = 'Planes'
        default_permissions = ('add', 'change', 'delete', 'view')
        permissions = (
            ('manage_plan', 'Puede gestionar planes'),
        )


class Subscription(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='subscriptions', verbose_name='Compañía')
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, verbose_name='Plan')
    start_date = models.DateField(default=timezone.now, verbose_name='Fecha de inicio')
    end_date = models.DateField(null=True, blank=True, verbose_name='Fecha de fin')
    is_active = models.BooleanField(default=True, verbose_name='Activa')
    canceled_at = models.DateTimeField(null=True, blank=True, verbose_name='Cancelada en')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.company.commercial_name} -> {self.plan.name}'

    def save(self, *args, **kwargs):
        if self.end_date is None and self.plan and self.start_date:
            self.end_date = self.start_date + timedelta(days=self.plan.period_days)
        super().save(*args, **kwargs)

    @property
    def days_left(self):
        if self.end_date:
            return (self.end_date - timezone.now().date()).days
        return None

    @property
    def expired(self):
        return self.end_date is not None and self.end_date < timezone.now().date()

    def deactivate_if_expired(self):
        if self.is_active and self.expired:
            self.is_active = False
            self.save(update_fields=['is_active'])

    class Meta:
        verbose_name = 'Suscripción'
        verbose_name_plural = 'Suscripciones'
        indexes = [
            models.Index(fields=['is_active']),
        ]
        default_permissions = ('add', 'change', 'delete', 'view')
        permissions = (
            ('manage_subscription', 'Puede gestionar suscripciones'),
        )


def get_active_subscription(company: Company):
    """Return active (non-expired) subscription for a company."""
    sub = company.subscriptions.filter(is_active=True).order_by('-start_date').first()
    if sub:
        sub.deactivate_if_expired()
        if not sub.is_active:
            return None
    return sub
