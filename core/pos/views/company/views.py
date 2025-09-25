import json

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import pkcs12
from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import FormView, UpdateView

from config import settings
from core.pos.forms import CompanyForm, Company, CompanyOnboardingForm
from core.security.mixins import GroupPermissionMixin


class CompanyUpdateView(GroupPermissionMixin, UpdateView):
    template_name = 'company/create.html'
    form_class = CompanyForm
    model = Company
    permission_required = 'change_company'
    success_url = settings.LOGIN_REDIRECT_URL

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
    permission_required = None  # Se maneja solo por autenticación y lógica de owner

    def dispatch(self, request, *args, **kwargs):
        # Debug info
        print(f"[CompanyOnboardingView] Usuario: {request.user}, autenticado: {request.user.is_authenticated}")
        print(f"[CompanyOnboardingView] Tiene company: {hasattr(request.user, 'company')}")
        if hasattr(request.user, 'company'):
            print(f"[CompanyOnboardingView] Company actual: {request.user.company}")
        
        # Si el usuario ya tiene una compañía asignada, redirigimos (evitar duplicados)
        if request.user.is_authenticated and hasattr(request.user, 'company') and request.user.company is not None:
            print(f"[CompanyOnboardingView] Usuario ya tiene company, redirigiendo a {self.success_url}")
            return redirect(self.success_url)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        try:
            print("[CompanyOnboardingView] Iniciando form_valid")
            print(f"[CompanyOnboardingView] Usuario actual: {self.request.user} (ID: {self.request.user.id})")
            
            # Verificar si el usuario ya posee una compañía
            if hasattr(self.request.user, 'owned_company') and self.request.user.owned_company:
                print(f"[CompanyOnboardingView] Usuario ya posee una compañía: {self.request.user.owned_company}")
                form.add_error(None, "Ya tienes una compañía registrada.")
                return self.form_invalid(form)
            
            # Crear la compañía
            company = form.save(commit=False)
            company.owner = self.request.user
            print(f"[CompanyOnboardingView] Asignando owner: {self.request.user} (ID: {self.request.user.id})")
            
            # Guardar la compañía primero
            company.save()
            print(f"[CompanyOnboardingView] Compañía creada con ID: {company.id}")
            print(f"[CompanyOnboardingView] Owner asignado: {company.owner}")
            
            # Ahora asignar la compañía al usuario (relación ForeignKey)
            self.request.user.company = company
            self.request.user.save()
            print(f"[CompanyOnboardingView] Usuario actualizado. Company ID: {self.request.user.company_id}")
            
            # Verificar que las relaciones se establecieron correctamente
            print(f"[CompanyOnboardingView] Verificación final:")
            print(f"  - Company.owner: {company.owner}")
            print(f"  - User.company: {self.request.user.company}")
            print(f"  - User.owned_company: {getattr(self.request.user, 'owned_company', 'N/A')}")
            
            print(f"[CompanyOnboardingView] Redirigiendo a {self.success_url}")
            return redirect(self.success_url)
            
        except Exception as e:
            print(f"[CompanyOnboardingView] Error en form_valid: {e}")
            import traceback
            traceback.print_exc()
            
            # Agregar error al formulario para mostrarlo al usuario
            form.add_error(None, f"Error al crear la compañía: {str(e)}")
            return self.form_invalid(form)

    def form_invalid(self, form):
        print(f"[CompanyOnboardingView] Formulario inválido. Errores: {form.errors}")
        return super().form_invalid(form)

    def post(self, request, *args, **kwargs):
        print(f"[CompanyOnboardingView] POST recibido. Datos: {request.POST}")
        return super().post(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Configuración Inicial de la Compañía'
        context['action'] = 'create'
        return context
