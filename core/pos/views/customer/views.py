import json
from django.contrib.auth.models import Group
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView, DeleteView, ListView
from config import settings
from core.pos.forms import CustomerForm, CustomerUserForm
from core.pos.models import Customer
from core.pos.utilities.sri import SRI
from core.security.mixins import GroupPermissionMixin, GroupModuleMixin
from core.subscription.models import check_quota_limits
from core.user.models import User


class CustomerListView(GroupPermissionMixin, ListView):
    model = Customer
    template_name = 'customer/list.html'
    permission_required = 'view_customer'

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST.get('action')
        try:
            if action == 'search':
                data = []
                user_company = getattr(request.user, 'company', None)
                queryset = self.model.objects.filter(company=user_company) if user_company else self.model.objects.none()
                for obj in queryset:
                    data.append(obj.as_dict())
            else:
                data['error'] = 'No ha seleccionado ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Listado de {self.model._meta.verbose_name_plural}'
        context['create_url'] = reverse_lazy('customer_create')
        
        quota_info = check_quota_limits(self.request.user, 'customer')
        context['quota_info'] = quota_info
        
        return context


class CustomerCreateView(GroupPermissionMixin, CreateView):
    model = Customer
    template_name = 'customer/create.html'
    form_class = CustomerForm
    success_url = reverse_lazy('customer_list')
    permission_required = 'add_customer'

    def get_form_user(self):
        form = CustomerUserForm(self.request.POST or None, self.request.FILES or None)
        return form

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST.get('action')
        try:
            if action == 'add':
                quota_check = check_quota_limits(request.user, 'customer')
                if not quota_check['can_create']:
                    data['error'] = quota_check['message']
                    return HttpResponse(json.dumps(data), content_type='application/json')
                
                with transaction.atomic():
                    form1 = self.get_form_user()
                    form2 = self.form_class(request.POST, request.FILES, request=request)

                    if form1.is_valid() and form2.is_valid():
                        dni = form2.cleaned_data.get('dni')
                        
                        # Verificar si ya existe un usuario con este username (dni)
                        existing_user = User.objects.filter(username=dni).first()
                        
                        if existing_user:
                            # Reutilizar el usuario existente
                            user = existing_user
                            # Actualizar solo el nombre si es diferente
                            new_names = form1.cleaned_data.get('names')
                            if new_names and new_names != user.names:
                                user.names = new_names
                            # Actualizar email si es diferente y está presente
                            new_email = form1.cleaned_data.get('email')
                            if new_email and new_email != user.email:
                                user.email = new_email
                            # Actualizar imagen si se proporciona una nueva
                            if form1.cleaned_data.get('image'):
                                user.image = form1.cleaned_data.get('image')
                            user.save()
                        else:
                            # Crear nuevo usuario
                            user = form1.save(commit=False)
                            user.username = dni
                            user.set_password(user.username)
                            user.is_staff = False
                            user.is_superuser = False
                            user.is_active = True
                            user.save()

                        user.groups.clear()

                        customer_group_id = settings.GROUPS.get('customer')

                        try:
                            customer_group = Group.objects.get(pk=customer_group_id)
                            user.groups.add(customer_group)
                        except Group.DoesNotExist:
                            pass

                        customer = form2.save(commit=False)
                        customer.user = user
                        customer.company = getattr(request.user, 'company', None)
                        customer.save()

                        data = customer.as_dict()


                    else:
                        data['error'] = form1.errors if not form1.is_valid() else form2.errors
            elif action == 'validate_data':
                field = request.POST.get('field')
                filters = Q()
                if field == 'dni':
                    filters &= Q(dni__iexact=request.POST.get('dni'))
                user_company = getattr(request.user, 'company', None)
                if user_company:
                    filters &= Q(company=user_company)
                data['valid'] = not self.model.objects.filter(filters).exists() if filters.children else True
            elif action == 'search_ruc_in_sri':
                data = SRI().search_ruc_in_sri(ruc=request.POST.get('dni'))
            else:
                data['error'] = 'No ha seleccionado ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
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
        return CustomerUserForm(self.request.POST or None, self.request.FILES or None, instance=self.object.user)

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST.get('action')
        try:
            if action == 'edit':
                with transaction.atomic():
                    form1 = self.get_form_user()
                    form2 = self.form_class(request.POST, request.FILES, instance=self.object, request=request)
                    if form1.is_valid() and form2.is_valid():
                        user = form1.save(commit=False)
                        user.save()
                        customer = form2.save(commit=False)
                        customer.user = user
                        customer.company = getattr(request.user, 'company', None)
                        customer.save()
                        data = customer.as_dict()
                    else:
                        data['error'] = form1.errors if not form1.is_valid() else form2.errors
            elif action == 'validate_data':
                field = request.POST.get('field')
                filters = Q()
                if field == 'dni':
                    filters &= Q(dni__iexact=request.POST.get('dni'))
                user_company = getattr(request.user, 'company', None)
                if user_company:
                    filters &= Q(company=user_company)
                data['valid'] = not self.model.objects.filter(filters).exclude(id=self.object.id).exists() if filters.children else True
            elif action == 'search_ruc_in_sri':
                data = SRI().search_ruc_in_sri(ruc=request.POST.get('dni'))
            else:
                data['error'] = 'No ha seleccionado ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Edición de un {self.model._meta.verbose_name}'
        context['list_url'] = self.success_url
        context['action'] = 'edit'
        context['frmUser'] = self.get_form_user()
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
        return getattr(self.request.user, 'customers', None).first()

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        for field in ['dni', 'identification_type']:
            if field in form.fields:
                form.fields[field].disabled = True
        return form

    def get_form_user(self):
        return CustomerUserForm(self.request.POST or None, self.request.FILES or None, instance=self.request.user)

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST.get('action')
        try:
            if action == 'edit':
                with transaction.atomic():
                    form1 = self.get_form_user()
                    form2 = self.form_class(request.POST, request.FILES, instance=self.object, request=request)
                    if form1.is_valid() and form2.is_valid():
                        user = form1.save(commit=False)
                        user.save()
                        customer = form2.save(commit=False)
                        customer.user = user
                        customer.company = getattr(request.user, 'company', None)
                        customer.save()
                        data = customer.as_dict()
                    else:
                        data['error'] = form1.errors if not form1.is_valid() else form2.errors
            elif action == 'validate_data':
                field = request.POST.get('field')
                filters = Q()
                if field == 'dni':
                    filters &= Q(dni__iexact=request.POST.get('dni'))
                user_company = getattr(request.user, 'company', None)
                if user_company:
                    filters &= Q(company=user_company)
                data['valid'] = not self.model.objects.filter(filters).exclude(id=self.object.id).exists() if filters.children else True
            else:
                data['error'] = 'No ha seleccionado ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Edición de una cuenta de {self.model._meta.verbose_name}'
        context['list_url'] = self.success_url
        context['action'] = 'edit'
        context['frmUser'] = self.get_form_user()
        return context
