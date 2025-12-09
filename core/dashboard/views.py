import json
from datetime import datetime, timedelta

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum, FloatField, Count, Q
from django.db.models.functions import Coalesce
from django.http import HttpResponse
from django.views.generic import TemplateView
from django.utils import timezone

from core.pos.models import Product, Invoice, Customer, Provider, Category, Purchase, Company
from core.subscription.models import Subscription, Plan
from core.security.models import Dashboard
from collections import OrderedDict


class DashboardView(LoginRequiredMixin, TemplateView):
    def get_template_names(self):
        # Superadmin ve dashboard especial
        if self.request.user.is_superuser:
            return ['vtc_dashboard_superadmin.html']
        
        dashboard = Dashboard.objects.first()
        if dashboard and dashboard.layout == 1:
            return 'vtc_dashboard_client.html' if self.request.user.is_customer else 'vtc_dashboard_admin.html'
        return 'hzt_dashboard.html'

    def get(self, request, *args, **kwargs):
        request.user.set_group_session()
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST['action']
        try:
            # Determinar la company del usuario logueado
            company = getattr(request, 'company', None) or getattr(getattr(request, 'user', None), 'company', None)
            if action == 'get_top_stock_products':
                data = []
                qs = Product.objects.filter(stock__gt=0)
                if company is not None:
                    qs = qs.filter(company=company)
                for i in qs.order_by('-stock')[0:10]:
                    data.append([i.name, i.stock])
            elif action == 'get_monthly_sales_and_purchases':
                data = []
                year = datetime.now().year
                rows = []
                for month in range(1, 13):
                    inv_qs = Invoice.objects.filter(date_joined__month=month, date_joined__year=year)
                    if company is not None:
                        inv_qs = inv_qs.filter(company=company)
                    result = inv_qs.aggregate(result=Coalesce(Sum('total_amount'), 0.00, output_field=FloatField()))['result']
                    rows.append(float(result))
                data.append({'name': 'Ventas', 'data': rows})
                rows = []
                for month in range(1, 13):
                    pur_qs = Purchase.objects.filter(date_joined__month=month, date_joined__year=year)
                    if company is not None:
                        pur_qs = pur_qs.filter(company=company)
                    result = pur_qs.aggregate(result=Coalesce(Sum('total_amount'), 0.00, output_field=FloatField()))['result']
                    rows.append(float(result))
                data.append({'name': 'Compras', 'data': rows})
            else:
                data['error'] = 'No ha seleccionado ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Panel de administración'
        
        # Dashboard especial para superadmin
        if self.request.user.is_superuser:
            today = timezone.now().date()
            seven_days = today + timedelta(days=7)
            current_year = datetime.now().year
            
            # Estadísticas generales
            context['total_companies'] = Company.objects.count()
            context['active_subscriptions'] = Subscription.objects.filter(is_active=True).count()
            context['expired_subscriptions'] = Subscription.objects.filter(
                Q(is_active=False) | Q(end_date__lt=today)
            ).count()
            context['expiring_soon'] = Subscription.objects.filter(
                is_active=True,
                end_date__gte=today,
                end_date__lte=seven_days
            ).count()
            
            # Estadísticas por plan
            plans = Plan.objects.all()
            plan_stats = []
            total_revenue = 0
            
            for plan in plans:
                active_subs = Subscription.objects.filter(plan=plan, is_active=True)
                active_count = active_subs.count()
                expired_count = Subscription.objects.filter(
                    plan=plan
                ).filter(Q(is_active=False) | Q(end_date__lt=today)).count()
                
                revenue = active_count * float(plan.price)
                total_revenue += revenue
                
                plan_stats.append({
                    'plan_name': plan.name,
                    'plan_price': plan.price,
                    'plan_days': plan.period_days,
                    'active_count': active_count,
                    'expired_count': expired_count,
                    'total_count': active_count + expired_count,
                    'revenue': revenue
                })
            
            context['plan_stats'] = plan_stats
            context['total_revenue'] = total_revenue
            
            # Últimas suscripciones
            context['recent_subscriptions'] = Subscription.objects.select_related(
                'user', 'plan', 'user__company'
            ).order_by('-created_at')[:10]
            
            # Datos para gráficos
            # Suscripciones creadas por mes del año actual
            subscriptions_per_month = []
            for month in range(1, 13):
                count = Subscription.objects.filter(
                    created_at__year=current_year,
                    created_at__month=month
                ).count()
                subscriptions_per_month.append(count)
            context['companies_per_month'] = json.dumps(subscriptions_per_month)
            context['current_year'] = current_year
            
            # Distribución de planes (para gráfico pie)
            plan_distribution = []
            for plan in plans:
                count = Subscription.objects.filter(plan=plan, is_active=True).count()
                if count > 0:
                    plan_distribution.append({
                        'name': plan.name,
                        'y': count
                    })
            context['plan_distribution'] = json.dumps(plan_distribution)
            
            return context
        
        # Dashboard normal para otros usuarios
        if not self.request.user.is_customer:
            company = getattr(self.request, 'company', None) or getattr(getattr(self.request, 'user', None), 'company', None)
            cust_qs = Customer.objects.all()
            prov_qs = Provider.objects.all()
            cat_qs = Category.objects.all()
            prod_qs = Product.objects.all()
            inv_qs = Invoice.objects.all()
            if company is not None:
                cust_qs = cust_qs.filter(company=company)
                prov_qs = prov_qs.filter(company=company)
                cat_qs = cat_qs.filter(company=company)
                prod_qs = prod_qs.filter(company=company)
                inv_qs = inv_qs.filter(company=company)
            context['customers'] = cust_qs.count()
            context['providers'] = prov_qs.count()
            context['categories'] = cat_qs.count()
            context['products'] = prod_qs.count()
            context['invoices'] = inv_qs.order_by('-id')[0:10]
        else:
            invoices = Invoice.objects.filter(customer__user=self.request.user).select_related('company', 'receipt').order_by('-date_joined', '-id')
            grouped_invoices = OrderedDict()
            for invoice in invoices:
                grouped_invoices.setdefault(invoice.company, []).append(invoice)
            context['customer_invoice_groups'] = [
                {
                    'company': company,
                    'invoices': invoice_list
                }
                for company, invoice_list in grouped_invoices.items()
            ]

            customer_company = getattr(getattr(self.request.user, 'customer', None), 'company', None)
            if customer_company:
                context['company'] = customer_company
            elif invoices:
                context['company'] = invoices[0].company
        return context