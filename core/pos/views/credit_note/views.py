import json

from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView

from core.pos.forms import CreditNoteForm, CreditNote, CreditNoteDetail, Invoice, Receipt, InvoiceDetail, VOUCHER_TYPE, INVOICE_STATUS, IDENTIFICATION_TYPE
from core.pos.models import Company
from core.pos.utilities.pdf_creator import PDFCreator
from core.pos.utilities.sri import SRI
from core.report.forms import ReportForm
from core.security.mixins import GroupPermissionMixin, CompanyQuerysetMixin, AutoAssignCompanyMixin


class CreditNoteListView(GroupPermissionMixin, CompanyQuerysetMixin, ListView):
    model = CreditNote
    template_name = 'credit_note/list_admin.html'
    permission_required = 'view_credit_note_admin'

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
                for i in self.get_queryset().filter(filters):
                    item = i.as_dict()
                    item['print_pdf'] = str(reverse_lazy('credit_note_print', kwargs={'pk': i.id}))
                    data.append(item)
            elif action == 'search_detail_products':
                data = []
                for i in CreditNoteDetail.objects.filter(credit_note_id=request.POST['id']):
                    data.append(i.as_dict())
            elif action == 'create_electronic_credit_note':
                credit_note = self.model.objects.get(pk=request.POST['id'])
                data = credit_note.generate_electronic_invoice_document()
            elif action == 'send_receipt_by_email':
                credit_note = self.model.objects.get(pk=request.POST['id'])
                data = SRI().send_receipt_by_email(instance=credit_note)
            else:
                data['error'] = 'No ha seleccionado ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Listado de {self.model._meta.verbose_name_plural}'
        context['create_url'] = reverse_lazy('credit_note_create_admin')
        context['form'] = ReportForm()
        return context


class CreditNoteCreateView(AutoAssignCompanyMixin, GroupPermissionMixin, CompanyQuerysetMixin, CreateView):
    model = CreditNote
    template_name = 'credit_note/create_admin.html'
    form_class = CreditNoteForm
    success_url = reverse_lazy('credit_note_list_admin')
    permission_required = 'add_credit_note_admin'

    def get_company(self):
        # Utilizar la compañía activa del request si existe
        company = getattr(self.request, 'company', None)
        if company:
            return company
        return Company.objects.first() or Company()

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        company = self.get_company()
        receipt = Receipt.objects.filter(voucher_type=VOUCHER_TYPE[1][0], establishment_code=company.establishment_code, issuing_point_code=company.issuing_point_code).first()
        kwargs['initial'] = {
            'receipt_number': f'{receipt.sequence + 1:09d}' if receipt else ''
        }
        return kwargs

    def post(self, request, *args, **kwargs):
        action = request.POST['action']
        data = {}
        try:
            if action == 'add':
                with transaction.atomic():
                    credit_note = CreditNote()
                    credit_note.invoice_id = int(request.POST['invoice'])
                    credit_note.motive = request.POST['motive']
                    credit_note.company = self.get_company()
                    credit_note.environment_type = credit_note.company.environment_type
                    credit_note.receipt = Receipt.objects.get(voucher_type=VOUCHER_TYPE[1][0], establishment_code=credit_note.company.establishment_code, issuing_point_code=credit_note.company.issuing_point_code)
                    credit_note.receipt_number = credit_note.generate_receipt_number()
                    credit_note.receipt_number_full = credit_note.get_receipt_number_full()
                    credit_note.tax = credit_note.company.tax_rate
                    credit_note.create_electronic_invoice = 'create_electronic_invoice' in request.POST
                    credit_note.save()
                    for i in json.loads(request.POST['products']):
                        invoice_detail = InvoiceDetail.objects.get(id=i['id'])
                        CreditNoteDetail.objects.create(
                            credit_note_id=credit_note.id,
                            invoice_detail_id=invoice_detail.id,
                            product_id=invoice_detail.product_id,
                            quantity=int(i['new_quantity']),
                            price=float(i['price']),
                            discount=float(i['discount']) / 100
                        )
                    credit_note.recalculate_invoice()
                    if credit_note.create_electronic_invoice:
                        data = credit_note.generate_electronic_invoice_document()
                        if not data['resp']:
                            transaction.set_rollback(True)
                        else:
                            credit_note.invoice.status = INVOICE_STATUS[3][0]
                            credit_note.invoice.edit()
                if 'error' in data:
                    credit_note.create_receipt_error(errors=data, change_status=False)
            elif action == 'search_invoice':
                data = []
                term = request.POST['term']
                invoices = Invoice.objects.filter(status__in=[INVOICE_STATUS[1][0], INVOICE_STATUS[2][0]])
                company = getattr(request, 'company', None)
                if company:
                    invoices = invoices.filter(company=company)
                for i in invoices.filter(Q(receipt_number_full__icontains=term) | Q(receipt_number__icontains=term) | Q(customer__user__names__icontains=term) | Q(customer__dni__icontains=term)).exclude(customer__identification_type=IDENTIFICATION_TYPE[-2][0]).order_by('receipt_number')[0:10]:
                    item = i.as_dict()
                    detail = []
                    for d in i.invoicedetail_set.all():
                        info = d.as_dict()
                        info['new_quantity'] = d.quantity
                        info['selected'] = 0
                        info['total_amount'] = 0.00
                        detail.append(info)
                    item['detail'] = detail
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
        return context


class CreditNoteDeleteView(GroupPermissionMixin, CompanyQuerysetMixin, DeleteView):
    model = CreditNote
    template_name = 'delete.html'
    success_url = reverse_lazy('credit_note_admin_list')
    permission_required = 'delete_credit_note_admin'

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


class CreditNotePrintView(GroupPermissionMixin, CompanyQuerysetMixin, ListView):
    model = CreditNote
    template_name = 'credit_note/invoice_pdf.html'
    success_url = reverse_lazy('credit_note_admin_list')
    permission_required = 'print_credit_note'

    def get(self, request, *args, **kwargs):
        credit_note = self.get_queryset().filter(id=self.kwargs['pk']).first()
        if credit_note:
            context = {'object': credit_note}
            pdf_file = PDFCreator(template_name=self.template_name).create(context=context)
            return HttpResponse(pdf_file, content_type='application/pdf')
        return HttpResponseRedirect(self.success_url)


class CreditNoteCustomerListView(GroupPermissionMixin, CompanyQuerysetMixin, ListView):
    model = CreditNote
    template_name = 'credit_note/list_customer.html'
    permission_required = 'view_credit_note_customer'

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST['action']
        try:
            if action == 'search':
                data = []
                start_date = request.POST['start_date']
                end_date = request.POST['end_date']
                filters = Q(invoice__customer__user=request.user)
                if len(start_date) and len(end_date):
                    filters &= Q(date_joined__range=[start_date, end_date])
                for i in self.get_queryset().filter(filters):
                    item = i.as_dict()
                    item['print_pdf'] = str(reverse_lazy('credit_note_print', kwargs={'pk': i.id}))
                    data.append(item)
            elif action == 'search_detail_products':
                data = []
                for i in CreditNoteDetail.objects.filter(credit_note_id=request.POST['id']):
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
