import json
import secrets
import string
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from django.contrib.auth.models import Group
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView, DeleteView, ListView

from config import settings
from core.pos.forms import CustomerForm, Customer, CustomerUserForm
from core.pos.utilities.sri import SRI
from core.security.mixins import GroupModuleMixin, GroupPermissionMixin, CompanyQuerysetMixin


class CustomerListView(GroupPermissionMixin, CompanyQuerysetMixin, ListView):
    model = Customer
    template_name = 'customer/list.html'
    permission_required = 'view_customer'

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST['action']
        try:
            if action == 'search':
                data = []
                qs = self.get_queryset()
                for i in qs:
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

    def generate_password(self, length=10):
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))


    def send_credentials_email(self, user, raw_password):
        if not user.email:
            return

        try:
            message = MIMEMultipart('alternative')
            message['Subject'] = 'Credenciales de acceso - OptimusPos Facturación'
            message['From'] = settings.EMAIL_HOST_USER
            message['To'] = user.email

            # Texto plano (fallback)
            text_content = (
                f"Hola {user.names},\n\n"
                f"Se ha creado su cuenta en OptimusPos Facturación.\n\n"
                f"Usuario: {user.username}\n"
                f"Contraseña: {raw_password}\n"
                f"URL: {getattr(settings, 'SITE_URL', '')}\n\n"
                f"Por favor cambie su contraseña después de iniciar sesión."
            )

            # HTML con diseño
            html_content = f"""
            <html>
            <body style="font-family:Arial, sans-serif; background:#f4f4f7; padding:20px;">
                <table style="max-width:600px; margin:auto; background:#ffffff; border-radius:8px; overflow:hidden;
                            box-shadow:0 2px 6px rgba(0,0,0,0.1);">
                    <tr>
                        <td style="background:#2b6cb0; color:#fff; padding:20px; text-align:center;">
                            <h2 style="margin:0;">OptimusPos Facturación</h2>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding:30px; color:#2d3748;">
                            <p style="font-size:16px;">Hola <strong>{user.names}</strong>,</p>
                            <p style="font-size:16px;">
                                Se ha creado su cuenta para acceder al portal de <strong>OptimusPos Facturación</strong>.
                            </p>
                            <p style="font-size:16px;">
                                <strong>Usuario:</strong> {user.username}<br>
                                <strong>Contraseña:</strong> {raw_password}<br>
                                <strong>URL:</strong> <a href="{getattr(settings, 'SITE_URL', '#')}" 
                                style="color:#2b6cb0;text-decoration:none;">{getattr(settings, 'SITE_URL', '')}</a>
                            </p>
                            <p style="font-size:16px;">
                                Por favor cambie su contraseña después de iniciar sesión.
                            </p>
                        </td>
                    </tr>
                    <tr>
                        <td style="background:#edf2f7; color:#4a5568; padding:15px; text-align:center; font-size:12px;">
                            © {user.date_joined.year} OptimusPos Facturación
                        </td>
                    </tr>
                </table>
            </body>
            </html>
            """

            message.attach(MIMEText(text_content, 'plain'))
            message.attach(MIMEText(html_content, 'html'))

            # Envío directo por SSL en puerto 465
            server = smtplib.SMTP_SSL(settings.EMAIL_HOST, 465)
            server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
            server.sendmail(settings.EMAIL_HOST_USER, [user.email], message.as_string())
            server.quit()

        except Exception:
            # Se silencian errores; puedes manejar logging si lo necesitas
            pass


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
                        raw_password = self.generate_password()
                        user.set_password(raw_password)
                        # Quitar privilegios peligrosos explícitamente
                        user.is_superuser = False
                        user.is_staff = False
                        user.save()
                        # Limpiar grupos existentes (si por algún motivo hereda)
                        user.groups.clear()
                        # Asignar grupo cliente (crear si no existe el id configurado)
                        try:
                            group_id = settings.GROUPS.get('customer')
                            cust_group = None
                            if group_id:
                                cust_group = Group.objects.filter(pk=group_id).first()
                            if cust_group is None:
                                # fallback: buscar por nombre 'cliente' o crear
                                cust_group = Group.objects.filter(name__iexact='cliente').first()
                                if cust_group is None:
                                    cust_group = Group.objects.create(name='cliente')
                            user.groups.add(cust_group)
                        except Exception as e:
                            print(f"No se pudo asignar/crear el grupo cliente: {e}")
                        form_customer = form2.save(commit=False)
                        form_customer.user = user
                        # Asignar compañía automáticamente si el request la tiene
                        company = getattr(request, 'company', None)
                        if company:
                            form_customer.company = company
                        form_customer.save()
                        data = form_customer.as_dict()
                        # Enviar email con credenciales
                        self.send_credentials_email(user, raw_password)
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
                        # Asegurar que no se eleve privilegios por edición
                        user.is_superuser = False
                        user.is_staff = False
                        user.save()
                        # Mantener sólo grupo cliente
                        try:
                            group_id = settings.GROUPS.get('customer')
                            cust_group = None
                            if group_id:
                                cust_group = Group.objects.filter(pk=group_id).first()
                            if cust_group is None:
                                cust_group = Group.objects.filter(name__iexact='cliente').first()
                            if cust_group:
                                user.groups.set([cust_group])
                        except Exception as e:
                            print(f"No se pudo reafirmar grupo cliente en edición: {e}")
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
