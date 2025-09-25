import json
from io import BytesIO

import pandas as pd
import xlsxwriter
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView, DeleteView, ListView
from django.views.generic.base import View

from core.pos.forms import ProductForm, Product, Category
from core.security.mixins import GroupPermissionMixin, CompanyQuerysetMixin, AutoAssignCompanyMixin
from core.subscription.models import check_quota_limits


class ProductListView(GroupPermissionMixin, CompanyQuerysetMixin, ListView):
    model = Product
    template_name = 'product/list.html'
    permission_required = 'view_product'

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST['action']
        try:
            if action == 'search':
                data = []
                for i in self.get_queryset():
                    data.append(i.as_dict())
            elif action == 'upload_excel':
                with transaction.atomic():
                    archive = request.FILES['archive']
                    df = pd.read_excel(archive, engine='openpyxl', dtype={'Código': str})
                    for record in json.loads(df.to_json(orient='records')):
                        if record['Nombre'] not in ['SUMINISTROS', 'SPRAY LIMPIADOR DE MARIPOSA/12.5- OZ', 'SPRAY LIMPIADOR DE FRENOS', 'LITRO DE ACEITE MOTOR ENI I-SIGMA TOP 10W-40', 'FILTRO A/C POER', 'FILTRO AIRE POER DIESEL', 'FILTRO DE COMBUSTIBLE POER ESP 4D20M', 'FILTRO ACEITE POER 4D20M', 'LAVADO EXPRESS', 'CHEQUEO DE 20000KM + 25 PUNTOS DE INSPECCION', 'ALINEACION Y BALANCEO']:
                            continue
                        product, created = self.model.objects.update_or_create(
                            code=str(record['Código']),
                            defaults={
                                'name': record['Nombre'],
                                'category': Category.objects.get_or_create(name=record['Categoría'])[0],
                                'price': float(record['Precio de Compra']),
                                'pvp': float(record['Precio de Venta']),
                                'stock': int(record['Stock']),
                                'is_inventoried': record['¿Es inventariado?'],
                                'has_tax': record['¿Se cobra impuesto?']
                            }
                        )
                        print(f'{product.id} => {created}')
            else:
                data['error'] = 'No ha seleccionado ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Listado de {self.model._meta.verbose_name_plural}'
        context['create_url'] = reverse_lazy('product_create')
        return context


class ProductCreateView(AutoAssignCompanyMixin, GroupPermissionMixin, CompanyQuerysetMixin, CreateView):
    model = Product
    template_name = 'product/create.html'
    form_class = ProductForm
    success_url = reverse_lazy('product_list')
    permission_required = 'add_product'

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST['action']
        try:
            if action == 'add':
                quota_check = check_quota_limits(request.user, 'product')
                if not quota_check['can_create']:
                    data['error'] = quota_check['message']
                else:
                    form = self.get_form()
                    if not form.is_valid():
                        data['error'] = form.errors
                    else:
                        # Encapsulamos en transacción para consistencia
                        from django.db import transaction
                        try:
                            with transaction.atomic():
                                # form.save ahora devuelve instancia o lanza ValueError si no es válido
                                product = form.save(commit=False)

                                # company debe venir del form (obligatorio) o del request
                                company_obj = form.cleaned_data.get('company') or getattr(request, 'company', None)
                                if not company_obj:
                                    data['error'] = 'Debe seleccionar la compañía.'
                                else:
                                    product.company = company_obj
                                    product.save()
                                    data = product.as_dict()
                        except Exception as ex:
                            data['error'] = f'Error al guardar el producto: {ex}'
            elif action == 'validate_data':
                field = request.POST['field']
                filters = Q()
                if field == 'code':
                    filters &= Q(code__iexact=request.POST['code'])
                data['valid'] = not self.model.objects.filter(filters).exists() if filters.children else True
            elif action == 'check_quota':
                quota_check = check_quota_limits(request.user, 'product')
                data = quota_check
            else:
                data['error'] = 'No ha seleccionado ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context['title'] = f'Creación de un {self.model._meta.verbose_name}'
        context['list_url'] = self.success_url
        context['action'] = 'add'
        
        quota_check = check_quota_limits(self.request.user, 'product')
        context['quota_info'] = quota_check
        
        return context


class ProductUpdateView(AutoAssignCompanyMixin, GroupPermissionMixin, CompanyQuerysetMixin, UpdateView):
    model = Product
    template_name = 'product/create.html'
    form_class = ProductForm
    success_url = reverse_lazy('product_list')
    permission_required = 'change_product'

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST['action']
        try:
            if action == 'edit':
                data = self.get_form().save()
            elif action == 'validate_data':
                field = request.POST['field']
                filters = Q()
                if field == 'code':
                    filters &= Q(code__iexact=request.POST['code'])
                data['valid'] = not self.model.objects.filter(filters).exclude(id=self.object.id).exists() if filters.children else True
            else:
                data['error'] = 'No ha seleccionado ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context['title'] = f'Edición de un {self.model._meta.verbose_name}'
        context['list_url'] = self.success_url
        context['action'] = 'edit'
        return context


class ProductDeleteView(GroupPermissionMixin, CompanyQuerysetMixin, DeleteView):
    model = Product
    template_name = 'delete.html'
    success_url = reverse_lazy('product_list')
    permission_required = 'delete_product'

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


class ProductStockAdjustmentView(GroupPermissionMixin, CompanyQuerysetMixin, ListView):
    model = Product
    template_name = 'product/stock_adjustment.html'
    permission_required = 'adjust_product_stock'

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST['action']
        try:
            if action == 'search_product':
                data = []
                ids = json.loads(request.POST['ids'])
                term = request.POST['term']
                filters = Q(is_inventoried=True)
                if len(term):
                    filters &= Q(Q(name__icontains=term) | Q(code__icontains=term))
                base_qs = self.get_queryset()
                queryset = base_qs.filter(filters).exclude(id__in=ids).order_by('name')
                if filters.children and len(term):
                    queryset = queryset[0:10]
                for i in queryset:
                    item = i.as_dict()
                    item['quantity'] = i.stock
                    data.append(item)
            elif action == 'create':
                with transaction.atomic():
                    for i in json.loads(request.POST['products']):
                        product = self.model.objects.get(pk=i['id'])
                        product.stock = int(i['quantity'])
                        product.save()
            else:
                data['error'] = 'No ha seleccionado ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'juste de Stock de {self.model._meta.verbose_name_plural}'
        return context


class ProductExportExcelView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        try:
            columns_info = [
                ('Código', 20, lambda c: c.code),
                ('Nombre', 50, lambda c: c.name),
                ('Categoría', 35, lambda c: c.category.name),
                ('Precio de Compra', 30, lambda c: f'{c.price:.4f}'),
                ('Precio de Venta', 30, lambda c: f'{c.pvp:.4f}'),
                ('Stock', 30, lambda c: f'{c.stock}'),
                ('¿Es inventariado?', 30, lambda c: c.is_inventoried),
                ('¿Se cobra impuesto?', 30, lambda c: c.has_tax),
            ]
            output = BytesIO()
            workbook = xlsxwriter.Workbook(output)
            worksheet = workbook.add_worksheet('Productos')
            cell_format = workbook.add_format({'bold': True, 'align': 'center', 'border': 1})
            row_format = workbook.add_format({'align': 'center', 'border': 1})
            for index, (name, width, _) in enumerate(columns_info):
                worksheet.set_column(index, index, width)
                worksheet.write(0, index, name, cell_format)
            for row, product in enumerate(self.get_queryset(), start=1):
                for col, (_, _, value_func) in enumerate(columns_info):
                    worksheet.write(row, col, value_func(product), row_format)
            workbook.close()
            output.seek(0)
            filename = 'PRODUCTOS.xlsx'
            response = HttpResponse(output, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = f'attachment; filename={filename}'
            return response
        except Exception as e:
            messages.error(request, str(e))
        return HttpResponseRedirect(reverse_lazy('product_list'))
