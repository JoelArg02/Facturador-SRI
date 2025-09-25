import json

from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.views.generic import DeleteView, CreateView, ListView

from core.pos.forms import AccountPayable, AccountPayablePaymentForm, AccountPayablePayment
from core.report.forms import ReportForm
from core.security.mixins import GroupPermissionMixin, CompanyQuerysetMixin, AutoAssignCompanyMixin


class AccountPayableListView(GroupPermissionMixin, CompanyQuerysetMixin, ListView):
    model = AccountPayable
    template_name = 'account_payable/list.html'
    permission_required = 'view_account_payable'

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
                    data.append(i.as_dict())
            elif action == 'search_payments':
                data = []
                base_qs = AccountPayablePayment.objects.filter(account_payable_id=request.POST['id'])
                # Asegurar filtrado por company a través de la relación inversa
                if hasattr(base_qs.model, 'account_payable'):
                    base_qs = base_qs.filter(account_payable__company=getattr(request, 'company', None))
                for index, i in enumerate(base_qs.order_by('id'), start=1):
                    item = i.as_dict()
                    item['index'] = index
                    data.append(item)
            elif action == 'delete_payment':
                account_payable_detail = AccountPayablePayment.objects.get(pk=request.POST['id'])
                account_payable_detail.delete()
            else:
                data['error'] = 'No ha seleccionado ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Listado de {self.model._meta.verbose_name_plural}'
        context['create_url'] = reverse_lazy('account_payable_create')
        context['form'] = ReportForm()
        return context


class AccountPayableCreateView(AutoAssignCompanyMixin, GroupPermissionMixin, CompanyQuerysetMixin, CreateView):
    model = AccountPayablePayment
    template_name = 'account_payable/create.html'
    form_class = AccountPayablePaymentForm
    success_url = reverse_lazy('account_payable_list')
    permission_required = 'add_account_payable'

    def post(self, request, *args, **kwargs):
        action = request.POST['action']
        data = {}
        try:
            if action == 'search_account_payable':
                data = []
                term = request.POST['term']
                qs = AccountPayable.objects.filter(Q(purchase__provider__name__icontains=term) | Q(purchase__number__icontains=term)).exclude(active=False)
                company = getattr(request, 'company', None)
                if company:
                    qs = qs.filter(company=company)
                for i in qs[0:10]:
                    data.append(i.as_dict())
            elif action == 'add':
                with transaction.atomic():
                    AccountPayablePayment.objects.create(
                        account_payable_id=int(request.POST['account_payable']),
                        date_joined=request.POST['date_joined'],
                        amount=float(request.POST['amount']),
                        description=request.POST['description']
                    )
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
        return context


class AccountPayableDeleteView(GroupPermissionMixin, CompanyQuerysetMixin, DeleteView):
    model = AccountPayable
    template_name = 'delete.html'
    success_url = reverse_lazy('account_payable_list')
    permission_required = 'delete_account_payable'

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
