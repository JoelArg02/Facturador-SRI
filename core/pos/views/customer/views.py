import json

from django.contrib.auth.models import Group
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView, DeleteView, ListView

from config import settings
from core.pos.forms import CustomerForm, Customer, CustomerUserForm
from core.pos.utilities.sri import SRI
from core.security.mixins import GroupModuleMixin, GroupPermissionMixin


class CustomerListView(GroupPermissionMixin, ListView):
    model = Customer
    template_name = 'customer/list.html'
    permission_required = 'view_customer'

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST['action']
        try:
            if action == 'search':
                data = []
                for i in self.model.objects.filter():
                    data.append(i.as_dict())
            else:
                data['error'] = 'No ha seleccionado ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Listado de {self.model._meta.verbose_name_plural}'
        context['create_url'] = reverse_lazy('customer_create')
        return context


class CustomerCreateView(GroupPermissionMixin, CreateView):
    model = Customer
    template_name = 'customer/create.html'
    form_class = CustomerForm
    success_url = reverse_lazy('customer_list')
    permission_required = 'add_customer'

    def get_form_user(self):
        form = CustomerUserForm()
        if self.request.POST or self.request.FILES:
            form = CustomerUserForm(self.request.POST, self.request.FILES)
        return form

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST['action']
        try:
            if action == 'add':
                with transaction.atomic():
                    form1 = self.get_form_user()
                    form2 = self.get_form()
                    if form1.is_valid() and form2.is_valid():
                        user = form1.save(commit=False)
                        user.username = form2.cleaned_data['dni']
                        user.set_password(user.username)
                        user.save()
                        user.groups.add(Group.objects.get(pk=settings.GROUPS['customer']))
                        form_customer = form2.save(commit=False)
                        form_customer.user = user
                        form_customer.save()
                        data = form_customer.as_dict()
                    else:
                        if not form1.is_valid():
                            data['error'] = form1.errors
                        elif not form2.is_valid():
                            data['error'] = form2.errors
            elif action == 'validate_data':
                field = request.POST['field']
                filters = Q()
                if field == 'dni':
                    filters &= Q(dni__iexact=request.POST['dni'])
                data['valid'] = not self.model.objects.filter(filters).exists() if filters.children else True
            elif action == 'search_ruc_in_sri':
                data = SRI().search_ruc_in_sri(ruc=request.POST['dni'])
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
        context['frmUser'] = self.get_form_user()
        return context


class CustomerUpdateView(GroupPermissionMixin, UpdateView):
    model = Customer
    template_name = 'customer/create.html'
    form_class = CustomerForm
    success_url = reverse_lazy('customer_list')
    permission_required = 'change_customer'

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().dispatch(request, *args, **kwargs)

    def get_form_user(self):
        form = CustomerUserForm(instance=self.request.user)
        if self.request.POST or self.request.FILES:
            form = CustomerUserForm(self.request.POST, self.request.FILES, instance=self.object.user)
        return form

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST['action']
        try:
            if action == 'edit':
                with transaction.atomic():
                    form1 = self.get_form_user()
                    form2 = self.get_form()
                    if form1.is_valid() and form2.is_valid():
                        user = form1.save(commit=False)
                        user.save()
                        form_customer = form2.save(commit=False)
                        form_customer.user = user
                        form_customer.save()
                    else:
                        if not form1.is_valid():
                            data['error'] = form1.errors
                        elif not form2.is_valid():
                            data['error'] = form2.errors
            elif action == 'validate_data':
                field = request.POST['field']
                filters = Q()
                if field == 'dni':
                    filters &= Q(dni__iexact=request.POST['dni'])
                data['valid'] = not self.model.objects.filter(filters).exclude(id=self.object.id).exists() if filters.children else True
            elif action == 'search_ruc_in_sri':
                data = SRI().search_ruc_in_sri(ruc=request.POST['dni'])
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
        context['frmUser'] = CustomerUserForm(instance=self.object.user)
        return context


class CustomerDeleteView(GroupPermissionMixin, DeleteView):
    model = Customer
    template_name = 'delete.html'
    success_url = reverse_lazy('customer_list')
    permission_required = 'delete_customer'

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


class CustomerUpdateProfileView(GroupModuleMixin, UpdateView):
    model = Customer
    template_name = 'customer/profile.html'
    form_class = CustomerForm
    success_url = settings.LOGIN_REDIRECT_URL

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        return self.request.user.customer

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        for field in ['dni', 'identification_type', 'send_email_invoice']:
            form.fields[field].disabled = True
            form.fields[field].required = False
        return form

    def get_form_user(self):
        form = CustomerUserForm(instance=self.request.user)
        if self.request.POST or self.request.FILES:
            form = CustomerUserForm(self.request.POST, self.request.FILES, instance=self.request.user)
        for field in ['names']:
            form.fields[field].disabled = True
            form.fields[field].required = False
        return form

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST['action']
        try:
            if action == 'edit':
                with transaction.atomic():
                    form1 = self.get_form_user()
                    form2 = self.get_form()
                    if form1.is_valid() and form2.is_valid():
                        user = form1.save(commit=False)
                        user.save()
                        form_customer = form2.save(commit=False)
                        form_customer.user = user
                        form_customer.save()
                    else:
                        if not form1.is_valid():
                            data['error'] = form1.errors
                        elif not form2.is_valid():
                            data['error'] = form2.errors
            elif action == 'validate_data':
                field = request.POST['field']
                filters = Q()
                if field == 'dni':
                    filters &= Q(dni__iexact=request.POST['dni'])
                data['valid'] = not self.model.objects.filter(filters).exclude(id=self.object.id).exists() if filters.children else True
            else:
                data['error'] = 'No ha seleccionado ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context['title'] = f'Edición de una cuenta de {self.model._meta.verbose_name}'
        context['list_url'] = self.success_url
        context['action'] = 'edit'
        context['frmUser'] = self.get_form_user()
        return context
