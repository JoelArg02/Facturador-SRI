import json

from django.http import HttpResponse
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView, DeleteView, ListView

from core.pos.forms import Receipt, ReceiptForm
from core.security.mixins import GroupPermissionMixin, AutoAssignCompanyMixin, CompanyQuerysetMixin


class ReceiptListView(GroupPermissionMixin, CompanyQuerysetMixin, ListView):
    model = Receipt
    template_name = 'receipt/list.html'
    permission_required = 'view_receipt'

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST['action']
        try:
            if action == 'search':
                data = []
                # CompanyQuerysetMixin.get_queryset() ya filtra por company
                for i in self.get_queryset():
                    data.append(i.as_dict())
            else:
                data['error'] = 'No ha seleccionado ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Listado de {self.model._meta.verbose_name_plural}'
        context['create_url'] = reverse_lazy('receipt_create')
        return context


class ReceiptCreateView(AutoAssignCompanyMixin, GroupPermissionMixin, CompanyQuerysetMixin, CreateView):
    model = Receipt
    template_name = 'receipt/create.html'
    form_class = ReceiptForm
    success_url = reverse_lazy('receipt_list')
    permission_required = 'add_receipt'

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST['action']
        try:
            if action == 'add':
                form = self.get_form()
                if form.is_valid():
                    # Guardar y obtener instancia real, con company auto-asignada
                    obj = form.save_instance(commit=True)
                    data = {
                        'id': obj.pk,
                        'name': obj.name if hasattr(obj, 'name') else str(obj),
                        'voucher_type': obj.voucher_type,
                        'establishment_code': obj.establishment_code,
                        'issuing_point_code': obj.issuing_point_code,
                        'sequence': obj.sequence
                    }
                else:
                    data['error'] = form.errors
            elif action == 'validate_data':
                voucher_type = request.POST['voucher_type']
                establishment_code = request.POST['establishment_code']
                issuing_point_code = request.POST['issuing_point_code']
                qs = self.get_queryset()
                data['valid'] = not qs.filter(voucher_type=voucher_type, establishment_code=establishment_code, issuing_point_code=issuing_point_code).exists() if len(voucher_type) and len(issuing_point_code) and len(establishment_code) else True
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


class ReceiptUpdateView(AutoAssignCompanyMixin, GroupPermissionMixin, CompanyQuerysetMixin, UpdateView):
    model = Receipt
    template_name = 'receipt/create.html'
    form_class = ReceiptForm
    success_url = reverse_lazy('receipt_list')
    permission_required = 'change_receipt'

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST['action']
        try:
            if action == 'edit':
                form = self.get_form()
                if form.is_valid():
                    obj = form.save_instance(commit=True)
                    data = {
                        'id': obj.pk,
                        'name': obj.name if hasattr(obj, 'name') else str(obj),
                        'voucher_type': obj.voucher_type,
                        'establishment_code': obj.establishment_code,
                        'issuing_point_code': obj.issuing_point_code,
                        'sequence': obj.sequence
                    }
                else:
                    data['error'] = form.errors
            elif action == 'validate_data':
                voucher_type = request.POST['voucher_type']
                establishment_code = request.POST['establishment_code']
                issuing_point_code = request.POST['issuing_point_code']
                qs = self.get_queryset()
                data['valid'] = not qs.filter(voucher_type=voucher_type, establishment_code=establishment_code, issuing_point_code=issuing_point_code).exclude(id=self.object.id).exists() if len(voucher_type) and len(issuing_point_code) and len(establishment_code) else True
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


class ReceiptDeleteView(GroupPermissionMixin, CompanyQuerysetMixin, DeleteView):
    model = Receipt
    template_name = 'delete.html'
    success_url = reverse_lazy('receipt_list')
    permission_required = 'delete_receipt'

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
