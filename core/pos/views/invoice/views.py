import json

from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from core.pos.forms import InvoiceForm, Invoice, Customer, Receipt, Product, InvoiceDetail, CreditNote, CreditNoteDetail, Company, AccountReceivable, VOUCHER_TYPE, INVOICE_STATUS, PAYMENT_TYPE
from core.pos.utilities.pdf_creator import PDFCreator
from core.pos.utilities.sri import SRI
from core.report.forms import ReportForm
from core.security.mixins import GroupPermissionMixin, AutoAssignCompanyMixin, CompanyQuerysetMixin
from core.subscription.models import check_quota_limits


class InvoiceListView(GroupPermissionMixin, CompanyQuerysetMixin, ListView):
    model = Invoice
    template_name = 'invoice/list_admin.html'
    permission_required = 'view_invoice_admin'

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
                for i in self.get_queryset().filter(filters):
                    item = i.as_dict()
                    item['print_pdf'] = str(reverse_lazy('invoice_print', kwargs={'pk': i.id, 'code': VOUCHER_TYPE[0][0]}))
                    item['print_ticket'] = str(reverse_lazy('invoice_print', kwargs={'pk': i.id, 'code': VOUCHER_TYPE[2][0]}))
                    data.append(item)
            elif action == 'search_detail_products':
                data = []
                for i in InvoiceDetail.objects.filter(invoice_id=request.POST['id']):
                    data.append(i.as_dict())
            elif action == 'create_electronic_invoice':
                invoice = self.model.objects.get(pk=request.POST['id'])
                
                # Verificar si necesita número de recibo
                receipt_number_is_null = invoice.receipt_number_is_null()
                if receipt_number_is_null:
                    invoice.receipt_number = invoice.generate_receipt_number()
                    invoice.receipt_number_full = invoice.generate_receipt_number_full()
                    invoice.edit()
                
                # Intentar generar factura electrónica
                data = invoice.generate_electronic_invoice_document()
                
                # Si hay error de secuencial registrado, intentar con el siguiente
                if not data['resp'] and 'error' in data:
                    if invoice.check_sequential_error(errors=data):
                        # Guardar el error actual
                        invoice.create_receipt_error(errors=data, change_status=False)
                        
                        # Intentar con el siguiente secuencial disponible
                        if invoice.find_next_available_sequential():
                            invoice.edit()  # Guardar el nuevo secuencial
                            
                            # Reintentar la generación
                            data = invoice.generate_electronic_invoice_document()
                            
                            if data['resp']:
                                invoice.create_electronic_invoice = True
                                invoice.edit()
                        else:
                            # Si no se pudo encontrar secuencial disponible
                            data['error'] = 'No se pudo encontrar un secuencial disponible'
                elif data['resp']:
                    # Éxito en el primer intento
                    invoice.create_electronic_invoice = True
                    invoice.edit()
                    if receipt_number_is_null:
                        invoice.save_sequence_number()
            elif action == 'create_credit_note':
                with transaction.atomic():
                    invoice = self.model.objects.get(pk=request.POST['id'])
                    credit_note = CreditNote()
                    credit_note.invoice_id = invoice.id
                    credit_note.motive = F'NOTA DE CREDITO DE LA VENTA {invoice.receipt_number_full}'
                    credit_note.company = invoice.company
                    credit_note.environment_type = credit_note.company.environment_type
                    credit_note.receipt = Receipt.objects.get(voucher_type=VOUCHER_TYPE[1][0], establishment_code=invoice.company.establishment_code, issuing_point_code=invoice.company.issuing_point_code)
                    credit_note.receipt_number = credit_note.generate_receipt_number()
                    credit_note.receipt_number_full = credit_note.get_receipt_number_full()
                    credit_note.tax = invoice.company.tax_rate
                    credit_note.save()
                    for invoice_detail in invoice.invoicedetail_set.all():
                        credit_note_detail = CreditNoteDetail()
                        credit_note_detail.credit_note_id = credit_note.id
                        credit_note_detail.invoice_detail_id = invoice_detail.id
                        credit_note_detail.product_id = invoice_detail.product_id
                        credit_note_detail.quantity = invoice_detail.quantity
                        credit_note_detail.price = invoice_detail.price
                        credit_note_detail.discount = invoice_detail.discount
                        credit_note_detail.save()
                    credit_note.recalculate_invoice()
                    data = credit_note.generate_electronic_invoice_document()
                    if not data['resp']:
                        transaction.set_rollback(True)
                    else:
                        invoice.status = INVOICE_STATUS[3][0]
                        invoice.edit()
                if 'error' in data:
                    credit_note.create_receipt_error(errors=data, change_status=False)
            elif action == 'send_receipt_by_email':
                invoice = self.model.objects.get(pk=request.POST['id'])
                data = SRI().send_receipt_by_email(instance=invoice)
            else:
                data['error'] = 'No ha seleccionado ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Listado de {self.model._meta.verbose_name_plural}'
        context['create_url'] = reverse_lazy('invoice_create_admin')
        context['form'] = ReportForm(company=getattr(self.request, 'company', None) or getattr(self.request.user, 'company', None))
        return context


class InvoiceCreateView(AutoAssignCompanyMixin, GroupPermissionMixin, CompanyQuerysetMixin, CreateView):
    model = Invoice
    template_name = 'invoice/create_admin.html'
    form_class = InvoiceForm
    success_url = reverse_lazy('invoice_list_admin')
    permission_required = 'add_invoice_admin'

    def get_company(self):
        # Usar la compañía del request; como fallback, la del usuario
        company = getattr(self.request, 'company', None)
        if company is None:
            company = getattr(self.request.user, 'company', None)
        return company

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        company = self.get_company()
        receipt = None
        if company:
            receipt = Receipt.objects.filter(company=company, voucher_type=VOUCHER_TYPE[0][0], establishment_code=company.establishment_code, issuing_point_code=company.issuing_point_code).first()
        kwargs['initial'] = {
            'receipt_number': f'{receipt.sequence + 1:09d}' if receipt else ''
        }
        return kwargs

    def get_end_consumer(self):
        customer = Customer.objects.filter(dni='9999999999999').first()
        return customer.as_dict() if customer else dict()

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST['action']
        try:
            if action == 'add':
                # Verificar cuotas antes de crear
                quota_check = check_quota_limits(request.user, 'invoice')
                if not quota_check['can_create']:
                    data['error'] = quota_check['message']
                else:
                    with transaction.atomic():
                        invoice = Invoice()
                        invoice.date_joined = request.POST['date_joined']
                        invoice.end_credit = request.POST['end_credit']
                        
                        # Debug: verificar qué tipo de objeto es company
                        company = self.get_company()
                        if company is None:
                            raise Exception('No se pudo determinar la compañía actual.')
                        invoice.company = company
                        invoice.environment_type = invoice.company.environment_type
                        invoice.receipt = Receipt.objects.get(company=company, voucher_type=request.POST['receipt'], establishment_code=invoice.company.establishment_code, issuing_point_code=invoice.company.issuing_point_code)
                        invoice.receipt_number = invoice.generate_receipt_number()
                        invoice.receipt_number_full = invoice.get_receipt_number_full()
                        invoice.employee_id = request.user.id
                        invoice.payment_type = request.POST['payment_type']
                        invoice.customer_id = int(request.POST['customer'])
                        invoice.tax = invoice.company.tax_rate
                        invoice.create_electronic_invoice = False
                        if not invoice.receipt.is_ticket:
                            invoice.create_electronic_invoice = 'create_electronic_invoice' in request.POST
                            invoice.is_draft_invoice = 'is_draft_invoice' in request.POST
                        invoice.additional_info = json.loads(request.POST['additional_info'])
                        invoice.save()
                        for i in json.loads(request.POST['products']):
                            product = Product.objects.get(pk=i['id'])
                            invoice_detail = InvoiceDetail.objects.create(
                                invoice_id=invoice.id,
                                product_id=product.id,
                                quantity=int(i['quantity']),
                                price=float(i['current_price']),
                                discount=float(i['discount']) / 100
                            )
                            invoice_detail.deduct_product_stock()
                        invoice.recalculate_invoice()
                        if invoice.payment_type == PAYMENT_TYPE[1][0]:
                            AccountReceivable.objects.create(
                                invoice_id=invoice.id,
                                date_joined=invoice.date_joined,
                                end_date=invoice.end_credit,
                                debt=invoice.total_amount
                            )
                        data = {'print_url': str(reverse_lazy('invoice_print', kwargs={'pk': invoice.id, 'code': invoice.receipt.voucher_type}))}
                        if invoice.create_electronic_invoice and not invoice.is_draft_invoice:
                            data = invoice.generate_electronic_invoice_document()
                            if data.get('resp'):
                                # Enviar por correo automáticamente al autorizar
                                try:
                                    email_resp = SRI().send_receipt_by_email(instance=invoice)
                                    data['email'] = email_resp
                                except Exception as e:
                                    data['email_error'] = str(e)
                            else:
                                transaction.set_rollback(True)
                if 'error' in data:
                    invoice.create_receipt_error(errors=data, change_status=False)
            elif action == 'get_receipt_number':
                company = self.get_company()
                data['receipt_number'] = ''
                receipt = None
                if company:
                    receipt = Receipt.objects.filter(company=company, voucher_type=request.POST['receipt'], establishment_code=company.establishment_code, issuing_point_code=company.issuing_point_code).first()
                if receipt:
                    data['receipt_number'] = f'{receipt.sequence + 1:09d}'
            elif action == 'search_product':
                try:
                    product_id = json.loads(request.POST.get('product_id', '[]'))
                except Exception:
                    product_id = []
                data = []
                term = request.POST.get('term', '').strip()
                filters = Q(Q(stock__gt=0) | Q(is_inventoried=False))
                if term:
                    filters &= Q(Q(name__icontains=term) | Q(code__icontains=term))
                # Filtrar por compañía actual
                company = self.get_company()
                queryset = Product.objects.filter(filters)
                if company:
                    queryset = queryset.filter(company=company)
                queryset = queryset.exclude(id__in=product_id).order_by('name')[:20]
                for i in queryset:
                    item = i.as_dict()
                    item['discount'] = 0.00
                    item['total_discount'] = 0.00
                    data.append(item)
            elif action == 'search_product_code':
                code = request.POST['code']
                if len(code):
                    company = self.get_company()
                    qs = Product.objects
                    if company:
                        qs = qs.filter(company=company)
                    product = qs.filter(code=code).first()
                    if product:
                        data = product.as_dict()
                        data['discount'] = 0.00
                        data['total_discount'] = 0.00
            elif action == 'search_customer':
                data = []
                term = request.POST['term']
                print(f"[InvoiceCreateView.search_customer] Buscando clientes con término: '{term}'")
                print(f"[InvoiceCreateView.search_customer] Usuario: {request.user}")
                print(f"[InvoiceCreateView.search_customer] Company del request: {getattr(request, 'company', 'NO COMPANY')}")
                
                # Obtener la company del request
                company = getattr(request, 'company', None)
                
                # Construir el filtro base
                base_filter = Q(user__names__icontains=term) | Q(dni__icontains=term)
                
                # Agregar filtro por company si existe
                if company:
                    customers_qs = Customer.objects.filter(base_filter, company=company)
                    print(f"[InvoiceCreateView.search_customer] Filtrando por company {company.id}: {company.company_name}")
                else:
                    customers_qs = Customer.objects.filter(base_filter)
                    print(f"[InvoiceCreateView.search_customer] SIN FILTRO DE COMPANY - se traerán todos los clientes")
                
                customers_qs = customers_qs.order_by('user__names')[0:10]
                print(f"[InvoiceCreateView.search_customer] Clientes encontrados: {customers_qs.count()}")
                
                for i in customers_qs:
                    customer_dict = i.as_dict()
                    print(f"[InvoiceCreateView.search_customer] Cliente: {i.user.names} (ID: {i.id}, Company: {i.company})")
                    print(f"[InvoiceCreateView.search_customer] Dict del cliente: {customer_dict}")
                    print(f"[InvoiceCreateView.search_customer] Campos del dict: {list(customer_dict.keys())}")
                    data.append(customer_dict)
                
                print(f"[InvoiceCreateView.search_customer] Respuesta final: {data}")
            elif action == 'check_quota':
                # Nueva acción para verificar cuotas
                quota_check = check_quota_limits(request.user, 'invoice')
                data = quota_check
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
        context['additional_info'] = []
        
        # Agregar información de cuotas
        quota_check = check_quota_limits(self.request.user, 'invoice')
        context['quota_info'] = quota_check
        
        return context


class InvoiceUpdateView(AutoAssignCompanyMixin, GroupPermissionMixin, CompanyQuerysetMixin, UpdateView):
    model = Invoice
    template_name = 'invoice/create_admin.html'
    form_class = InvoiceForm
    success_url = reverse_lazy('invoice_list_admin')
    permission_required = 'change_invoice_admin'

    def get_company(self):
        company = getattr(self.request, 'company', None)
        if company is None:
            company = getattr(self.request.user, 'company', None)
        return company

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['disabled_fields'] = ['receipt']
        return kwargs

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST['action']
        try:
            if action == 'edit':
                with transaction.atomic():
                    invoice = self.get_object()
                    invoice.date_joined = request.POST['date_joined']
                    invoice.end_credit = request.POST['end_credit']
                    invoice.employee_id = request.user.id
                    invoice.payment_type = request.POST['payment_type']
                    invoice.customer_id = int(request.POST['customer'])
                    invoice.tax = invoice.company.tax_rate
                    invoice.create_electronic_invoice = False
                    if not invoice.receipt.is_ticket:
                        invoice.create_electronic_invoice = 'create_electronic_invoice' in request.POST
                        invoice.is_draft_invoice = 'is_draft_invoice' in request.POST
                    invoice.additional_info = json.loads(request.POST['additional_info'])
                    invoice.save()
                    invoice.invoicedetail_set.all().delete()
                    invoice.accountreceivable_set.all().delete()
                    for i in json.loads(request.POST['products']):
                        product = Product.objects.get(pk=i['id'])
                        invoice_detail = InvoiceDetail.objects.create(
                            invoice_id=invoice.id,
                            product_id=product.id,
                            quantity=int(i['quantity']),
                            price=float(i['current_price']),
                            discount=float(i['discount']) / 100
                        )
                        invoice_detail.deduct_product_stock()
                    invoice.recalculate_invoice()
                    if invoice.payment_type == PAYMENT_TYPE[1][0]:
                        AccountReceivable.objects.create(
                            invoice_id=invoice.id,
                            date_joined=invoice.date_joined,
                            end_date=invoice.end_credit,
                            debt=invoice.total_amount
                        )
                    data = {'print_url': str(reverse_lazy('invoice_print', kwargs={'pk': invoice.id, 'code': invoice.receipt.voucher_type}))}
                    if invoice.create_electronic_invoice and not invoice.is_draft_invoice:
                        data = invoice.generate_electronic_invoice_document()
                        if not data['resp']:
                            transaction.set_rollback(True)
                if 'error' in data:
                    invoice.create_receipt_error(errors=data, change_status=False)
            elif action == 'get_receipt_number':
                company = self.get_company()
                data['receipt_number'] = ''
                receipt = None
                if company:
                    receipt = Receipt.objects.filter(company=company, voucher_type=request.POST['receipt'], establishment_code=company.establishment_code, issuing_point_code=company.issuing_point_code).first()
                if receipt:
                    data['receipt_number'] = f'{receipt.sequence + 1:09d}'
            elif action == 'search_product':
                try:
                    product_id = json.loads(request.POST.get('product_id', '[]'))
                except Exception:
                    product_id = []
                data = []
                term = request.POST.get('term', '').strip()
                filters = Q(Q(stock__gt=0) | Q(is_inventoried=False))
                if term:
                    filters &= Q(Q(name__icontains=term) | Q(code__icontains=term))
                company = self.get_company()
                queryset = Product.objects.filter(filters)
                if company:
                    queryset = queryset.filter(company=company)
                queryset = queryset.exclude(id__in=product_id).order_by('name')[:20]
                for i in queryset:
                    item = i.as_dict()
                    item['discount'] = 0.00
                    item['total_discount'] = 0.00
                    data.append(item)
            elif action == 'search_product_code':
                code = request.POST['code']
                if len(code):
                    company = self.get_company()
                    qs = Product.objects
                    if company:
                        qs = qs.filter(company=company)
                    product = qs.filter(code=code).first()
                    if product:
                        data = product.as_dict()
                        data['discount'] = 0.00
                        data['total_discount'] = 0.00
            elif action == 'search_customer':
                data = []
                term = request.POST['term']
                
                # Obtener la company del request
                company = getattr(request, 'company', None)
                
                # Construir el filtro base
                base_filter = Q(user__names__icontains=term) | Q(dni__icontains=term)
                
                # Agregar filtro por company si existe
                if company:
                    customers_qs = Customer.objects.filter(base_filter, company=company)
                else:
                    customers_qs = Customer.objects.filter(base_filter)
                
                customers_qs = customers_qs.order_by('user__names')[0:10]
                
                for i in customers_qs:
                    data.append(i.as_dict())
            else:
                data['error'] = 'No ha seleccionado ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_products(self):
        data = []
        for detail in self.object.invoicedetail_set.all():
            item = detail.product.as_dict()
            item['quantity'] = detail.quantity
            item['current_price'] = float(detail.price)
            item['discount'] = float(detail.discount_rate)
            item['total_discount'] = float(detail.total_discount)
            data.append(item)
        return json.dumps(data)

    def get_additional_info(self):
        additional_info = self.get_object().additional_info
        if additional_info:
            return json.dumps(additional_info)
        return []

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context['title'] = f'Edición de una {self.model._meta.verbose_name}'
        context['list_url'] = self.success_url
        context['action'] = 'edit'
        context['end_consumer'] = json.dumps(self.object.customer.as_dict())
        context['products'] = self.get_products()
        context['additional_info'] = self.get_additional_info()
        return context


class InvoiceDeleteView(GroupPermissionMixin, CompanyQuerysetMixin, DeleteView):
    model = Invoice
    template_name = 'delete.html'
    success_url = reverse_lazy('invoice_list_admin')
    permission_required = 'delete_invoice_admin'

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


class InvoicePrintView(GroupPermissionMixin, ListView):
    model = Invoice
    template_name = 'invoice/invoice_pdf.html'
    success_url = reverse_lazy('invoice_list_admin')
    permission_required = 'print_invoice'

    def get_template_names(self):
        if self.kwargs['code'] == VOUCHER_TYPE[2][0]:
            return 'invoice/ticket_pdf.html'
        return self.template_name

    def get(self, request, *args, **kwargs):
        invoice = self.get_queryset().filter(id=self.kwargs['pk']).first()
        if invoice:
            context = {'object': invoice, 'height': 450 + invoice.invoicedetail_set.all().count() * 10}
            pdf_file = PDFCreator(template_name=self.get_template_names()).create(context=context)
            return HttpResponse(pdf_file, content_type='application/pdf')
        return HttpResponseRedirect(self.success_url)


class InvoiceCustomerListView(GroupPermissionMixin, ListView):
    model = Invoice
    template_name = 'invoice/list_customer.html'
    permission_required = 'view_invoice_customer'

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST['action']
        try:
            if action == 'search':
                data = []
                start_date = request.POST.get('start_date', '')
                end_date = request.POST.get('end_date', '')
                filters = Q(customer__user=request.user)
                if len(start_date) and len(end_date):
                    filters &= Q(date_joined__range=[start_date, end_date])
                for i in self.model.objects.filter(filters):
                    item = i.as_dict()
                    item['print_pdf'] = str(reverse_lazy('invoice_print', kwargs={'pk': i.id, 'code': VOUCHER_TYPE[0][0]}))
                    item['print_ticket'] = str(reverse_lazy('invoice_print', kwargs={'pk': i.id, 'code': VOUCHER_TYPE[2][0]}))
                    data.append(item)
            elif action == 'search_detail_products':
                data = []
                for i in InvoiceDetail.objects.filter(invoice_id=request.POST['id']):
                    data.append(i.as_dict())
            else:
                data['error'] = 'No ha seleccionado ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Listado de {self.model._meta.verbose_name_plural}'
        context['form'] = ReportForm()
        return context
