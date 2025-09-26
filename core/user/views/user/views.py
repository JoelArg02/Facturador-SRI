import json

from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import Group
from django.db.models import Q
from django.forms import model_to_dict
from django.http import HttpResponseRedirect, HttpResponse
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView, DeleteView, ListView, FormView, View

from config import settings
from core.login.forms import UpdatePasswordForm
from core.security.form_handlers.helpers import update_form_fields_attributes
from core.security.mixins import GroupPermissionMixin, GroupModuleMixin, CompanyQuerysetMixin
from core.user.forms import UserForm, ProfileForm, User


class UserListView(GroupPermissionMixin, CompanyQuerysetMixin, ListView):
    model = User
    template_name = 'user/list.html'
    permission_required = 'view_user'

    def get_queryset(self):
        """Filtrar usuarios por compañía solo si no es super administrador"""
        if self.request.user.is_superuser:
            # Super administrador ve todos los usuarios
            return self.model.objects.all()
        else:
            # Administradores regulares solo ven usuarios de su compañía
            return super().get_queryset()

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST['action']
        try:
            if action == 'search':
                data = []
                for i in self.get_queryset():
                    data.append(i.as_dict())
            elif action == 'reset_password':
                user = self.model.objects.get(pk=request.POST['id'])
                current_session = user == request.user
                user.create_or_update_password(password=user.username)
                user.save()
                if current_session:
                    update_session_auth_hash(request, user)
            elif action == 'login_with_user':
                from django.contrib.auth import login
                admin = self.model.objects.get(pk=request.POST['id'])
                login(request, admin)
            elif action == 'update_password':
                user = self.model.objects.get(pk=request.POST['id'])
                current_session = user == request.user
                user.create_or_update_password(password=request.POST['password'])
                user.save()
                if current_session:
                    update_session_auth_hash(request, user)
            else:
                data['error'] = 'No ha seleccionado ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Listado de {self.model._meta.verbose_name_plural}'
        context['create_url'] = reverse_lazy('user_create')
        context['form'] = UpdatePasswordForm()
        return context


class UserCreateView(GroupPermissionMixin, CompanyQuerysetMixin, CreateView):
    model = User
    template_name = 'user/create.html'
    form_class = UserForm
    success_url = reverse_lazy('user_list')
    permission_required = 'add_user'

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST['action']
        try:
            if action == 'add':
                data = self.get_form().save()
            elif action == 'validate_data':
                field = request.POST['field']
                filters = Q()
                if field == 'username':
                    filters &= Q(username__iexact=request.POST['username'])
                elif field == 'email':
                    filters &= Q(email__iexact=request.POST['email'])
                data['valid'] = not self.model.objects.filter(filters).exists() if filters.children else True
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


class UserUpdateView(GroupPermissionMixin, UpdateView):
    model = User
    template_name = 'user/create.html'
    form_class = UserForm
    success_url = reverse_lazy('user_list')
    permission_required = 'change_user'

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST['action']
        try:
            if action == 'edit':
                data = self.get_form().save()
            elif action == 'validate_data':
                field = request.POST['field']
                filters = Q()
                if field == 'username':
                    filters &= Q(username__iexact=request.POST['username'])
                elif field == 'email':
                    filters &= Q(email__iexact=request.POST['email'])
                data['valid'] = not self.model.objects.filter(filters).exclude(id=self.object.id).exists() if filters.children else True
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


class UserDeleteView(GroupPermissionMixin, DeleteView):
    model = User
    template_name = 'delete.html'
    success_url = reverse_lazy('user_list')
    permission_required = 'delete_user'

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


class UserUpdateProfileView(GroupModuleMixin, UpdateView):
    model = User
    template_name = 'user/update_profile.html'
    form_class = ProfileForm
    success_url = settings.LOGIN_REDIRECT_URL

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        return self.request.user

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST['action']
        try:
            if action == 'edit':
                data = self.get_form().save()
            elif action == 'validate_data':
                field = request.POST['field']
                filters = Q()
                if field == 'username':
                    filters &= Q(username__iexact=request.POST['username'])
                elif field == 'email':
                    filters &= Q(email__iexact=request.POST['email'])
                data['valid'] = not self.model.objects.filter(filters).exclude(id=request.user.id).exists() if filters.children else True
            else:
                data['error'] = 'No ha seleccionado ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context['title'] = f'Edición de un perfil de {self.model._meta.verbose_name}'
        context['list_url'] = self.success_url
        context['action'] = 'edit'
        return context


class UserUpdatePasswordView(GroupModuleMixin, FormView):
    template_name = 'user/update_password.html'
    form_class = PasswordChangeForm
    success_url = settings.LOGIN_REDIRECT_URL

    def get_form(self, form_class=None):
        form = PasswordChangeForm(user=self.request.user)
        update_form_fields_attributes(form)
        for i in form.visible_fields():
            i.field.widget.attrs.update({'placeholder': f'Ingrese su {i.label.lower()}'})
        return form

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST['action']
        try:
            if action == 'update_password':
                form = PasswordChangeForm(user=request.user, data=request.POST)
                if form.is_valid():
                    form.save()
                    update_session_auth_hash(request, form.user)
                else:
                    data['error'] = form.errors
            else:
                data['error'] = 'No ha seleccionado ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Edición de Contraseña'
        context['list_url'] = self.success_url
        context['action'] = 'update_password'
        return context


class UserChooseProfileView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        try:
            group = Group.objects.filter(id=self.kwargs['pk']).first()
            request.session['group'] = model_to_dict(group, exclude=['permissions']) if group else dict()
        except:
            pass
        return HttpResponseRedirect(settings.LOGIN_REDIRECT_URL)
