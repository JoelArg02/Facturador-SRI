import json
from datetime import datetime

from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView, DeleteView, ListView

from core.pos.forms import Promotion, PromotionForm, Product, PromotionDetail
from core.report.forms import ReportForm
from core.security.mixins import GroupPermissionMixin, AutoAssignCompanyMixin, CompanyQuerysetMixin


class PromotionListView(GroupPermissionMixin, CompanyQuerysetMixin, ListView):
    model = Promotion
    template_name = 'promotion/list.html'
    form_class = ReportForm
    permission_required = 'view_promotion'

    def get(self, request, *args, **kwargs):
        promotion = self.model.objects.filter(end_date__lte=datetime.now().date(), active=True)
        if promotion.exists():
            promotion.update(active=False)
        return super(PromotionListView, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST['action']
        try:
            if action == 'search':
                data = []
                start_date = request.POST['start_date']
                end_date = request.POST['start_date']
                filters = Q()
                if len(start_date) and len(end_date):
                    filters &= Q(start_date__range=[start_date, end_date])
                for i in self.model.objects.filter(filters):
                    data.append(i.as_dict())
            elif action == 'search_detail_products':
                data = []
                for i in PromotionDetail.objects.filter(promotion_id=request.POST['id']):
                    data.append(i.as_dict())
            else:
                data['error'] = 'No ha seleccionado ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Listado de {self.model._meta.verbose_name_plural}'
        context['create_url'] = reverse_lazy('promotion_create')
        context['form'] = ReportForm()
        return context


class PromotionCreateView(AutoAssignCompanyMixin, GroupPermissionMixin, CompanyQuerysetMixin, CreateView):
    model = Promotion
    template_name = 'promotion/create.html'
    form_class = PromotionForm
    success_url = reverse_lazy('promotion_list')
    permission_required = 'add_promotion'

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST['action']
        try:
            if action == 'add':
                with transaction.atomic():
                    promotion = Promotion.objects.create(
                        start_date=datetime.strptime(request.POST['start_date'], '%Y-%m-%d').date(),
                        end_date=datetime.strptime(request.POST['end_date'], '%Y-%m-%d').date()
                    )
                    for i in json.loads(request.POST['products']):
                        product = Product.objects.get(pk=i['id'])
                        PromotionDetail.objects.create(promotion_id=promotion.id, product_id=product.id, discount=float(i['discount']) / 100, current_price=float(product.pvp))
            elif action == 'search_product':
                data = []
                product_id = json.loads(request.POST['product_id'])
                term = request.POST['term']
                product_id = product_id + list(PromotionDetail.objects.filter(promotion__active=True).values_list('product_id', flat=True))
                filters = Q()
                if len(term):
                    filters &= Q(Q(name__icontains=term) | Q(code__icontains=term))
                queryset = Product.objects.filter(filters).exclude(id__in=product_id).order_by('name')
                if filters.children and len(term):
                    queryset = queryset[0:10]
                for i in queryset:
                    item = i.as_dict()
                    item['selected'] = False
                    data.append(item)
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
        context['products'] = []
        return context


class PromotionUpdateView(AutoAssignCompanyMixin, GroupPermissionMixin, CompanyQuerysetMixin, UpdateView):
    model = Promotion
    template_name = 'promotion/create.html'
    form_class = PromotionForm
    success_url = reverse_lazy('promotion_list')
    permission_required = 'change_promotion'

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().dispatch(request, *args, **kwargs)

    def get_form(self, form_class=None):
        instance = self.object
        date_range = f"{instance.start_date.strftime('%Y-%m-%d')} - {instance.end_date.strftime('%Y-%m-%d')}"
        form = PromotionForm(instance=instance, initial={
            'date_range': date_range
        })
        form.fields['date_range'].initial = date_range
        return form

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST['action']
        try:
            if action == 'edit':
                with transaction.atomic():
                    promotion = self.object
                    promotion.start_date = datetime.strptime(request.POST['start_date'], '%Y-%m-%d').date()
                    promotion.end_date = datetime.strptime(request.POST['end_date'], '%Y-%m-%d').date()
                    promotion.save()
                    promotion.promotiondetail_set.all().delete()
                    for i in json.loads(request.POST['products']):
                        product = Product.objects.get(pk=i['id'])
                        PromotionDetail.objects.create(promotion_id=promotion.id, product_id=product.id, discount=float(i['discount']) / 100, current_price=float(product.pvp))
            elif action == 'search_product':
                data = []
                product_id = json.loads(request.POST['product_id'])
                term = request.POST['term']
                product_id = product_id + list(PromotionDetail.objects.filter(promotion__active=True).values_list('product_id', flat=True))
                filters = Q()
                if len(term):
                    filters &= Q(Q(name__icontains=term) | Q(code__icontains=term))
                queryset = Product.objects.filter(filters).exclude(id__in=product_id).order_by('name')
                if filters.children and len(term):
                    queryset = queryset[0:10]
                for i in queryset:
                    item = i.as_dict()
                    item['selected'] = False
                    data.append(item)
            else:
                data['error'] = 'No ha seleccionado ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_products(self):
        data = []
        try:
            for i in self.object.promotiondetail_set.all():
                item = i.product.as_dict()
                item['discount'] = f'{float(i.discount) * 100:.2f}'
                item['total_discount'] = f'{i.total_discount:.2f}'
                item['current_price'] = f'{i.current_price:.2f}'
                item['final_price'] = f'{i.final_price:.2f}'
                data.append(item)
        except:
            pass
        return json.dumps(data)

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context['title'] = f'Edición de una {self.model._meta.verbose_name}'
        context['list_url'] = self.success_url
        context['action'] = 'edit'
        context['products'] = self.get_products()
        return context


class PromotionDeleteView(GroupPermissionMixin, CompanyQuerysetMixin, DeleteView):
    model = Promotion
    template_name = 'delete.html'
    success_url = reverse_lazy('promotion_list')
    permission_required = 'delete_promotion'

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
