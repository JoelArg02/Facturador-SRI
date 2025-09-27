import json

from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView

from core.pos.forms import PurchaseForm, Purchase, PurchaseDetail, Product, Provider, AccountPayable, PAYMENT_TYPE
from core.pos.models import Company
from core.report.forms import ReportForm
from core.security.mixins import GroupPermissionMixin, AutoAssignCompanyMixin, CompanyQuerysetMixin


class PurchaseListView(GroupPermissionMixin, CompanyQuerysetMixin, ListView):
    model = Purchase
    template_name = 'purchase/list.html'
    permission_required = 'view_purchase'

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST['action']
        try:
            if action == 'search':
                data = []
                start_date = request.POST['start_date']
                end_date = request.POST['end_date']
                filters = Q()
                if len(start_date) and len(end_date):
                    filters &= Q(date_joined__range=[start_date, end_date])
                queryset = self.get_queryset().filter(filters)
                for i in queryset:
                    data.append(i.as_dict())
            elif action == 'search_detail_products':
                data = []
                for i in PurchaseDetail.objects.filter(purchase_id=request.POST['id']):
                    data.append(i.as_dict())
            else:
                data['error'] = 'No ha seleccionado ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Listado de {self.model._meta.verbose_name_plural}'
        context['create_url'] = reverse_lazy('purchase_create')
        context['form'] = ReportForm()
        return context


class PurchaseCreateView(AutoAssignCompanyMixin, GroupPermissionMixin, CompanyQuerysetMixin, CreateView):
    model = Purchase
    template_name = 'purchase/create.html'
    form_class = PurchaseForm
    success_url = reverse_lazy('purchase_list')
    permission_required = 'add_purchase'

    def post(self, request, *args, **kwargs):
        action = request.POST['action']
        data = {}
        try:
            if action == 'add':
                with transaction.atomic():
                    # Determinar compañía actual desde request (middleware o usuario)
                    current_company = getattr(request, 'company', None) or getattr(getattr(request, 'user', None), 'company', None)
                    if current_company is None:
                        raise Exception('No se pudo determinar la compañía actual para la compra.')
                    # Validar proveedor pertenece a la compañía
                    provider_id = int(request.POST['provider'])
                    provider = Provider.objects.filter(id=provider_id, company=current_company).first()
                    if provider is None:
                        raise Exception('El proveedor seleccionado no pertenece a su compañía.')
                    purchase = Purchase.objects.create(
                        company=current_company,
                        number=request.POST['number'],
                        date_joined=request.POST['date_joined'],
                        provider=provider,
                        payment_type=request.POST['payment_type'],
                        tax=float(current_company.tax) / 100,
                    )
                    for i in json.loads(request.POST['products']):
                        # Validar producto pertenece a la compañía
                        product = Product.objects.filter(pk=i['id'], company=current_company).first()
                        if product is None:
                            raise Exception('Uno de los productos no pertenece a su compañía.')
                        detail = PurchaseDetail.objects.create(
                            company=current_company,
                            purchase_id=purchase.id,
                            product_id=product.id,
                            quantity=int(i['quantity']),
                            price=float(i['price'])
                        )
                        detail.product.stock += detail.quantity
                        detail.product.save()

                    purchase.recalculate_invoice()

                    if purchase.payment_type == PAYMENT_TYPE[1][0]:
                        purchase.end_credit = request.POST['end_credit']
                        purchase.save()
                        AccountPayable.objects.create(purchase_id=purchase.id, date_joined=purchase.date_joined, end_date=purchase.end_credit, debt=purchase.subtotal)
            elif action == 'search_product':
                data = []
                product_id = json.loads(request.POST['product_id'])
                term = request.POST['term']
                filters = Q(is_inventoried=True)
                if len(term):
                    filters &= Q(Q(name__icontains=term) | Q(code__icontains=term))
                # Filtrar por compañía actual
                current_company = getattr(request, 'company', None) or getattr(getattr(request, 'user', None), 'company', None)
                queryset = Product.objects.filter(filters)
                if current_company is not None:
                    queryset = queryset.filter(company=current_company)
                queryset = queryset.exclude(id__in=product_id).order_by('name')
                if filters.children and len(term):
                    queryset = queryset[0:10]
                for i in queryset:
                    data.append(i.as_dict())
            elif action == 'search_provider':
                data = []
                term = request.POST['term']
                current_company = getattr(request, 'company', None) or getattr(getattr(request, 'user', None), 'company', None)
                qs = Provider.objects.all()
                if current_company is not None:
                    qs = qs.filter(company=current_company)
                if term:
                    qs = qs.filter(name__icontains=term)
                for i in qs.order_by('name')[0:10]:
                    data.append(i.as_dict())
            elif action == 'validate_data':
                data['valid'] = not self.get_queryset().filter(number=request.POST['number']).exists()
            else:
                data['error'] = 'No ha seleccionado ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context['title'] = f'Creación de una {self.model._meta.verbose_name}'
        context['list_url'] = self.success_url
        context['action'] = 'add'
        return context


class PurchaseDeleteView(GroupPermissionMixin, CompanyQuerysetMixin, DeleteView):
    model = Purchase
    template_name = 'delete.html'
    success_url = reverse_lazy('purchase_list')
    permission_required = 'delete_purchase'

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            self.get_object().delete()
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Eliminación de un {self.model._meta.verbose_name}'
        context['list_url'] = self.success_url
        return context
