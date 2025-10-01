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
from core.subscription.models import check_quota_limits


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


def get_customer_group():
    """Obtiene (o crea) el grupo válido para clientes finales."""
    group_setting = getattr(settings, 'GROUPS', {}).get('customer') if hasattr(settings, 'GROUPS') else None
    candidate = None

    def is_valid(group: Group) -> bool:
        return group is not None and 'cliente' in group.name.lower()

    if isinstance(group_setting, int):
        candidate = Group.objects.filter(pk=group_setting).first()
        if not is_valid(candidate):
            candidate = None
    elif isinstance(group_setting, str):
        candidate = Group.objects.filter(name__iexact=group_setting).first()
        if not is_valid(candidate):
            candidate = None

    if candidate is None:
        for name in ['Cliente', 'Cliente final', 'Customer']:
            candidate = Group.objects.filter(name__iexact=name).first()
            if is_valid(candidate):
                break

    if candidate is None:
        candidate = Group.objects.create(name='Cliente')

    return candidate


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
            pass

    def create_customer_user(self, form_user, customer_dni):
        temp_user = form_user.save(commit=False)
        raw_password = (customer_dni or '').strip() or self.generate_password()
        from core.user.models import User  # import local para evitar ciclos
        user = User.objects.create_user(username=customer_dni, email=temp_user.email, password=raw_password)
        user.names = temp_user.names
        if temp_user.image:
            user.image = temp_user.image
        user.is_superuser = False
        user.is_staff = False
        user.save(update_fields=['names', 'image', 'is_superuser', 'is_staff'])
        # Asignar grupo cliente garantizado
        user.groups.set([get_customer_group()])
        user.is_superuser = False
        user.is_staff = False
        user.save(update_fields=['is_superuser', 'is_staff'])
        return user, raw_password


    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST['action']
        try:
            if action == 'add':
                # Verificar cuotas antes de crear
                quota_check = check_quota_limits(request.user, 'customer')
                if not quota_check['can_create']:
                    data['error'] = quota_check['message']
                else:
                    with transaction.atomic():
                        form1 = self.get_form_user()
                        # Pasar compañía al formulario para validación de unicidad por tenant
                        form2 = self.get_form(form_class=None)
                        form2 = self.form_class(self.request.POST, company=getattr(request, 'company', None))
                        if form1.is_valid() and form2.is_valid():
                            raw_password = None
                            # Reutilizar usuario si ya existe por username (dni/ruc)
                            from core.user.models import User
                            username = form2.cleaned_data['dni']
                            user = User.objects.filter(username=username).first()
                            user_is_new = False
                            if not user:
                                try:
                                    user, raw_password = self.create_customer_user(form1, username)
                                    user_is_new = True
                                except Exception as e:
                                    data['error'] = f'Error creando usuario cliente: {e}'
                                    raise
                            else:
                                # Actualizar nombres e imagen si se proporcionan, pero no cambiar contraseña ni privilegios
                                temp_user = form1.save(commit=False)
                                if temp_user.names:
                                    user.names = temp_user.names
                                if temp_user.image:
                                    user.image = temp_user.image
                                if temp_user.email:
                                    user.email = temp_user.email
                                user.is_superuser = False
                                user.is_staff = False
                                user.save(update_fields=['names', 'image', 'email', 'is_superuser', 'is_staff'])
                                try:
                                    user.groups.set([get_customer_group()])
                                except Exception:
                                    pass
                            # Crear Customer
                            form_customer = form2.save(commit=False)
                            form_customer.user = user
                            # Asignar la compañía del request
                            form_customer.company = getattr(request, 'company', None)
                            if not form_customer.company:
                                data['error'] = 'No se pudo obtener la compañía. Contacta al administrador.'
                                raise Exception('No company associated')
                            form_customer.save()
                            data = form_customer.as_dict()
                            # Enviar email solo si es un usuario recién creado
                            if user_is_new and raw_password:
                                self.send_credentials_email(user, raw_password)
                        else:
                            invalids = {}
                            if not form1.is_valid():
                                invalids['user_form'] = form1.errors
                            if not form2.is_valid():
                                invalids['customer_form'] = form2.errors
                            data['error'] = invalids
            elif action == 'validate_data':
                field = request.POST['field']
                filters = Q()
                # Restringir por compañía actual
                filters &= Q(company=getattr(request, 'company', None))
                if field == 'dni':
                    ident = request.POST['dni']
                    if len(ident) == 10:
                        filters &= Q(dni__iexact=ident)
                    elif len(ident) == 13:
                        filters &= Q(ruc__iexact=ident)
                    else:
                        data['valid'] = False
                        return HttpResponse(json.dumps(data), content_type='application/json')
                data['valid'] = not self.model.objects.filter(filters).exists() if filters.children else True
            elif action == 'search_ruc_in_sri':
                
                ruc = request.POST['dni']
                print(ruc)
                data = SRI().search_ruc_in_sri(ruc=ruc)
                print(data)
                if not data.get('razonSocial'):
                    data['error'] = 'No se encontró información en SRI.'
                    return HttpResponse(json.dumps(data), content_type='application/json')
                data.update({
                    'business_name': data.get('razonSocial', ''),
                    'commercial_name': data.get('razonSocial', ''),
                    'tradename': data.get('razonSocial', ''),
                    'is_business': True,
                })
                return HttpResponse(json.dumps(data), content_type="application/json")

            elif action == 'check_quota':
                
                quota_check = check_quota_limits(request.user, 'customer')
                data = quota_check
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
        
        # Agregar información de cuotas
        quota_check = check_quota_limits(self.request.user, 'customer')
        context['quota_info'] = quota_check
        
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
                    form2 = self.form_class(self.request.POST, instance=self.get_object(), company=getattr(request, 'company', None))
                    if form1.is_valid() and form2.is_valid():
                        user = form1.save(commit=False)
                        # Asegurar que no se eleve privilegios por edición
                        user.is_superuser = False
                        user.is_staff = False
                        user.save()
                        # Mantener sólo grupo cliente
                        try:
                            user.groups.set([get_customer_group()])
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
                filters &= Q(company=getattr(request, 'company', None))
                if field == 'dni':
                    ident = request.POST['dni']
                    if len(ident) == 10:
                        filters &= Q(dni__iexact=ident)
                    elif len(ident) == 13:
                        filters &= Q(ruc__iexact=ident)
                    else:
                        data['valid'] = False
                        return HttpResponse(json.dumps(data), content_type='application/json')
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
        # Pasar compañía al formulario para validaciones
        form = self.form_class(instance=self.get_object(), company=getattr(self.request, 'company', None))
        # Campos deshabilitados únicamente: dni (identificador principal)
        for field in ['dni']:
            if field in form.fields:
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
                    form2 = self.form_class(self.request.POST, instance=self.get_object(), company=getattr(request, 'company', None))
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
                filters &= Q(company=getattr(request, 'company', None))
                if field == 'dni':
                    ident = request.POST['dni']
                    if len(ident) == 10:
                        filters &= Q(dni__iexact=ident)
                    elif len(ident) == 13:
                        filters &= Q(ruc__iexact=ident)
                    else:
                        data['valid'] = False
                        return HttpResponse(json.dumps(data), content_type='application/json')
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
