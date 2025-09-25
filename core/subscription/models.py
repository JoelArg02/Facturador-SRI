from __future__ import annotations

from datetime import timedelta
from typing import Optional, Union, TYPE_CHECKING

from django.conf import settings
from django.db import models
from django.utils import timezone

if TYPE_CHECKING:
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
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='subscriptions', verbose_name='Usuario')
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, verbose_name='Plan')
    start_date = models.DateField(default=timezone.now, verbose_name='Fecha de inicio')
    end_date = models.DateField(null=True, blank=True, verbose_name='Fecha de fin')
    is_active = models.BooleanField(default=True, verbose_name='Activa')
    canceled_at = models.DateTimeField(null=True, blank=True, verbose_name='Cancelada en')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        owner = getattr(self.user, 'get_full_name', lambda: None)()
        owner_display = owner or getattr(self.user, 'username', 'Usuario')
        company = self.company
        if company:
            return f'{company.commercial_name} ({owner_display}) -> {self.plan.name}'
        return f'{owner_display} -> {self.plan.name}'

    def save(self, *args, **kwargs):
        if self.end_date is None and self.plan and self.start_date:
            self.end_date = self.start_date + timedelta(days=self.plan.period_days)
        super().save(*args, **kwargs)

    @property
    def company(self):
        return getattr(self.user, 'company', None)

    @property
    def company_id(self):
        company = self.company
        return company.id if company else None

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
            models.Index(fields=['is_active'], name='subscription_is_active_idx'),
            models.Index(fields=['user', 'is_active'], name='subscriptionuseris_active_idx'),
        ]
        default_permissions = ('add', 'change', 'delete', 'view')
        permissions = (
            ('manage_subscription', 'Puede gestionar suscripciones'),
        )


def _resolve_user(subject: Union['Company', models.Model, None]) -> Optional[models.Model]:
    """Resolve a subscription owner user from either a company or user instance."""
    if subject is None:
        return None

    # Lazy import to avoid circular references
    from django.contrib.auth import get_user_model

    UserModel = get_user_model()
    if isinstance(subject, UserModel):
        return subject

    owner = getattr(subject, 'owner', None)
    if owner and isinstance(owner, UserModel):
        return owner

    # Fallback: if subject has a direct user attribute (e.g. already Subscription.user)
    user = getattr(subject, 'user', None)
    if user and isinstance(user, UserModel):
        return user

    return None


def get_active_subscription(subject: Union['Company', models.Model, None]):
    """Return active (non-expired) subscription for a company or user."""
    user = _resolve_user(subject)
    if user is None:
        return None

    sub = user.subscriptions.filter(is_active=True).order_by('-start_date').first()
    if sub:
        sub.deactivate_if_expired()
        if not sub.is_active:
            return None
    return sub


def check_quota_limits(user, resource_type='product'):
    """
    Verifica si el usuario puede crear más recursos según su plan.
    
    Args:
        user: Usuario a verificar
        resource_type: 'product', 'customer', 'invoice'
        
    Returns:
        dict: {
            'can_create': bool,
            'current_count': int,
            'max_allowed': int,
            'message': str
        }
    """
    print(f"DEBUG check_quota_limits - user: {user}")
    print(f"DEBUG check_quota_limits - user type: {type(user)}")
    print(f"DEBUG check_quota_limits - resource_type: {resource_type}")
    
    result = {
        'can_create': True,
        'current_count': 0,
        'max_allowed': 0,
        'message': ''
    }
    
    # Obtener suscripción activa
    subscription = get_active_subscription(user)
    print(f"DEBUG check_quota_limits - subscription: {subscription}")
    if not subscription:
        result.update({
            'can_create': False,
            'message': 'No tienes una suscripción activa. Contacta al administrador.'
        })
        print(f"DEBUG check_quota_limits - no subscription, returning: {result}")
        return result
    
    # Importaciones lazy para evitar dependencias circulares
    from core.pos.models import Product, Customer, Invoice
    
    # Obtener la compañía del usuario (exactamente como funciona en las vistas)
    print(f"DEBUG check_quota_limits - hasattr(user, 'company'): {hasattr(user, 'company')}")
    company = getattr(user, 'company', None)
    print(f"DEBUG check_quota_limits - company: {company}")
    if not company:
        result.update({
            'can_create': False,
            'message': 'No tienes una compañía asociada. Contacta al administrador.'
        })
        print(f"DEBUG check_quota_limits - no company, returning: {result}")
        return result
    
    # Verificar según el tipo de recurso
    if resource_type == 'product':
        current_count = Product.objects.filter(company=company).count()
        max_allowed = subscription.plan.max_products
        resource_name = 'productos'
    elif resource_type == 'customer':
        current_count = Customer.objects.filter(company=company).count()
        max_allowed = subscription.plan.max_customers
        resource_name = 'clientes'
    elif resource_type == 'invoice':
        current_count = Invoice.objects.filter(company=company).count()
        max_allowed = subscription.plan.max_invoices
        resource_name = 'facturas'
    else:
        result.update({
            'can_create': False,
            'message': 'Tipo de recurso no válido.'
        })
        return result
    
    result.update({
        'current_count': current_count,
        'max_allowed': max_allowed
    })
    
    if current_count >= max_allowed:
        result.update({
            'can_create': False,
            'message': f'Has alcanzado el límite de {resource_name} de tu plan ({max_allowed}). Actualiza tu plan para crear más {resource_name}.'
        })
    else:
        remaining = max_allowed - current_count
        result['message'] = f'Puedes crear {remaining} {resource_name} más en tu plan actual.'
    
    return result
