import json

from django.db.models import Q
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.views.generic import ListView, DeleteView

from core.pos.models import ReceiptError
from core.report.forms import ReportForm
from core.security.mixins import GroupPermissionMixin, CompanyQuerysetMixin


class ReceiptErrorListView(GroupPermissionMixin, CompanyQuerysetMixin, ListView):
    model = ReceiptError
    template_name = 'receipt_error/list.html'
    permission_required = 'view_receipt_error'

    def get_queryset(self):
        """Filtra los errores por la empresa del usuario a través de receipt.company"""
        qs = super().get_queryset()
        company = self.get_company()
        
        # Si hay empresa y el usuario no es superusuario, filtrar por empresa
        if company and not getattr(self.request.user, 'is_superuser', False):
            return qs.filter(receipt__company=company)
        
        return qs

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST['action']
        try:
            if action == 'search':
                data = []
                start_date = request.POST['start_date']
                end_date = request.POST['end_date']
                receipt = request.POST['receipt']
                filters = Q()
                if len(start_date) and len(end_date):
                    filters &= Q(date_joined__range=[start_date, end_date])
                if len(receipt):
                    filters &= Q(receipt_id=receipt)
                for i in self.get_queryset().filter(filters):
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


class ReceiptErrorDeleteView(GroupPermissionMixin, CompanyQuerysetMixin, DeleteView):
    model = ReceiptError
    template_name = 'delete.html'
    success_url = reverse_lazy('receipt_error_list')
    permission_required = 'delete_receipt_error'

    def get_queryset(self):
        """Filtra los errores por la empresa del usuario a través de receipt.company"""
        qs = super().get_queryset()
        company = self.get_company()
        
        # Si hay empresa y el usuario no es superusuario, filtrar por empresa
        if company and not getattr(self.request.user, 'is_superuser', False):
            return qs.filter(receipt__company=company)
        
        return qs

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
