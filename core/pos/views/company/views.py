import json

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import pkcs12
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import FormView, UpdateView

from config import settings
from core.pos.forms import CompanyForm, Company, CompanyOnboardingForm
from core.security.mixins import GroupPermissionMixin


class CompanySelfUpdateView(LoginRequiredMixin, UpdateView):
    template_name = 'company/create.html'
    form_class = CompanyForm
    model = Company
    success_url = settings.LOGIN_REDIRECT_URL

    def get_user_company(self):
        return getattr(self.request.user, 'owned_company', None)

    def dispatch(self, request, *args, **kwargs):
        print('[CompanySelfUpdateView] START dispatch')
        print(f"[CompanySelfUpdateView] user.id={getattr(request.user,'id',None)} username={getattr(request.user,'username',None)} is_auth={request.user.is_authenticated}")
        owned = getattr(request.user, 'owned_company', None)
        assigned = getattr(request.user, 'company', None)
        print(f"[CompanySelfUpdateView] owned_company.id={getattr(owned,'id',None)} owner_id={getattr(owned,'owner_id',None)}")
        print(f"[CompanySelfUpdateView] user.company.id={getattr(assigned,'id',None)}")
        company = self.get_user_company()
        print(f"[CompanySelfUpdateView] get_user_company.id={getattr(company,'id',None)}")
        if company is None:
            print('[CompanySelfUpdateView] No owned_company → redirect to onboarding')
            messages.info(request, 'Aún no tienes una compañía propia. Completa el registro inicial.')
            return redirect('company_onboarding')
        # Validación explícita de propiedad
        if getattr(company, 'owner_id', None) != request.user.id and not request.user.is_superuser:
            print(f"[CompanySelfUpdateView] DENY: company.owner_id={getattr(company,'owner_id',None)} != user.id={request.user.id} and not superuser")
            messages.error(request, 'Solo el dueño de la compañía puede editar sus datos.')
            return redirect(settings.LOGIN_REDIRECT_URL)
        print('[CompanySelfUpdateView] OK owner, continue')
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        # Ya se validó en dispatch que existe; devolverla
        return self.get_user_company()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Mi empresa'
        context['list_url'] = self.success_url
        context['action'] = 'create_or_edit'
        return context

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Ocultar y proteger el campo owner para usuarios que no son superusuario
        if not getattr(self.request.user, 'is_superuser', False) and 'owner' in form.fields:
            form.fields['owner'].widget = form.fields['owner'].hidden_widget()
            form.fields['owner'].required = False
        return form

    def form_valid(self, form):
        # Asegurar que no puedan cambiar el owner vía POST si no son superusuarios
        if not getattr(self.request.user, 'is_superuser', False):
            try:
                current_owner = self.get_object().owner
                form.instance.owner = current_owner
            except Exception:
                form.instance.owner = self.request.user
        return super().form_valid(form)

    def post(self, request, *args, **kwargs):
        """Replica el flujo AJAX del CompanyUpdateView para compatibilidad con company/js/form.js"""
        data = {}
        action = request.POST.get('action')
        try:
            if action == 'create_or_edit':
                instance = self.get_object()
                if instance.pk:
                    form = CompanyForm(request.POST, request.FILES, instance=instance)
                else:
                    form = CompanyForm(request.POST, request.FILES)
                data = form.save()
            elif action == 'load_certificate':
                instance = self.get_object()
                electronic_signature_key = request.POST.get('electronic_signature_key', '')
                archive = None
                if 'certificate' in request.FILES:
                    archive = request.FILES['certificate'].file
                elif getattr(instance, 'pk', None) is not None and instance.electronic_signature:
                    archive = open(instance.electronic_signature.path, 'rb')
                if archive:
                    with archive as file:
                        private_key, certificate, additional_certificates = pkcs12.load_key_and_certificates(
                            file.read(), electronic_signature_key.encode()
                        )
                        for s in certificate.subject:
                            data[s.oid._name] = s.value
                        public_key = certificate.public_key().public_bytes(
                            encoding=serialization.Encoding.PEM,
                            format=serialization.PublicFormat.SubjectPublicKeyInfo
                        ).decode('utf-8')
                        data['public_key'] = public_key
            else:
                # Si no viene action, degradar a comportamiento normal de UpdateView
                return super().post(request, *args, **kwargs)
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')


class CompanyOwnerEditView(LoginRequiredMixin, UpdateView):
    """Vista dedicada para dueños, sin campos de configuración de correo."""
    template_name = 'company/owner_edit.html'
    model = Company
    success_url = settings.LOGIN_REDIRECT_URL

    # Campos permitidos (sin SMTP ni correo saliente)
    fields = [
        'ruc', 'company_name', 'commercial_name', 'main_address', 'establishment_address',
        'establishment_code', 'issuing_point_code', 'special_taxpayer', 'obligated_accounting',
        'image', 'environment_type', 'emission_type', 'retention_agent', 'regimen_rimpe', 'mobile',
        'phone', 'email', 'website', 'description', 'tax', 'tax_percentage', 'electronic_signature',
        'electronic_signature_key'
    ]

    def get_object(self, queryset=None):
        company = getattr(self.request.user, 'owned_company', None)
        if company is None:
            return Company()
        return company

    def dispatch(self, request, *args, **kwargs):
        print('[CompanyOwnerEditView] START dispatch')
        company = getattr(request.user, 'owned_company', None)
        print(f"[CompanyOwnerEditView] owned_company.id={getattr(company,'id',None)} owner_id={getattr(company,'owner_id',None)} user.id={getattr(request.user,'id',None)}")
        if company is None:
            print('[CompanyOwnerEditView] No owned_company → redirect to onboarding')
            messages.info(request, 'Aún no tienes una compañía propia. Completa el registro inicial.')
            return redirect('company_onboarding')
        if company.owner_id != request.user.id and not request.user.is_superuser:
            print('[CompanyOwnerEditView] DENY not owner')
            messages.error(request, 'Solo el dueño de la compañía puede editar sus datos.')
            return redirect(settings.LOGIN_REDIRECT_URL)
        print('[CompanyOwnerEditView] OK owner, continue')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        # Blindar owner
        if not getattr(self.request.user, 'is_superuser', False):
            form.instance.owner = self.request.user
        return super().form_valid(form)


class CompanyUpdateView(GroupPermissionMixin, UpdateView):
    template_name = 'company/create.html'
    form_class = CompanyForm
    model = Company
    permission_required = 'change_company'
    success_url = settings.LOGIN_REDIRECT_URL

    # Sin override de dispatch; se mantiene el gate por permisos tal como estaba

    def get_object(self, queryset=None):
        return Company.objects.first() or Company()

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST['action']
        try:
            if action == 'create_or_edit':
                instance = self.get_object()
                if instance.pk:
                    form = CompanyForm(request.POST, request.FILES, instance=instance)
                else:
                    form = CompanyForm(request.POST, request.FILES)
                data = form.save()
            elif action == 'load_certificate':
                instance = self.get_object()
                electronic_signature_key = request.POST['electronic_signature_key']
                archive = None
                if 'certificate' in request.FILES:
                    archive = request.FILES['certificate'].file
                elif instance.pk is not None:
                    archive = open(instance.electronic_signature.path, 'rb')
                if archive:
                    with archive as file:
                        private_key, certificate, additional_certificates = pkcs12.load_key_and_certificates(file.read(), electronic_signature_key.encode())
                        for s in certificate.subject:
                            data[s.oid._name] = s.value
                        public_key = certificate.public_key().public_bytes(encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo).decode('utf-8')
                        data['public_key'] = public_key
            else:
                data['error'] = 'No ha seleccionado ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context['title'] = f'Configuración de la {self.model._meta.verbose_name}'
        context['list_url'] = self.success_url
        context['action'] = 'create_or_edit'
        return context


class CompanyOnboardingView(GroupPermissionMixin, FormView):
    template_name = 'company/onboarding.html'
    form_class = CompanyOnboardingForm
    success_url = settings.LOGIN_REDIRECT_URL
    permission_required = None

    def dispatch(self, request, *args, **kwargs):
        print("──────────────────────────────────────────────────────────────")
        print("[CompanyOnboardingView] → dispatch()")
        print(f"Usuario: {request.user} | Autenticado: {request.user.is_authenticated}")
        if request.user.is_authenticated and hasattr(request.user, 'company') and request.user.company is not None:
            print(f"Ya tiene una compañía asignada → Redirigiendo a {self.success_url}")
            return redirect(self.success_url)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        print("──────────────────────────────────────────────────────────────")
        print("[CompanyOnboardingView] → form_valid() iniciado")
        print(f"Usuario: {self.request.user} (ID: {self.request.user.id})")

        try:
            # Verificar si el usuario ya tiene compañía
            if hasattr(self.request.user, 'owned_company') and self.request.user.owned_company:
                print("[ERROR] El usuario ya posee una compañía registrada")
                form.add_error(None, "Ya tienes una compañía registrada.")
                return self.form_invalid(form)

            # Guardar el formulario (soporte para dict o instancia)
            result = form.save(commit=False)
            print(f"[DEBUG] Resultado de form.save(): tipo = {type(result)}")

            if isinstance(result, dict):
                print(f"[DEBUG] Contenido de result: {json.dumps(result, default=str)}")
                company = result.get('instance')
                if not company:
                    print("[ERROR] El formulario devolvió un dict sin 'instance'")
                    form.add_error(None, "Error interno: el formulario no devolvió la instancia de la compañía.")
                    return self.form_invalid(form)
            else:
                company = result

            print(f"[OK] Se obtuvo instancia de Company: {company}")

            # Validar campos obligatorios antes de guardar
            missing_fields = [f.name for f in company._meta.fields if getattr(company, f.name) in (None, '', []) and not f.null and not f.blank]
            if missing_fields:
                print(f"[WARNING] Campos requeridos sin valor: {missing_fields}")

            # Asignar propietario
            company.owner = self.request.user
            print(f"[OK] Owner asignado: {company.owner}")

            # Guardar en base de datos
            company.save()
            print(f"[OK] Compañía guardada con ID: {company.id}")

            # Relacionar usuario con la compañía
            self.request.user.company = company
            self.request.user.save()
            print(f"[OK] Usuario actualizado → company_id={self.request.user.company_id}")

            # Verificación final
            print("[VERIFICACIÓN FINAL]")
            print(f"Company.owner → {company.owner}")
            print(f"User.company → {self.request.user.company}")
            print(f"User.owned_company → {getattr(self.request.user, 'owned_company', 'N/A')}")
            print("──────────────────────────────────────────────────────────────")
            return redirect(self.success_url)

        except Exception as e:
            print("──────────────────────────────────────────────────────────────")
            print("[ERROR] Excepción en form_valid()")
            traceback.print_exc()
            form.add_error(None, f"Error al crear la compañía: {str(e)}")
            print("──────────────────────────────────────────────────────────────")
            return self.form_invalid(form)

    def form_invalid(self, form):
        print("──────────────────────────────────────────────────────────────")
        print("[CompanyOnboardingView] → form_invalid()")
        print("Errores de formulario:")
        for field, errors in form.errors.items():
            print(f" - {field}: {errors}")
        print("──────────────────────────────────────────────────────────────")
        return super().form_invalid(form)

    def post(self, request, *args, **kwargs):
        print("──────────────────────────────────────────────────────────────")
        print("[CompanyOnboardingView] → POST recibido")
        print(f"Datos del formulario: {json.dumps(request.POST.dict(), indent=2, ensure_ascii=False)}")
        print("──────────────────────────────────────────────────────────────")
        return super().post(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Configuración Inicial de la Compañía'
        context['action'] = 'create'
        return context

