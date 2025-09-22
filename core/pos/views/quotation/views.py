import json

from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from core.pos.forms import QuotationForm, Quotation, Customer, Product, QuotationDetail, Company
from core.pos.utilities.pdf_creator import PDFCreator
from core.report.forms import ReportForm
from core.security.mixins import GroupPermissionMixin


class QuotationListView(GroupPermissionMixin, ListView):
    model = Quotation
    template_name = 'quotation/list.html'
    permission_required = 'view_quotation'

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST['action']
        try:
            if action == 'search':
                data = []
                start_date = request.POST.get('start_date', '')
                end_date = request.POST.get('end_date', '')
                filters = Q()
                if len(start_date) and len(end_date):
                    filters &= Q(date_joined__range=[start_date, end_date])
                for i in self.model.objects.filter(filters):
                    item = i.as_dict()
                    item['validate_stock'] = i.validate_stock
                    data.append(item)
            elif action == 'search_detail_products':
                data = []
                for i in QuotationDetail.objects.filter(quotation_id=request.POST['id']):
                    item = i.as_dict()
                    item['validate_stock'] = i.product.stock >= i.quantity if i.product.is_inventoried else True
                    data.append(item)
            elif action == 'send_quotation_by_email':
                quotation = Quotation.objects.get(id=request.POST['id'])
                quotation.send_quotation_by_email()
            elif action == 'create_electronic_invoice':
                quotation = Quotation.objects.get(id=request.POST['id'])
                data = quotation.create_invoice()
            elif action == 'create_draft_invoice':
                quotation = Quotation.objects.get(id=request.POST['id'])
                data = quotation.create_invoice(is_draft_invoice=True)
            else:
                data['error'] = 'No ha seleccionado ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Listado de {self.model._meta.verbose_name_plural}'
        context['create_url'] = reverse_lazy('quotation_create')
        context['form'] = ReportForm()
        return context


class QuotationCreateView(GroupPermissionMixin, CreateView):
    model = Quotation
    template_name = 'quotation/create.html'
    form_class = QuotationForm
    success_url = reverse_lazy('quotation_list')
    permission_required = 'add_quotation'

    def get_company(self):
        return Company.objects.first() or Company()

    def get_end_consumer(self):
        customer = Customer.objects.filter(dni='9999999999999').first()
        return customer.as_dict() if customer else dict()

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST['action']
        try:
            if action == 'add':
                with transaction.atomic():
                    quotation = Quotation()
                    quotation.customer_id = int(request.POST['customer'])
                    quotation.company = self.get_company()
                    quotation.employee_id = request.user.id
                    quotation.date_joined = request.POST['date_joined']
                    quotation.tax = quotation.company.tax_rate
                    quotation.save()
                    for i in json.loads(request.POST['products']):
                        product = Product.objects.get(pk=i['id'])
                        QuotationDetail.objects.create(
                            quotation_id=quotation.id,
                            product_id=product.id,
                            quantity=int(i['quantity']),
                            price=float(i['current_price']),
                            discount=float(i['discount']) / 100
                        )
                    quotation.recalculate_invoice()
                    data = {'print_url': str(reverse_lazy('quotation_print', kwargs={'pk': quotation.id}))}
            elif action == 'search_product':
                product_id = json.loads(request.POST['product_id'])
                data = []
                term = request.POST['term']
                filters = Q()
                if len(term):
                    filters &= Q(Q(name__icontains=term) | Q(code__icontains=term))
                queryset = Product.objects.filter(filters).exclude(id__in=product_id).order_by('name')
                if not filters.children:
                    queryset = queryset[0:10]
                for i in queryset:
                    item = i.as_dict()
                    item['discount'] = 0.00
                    item['total_discount'] = 0.00
                    data.append(item)
            elif action == 'search_product_code':
                code = request.POST['code']
                if len(code):
                    product = Product.objects.filter(code=code).first()
                    if product:
                        data = product.as_dict()
                        data['discount'] = 0.00
                        data['total_discount'] = 0.00
            elif action == 'search_customer':
                data = []
                term = request.POST['term']
                for i in Customer.objects.filter(Q(user__names__icontains=term) | Q(dni__icontains=term)).order_by('user__names')[0:10]:
                    data.append(i.as_dict())
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
        context['end_consumer'] = json.dumps(self.get_end_consumer())
        context['products'] = []
        return context


class QuotationUpdateView(GroupPermissionMixin, UpdateView):
    model = Quotation
    template_name = 'quotation/create.html'
    form_class = QuotationForm
    success_url = reverse_lazy('quotation_list')
    permission_required = 'change_quotation'

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().dispatch(request, *args, **kwargs)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['customer'].queryset = Customer.objects.filter(id=self.object.customer.id)
        return form

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST['action']
        try:
            if action == 'edit':
                with transaction.atomic():
                    quotation = self.get_object()
                    quotation.customer_id = int(request.POST['customer'])
                    quotation.employee_id = request.user.id
                    quotation.date_joined = request.POST['date_joined']
                    quotation.tax = quotation.company.tax_rate
                    quotation.save()
                    quotation.quotationdetail_set.all().delete()
                    for i in json.loads(request.POST['products']):
                        product = Product.objects.get(pk=i['id'])
                        QuotationDetail.objects.create(
                            quotation_id=quotation.id,
                            product_id=product.id,
                            quantity=int(i['quantity']),
                            price=float(i['current_price']),
                            discount=float(i['discount']) / 100
                        )
                    quotation.recalculate_invoice()
                    data = {'print_url': str(reverse_lazy('quotation_print', kwargs={'pk': quotation.id}))}
            elif action == 'search_product':
                product_id = json.loads(request.POST['product_id'])
                data = []
                term = request.POST['term']
                filters = Q()
                if len(term):
                    filters &= Q(Q(name__icontains=term) | Q(code__icontains=term))
                queryset = Product.objects.filter(filters).exclude(id__in=product_id).order_by('name')
                if not filters.children:
                    queryset = queryset[0:10]
                for i in queryset:
                    item = i.as_dict()
                    item['discount'] = 0.00
                    item['total_discount'] = 0.00
                    data.append(item)
            elif action == 'search_product_code':
                code = request.POST['code']
                if len(code):
                    product = Product.objects.filter(code=code).first()
                    if product:
                        data = product.as_dict()
                        data['discount'] = 0.00
                        data['total_discount'] = 0.00
            elif action == 'search_customer':
                data = []
                term = request.POST['term']
                for i in Customer.objects.filter(Q(user__names__icontains=term) | Q(dni__icontains=term)).order_by('user__names')[0:10]:
                    data.append(i.as_dict())
            else:
                data['error'] = 'No ha seleccionado ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_products(self):
        data = []
        for detail in self.object.quotationdetail_set.all():
            item = detail.product.as_dict()
            item['quantity'] = detail.quantity
            item['current_price'] = float(detail.price)
            item['discount'] = float(detail.discount_rate)
            item['total_discount'] = float(detail.total_discount)
            data.append(item)
        return json.dumps(data)

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context['title'] = f'Edición de una {self.model._meta.verbose_name}'
        context['list_url'] = self.success_url
        context['action'] = 'edit'
        context['end_consumer'] = dict()
        context['products'] = self.get_products()
        return context


class QuotationDeleteView(GroupPermissionMixin, DeleteView):
    model = Quotation
    template_name = 'delete.html'
    success_url = reverse_lazy('quotation_list')
    permission_required = 'delete_quotation'

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            self.get_object().delete()
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Eliminación de una {self.model._meta.verbose_name}'
        context['list_url'] = self.success_url
        return context


class QuotationPrintView(GroupPermissionMixin, ListView):
    model = Quotation
    template_name = 'quotation/invoice_pdf.html'
    success_url = reverse_lazy('quotation_list')
    permission_required = 'print_quotation'

    def get(self, request, *args, **kwargs):
        quotation = self.model.objects.filter(id=self.kwargs['pk']).first()
        if quotation:
            context = {'quotation': quotation}
            pdf_file = PDFCreator(template_name=self.template_name).create(context=context)
            return HttpResponse(pdf_file, content_type='application/pdf')
        return HttpResponseRedirect(self.success_url)
