from crum import get_current_request
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import Group
from django.http import HttpResponseRedirect

from config import settings


class BaseGroupMixin(LoginRequiredMixin):
    redirect_field_name = settings.LOGIN_REDIRECT_URL

    def get_last_url(self):
        request = get_current_request()
        last_url = request.session.get('url_last', settings.LOGIN_REDIRECT_URL)
        return last_url if last_url != request.path else settings.LOGIN_REDIRECT_URL

    def get_user_group(self, request):
        try:
            group_data = request.session.get('group')
            return Group.objects.get(id=group_data['id'])
        except:
            return None

    def set_module_in_session(self, request, group_module):
        if group_module:
            request.session['url_last'] = request.path
            request.session['module'] = group_module.module.as_dict()


class GroupPermissionMixin(BaseGroupMixin):
    permission_required = None

    def get_permissions(self):
        if isinstance(self.permission_required, str):
            return [self.permission_required]
        return list(self.permission_required or [])

    def get(self, request, *args, **kwargs):
        group = self.get_user_group(request)
        if not group:
            return HttpResponseRedirect(settings.LOGIN_REDIRECT_URL)

        permissions = self.get_permissions()
        if not permissions:
            return super().get(request, *args, **kwargs)

        group_permissions = group.permissions.filter(codename__in=permissions)
        if group_permissions.count() == len(permissions):
            group_module = group.groupmodule_set.filter(module__permissions__codename=permissions[0]).first()
            self.set_module_in_session(request, group_module)
            return super().get(request, *args, **kwargs)

        messages.error(request, 'No tienes los permisos necesarios para acceder a esta sección')
        return HttpResponseRedirect(self.get_last_url())


class GroupModuleMixin(BaseGroupMixin):
    def get(self, request, *args, **kwargs):
        group = self.get_user_group(request)
        if not group:
            return HttpResponseRedirect(settings.LOGIN_REDIRECT_URL)

        group_module = group.groupmodule_set.filter(module__url=request.path).first()
        if group_module:
            self.set_module_in_session(request, group_module)
            return super().get(request, *args, **kwargs)

        messages.error(request, 'No tienes los permisos necesarios para acceder a esta sección')
        return HttpResponseRedirect(self.get_last_url())


class CompanyQuerysetMixin:
    """Filtra automáticamente queryset de modelos con campo company."""
    company_field = 'company'

    def get_company(self):
        return getattr(self.request, 'company', None)

    def get_queryset(self):
        qs = super().get_queryset()
        company = self.get_company()
        model = qs.model
        if company and hasattr(model, self.company_field):
            return qs.filter(**{self.company_field: company})
        return qs

    def form_valid(self, form):
        company = self.get_company()
        if company and hasattr(form.instance, self.company_field) and getattr(form.instance, self.company_field) is None:
            setattr(form.instance, self.company_field, company)
        return super().form_valid(form)
