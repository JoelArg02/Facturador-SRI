from django.contrib import admin

from .models import Plan, Subscription


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'max_invoices', 'max_customers', 'max_products', 'period_days', 'active')
    search_fields = ('name',)
    list_filter = ('active',)


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'company_name', 'plan', 'start_date', 'end_date', 'is_active')
    list_filter = ('is_active', 'plan')
    search_fields = ('user__username', 'user__names', 'plan__name', 'user__company__commercial_name')

    @admin.display(description='Compañía', ordering='user__company__commercial_name')
    def company_name(self, obj):
        company = obj.company
        return company.commercial_name if company else '—'
