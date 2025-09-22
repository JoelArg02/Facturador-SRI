from crum import get_current_request
from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin, UserManager, Group
from django.db import models
from django.forms.models import model_to_dict
from django.utils import timezone

from config import settings


class User(AbstractBaseUser, PermissionsMixin):
    names = models.CharField(max_length=150, null=True, blank=True, help_text='Ingrese un nombre', verbose_name='Nombres')
    username = models.CharField(max_length=150, unique=True, help_text='Ingrese un username', verbose_name='Username')
    image = models.ImageField(upload_to='users/%Y/%m/%d', null=True, blank=True, verbose_name='Imagen')
    email = models.EmailField(null=True, blank=True, help_text='Ingrese un email', verbose_name='Correo electrónico')
    is_active = models.BooleanField(default=True, verbose_name='Estado')
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    is_password_change = models.BooleanField(default=False)
    password_reset_token = models.TextField(null=True, blank=True)

    objects = UserManager()

    EMAIL_FIELD = 'email'
    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']

    @property
    def get_session_user_group(self):
        try:
            request = get_current_request()
            return Group.objects.get(id=request.session['group']['id'])
        except:
            return None

    @property
    def is_customer(self):
        return hasattr(self, 'customer')

    def get_full_name(self):
        return self.names

    def get_image(self):
        if self.image:
            return f'{settings.MEDIA_URL}{self.image}'
        return f'{settings.STATIC_URL}img/default/empty.png'

    def get_group_id_session(self):
        try:
            request = get_current_request()
            return int(request.session['group'].id)
        except:
            return 0

    def set_group_session(self):
        try:
            request = get_current_request()
            groups = request.user.groups.all()
            if groups:
                if 'group' not in request.session:
                    request.session['group'] = model_to_dict(groups[0], exclude=['permissions'])
        except:
            pass

    def create_or_update_password(self, password):
        if self.pk:
            user = User.objects.get(pk=self.pk)
            if user.password != password:
                self.set_password(password)
        else:
            self.set_password(password)

    def get_short_name(self):
        if self.names:
            names = self.names.split(' ')
            if len(names) > 1:
                return f'{names[0]} {names[1]}'
        return self.names

    def has_at_least_one_group(self):
        return self.groups.all().exists()

    def has_more_than_one_group(self):
        return self.groups.all().count() > 1

    def as_dict(self):
        item = model_to_dict(self, exclude=['password_reset_token', 'password', 'user_permissions'])
        item['groups'] = [{'id': i.id, 'name': i.name} for i in self.groups.all()]
        item['last_login'] = self.last_login.strftime('%Y-%m-%d') if self.last_login else None
        item['image'] = self.get_image()
        item['date_joined'] = self.date_joined.strftime('%Y-%m-%d')
        return item

    def __str__(self):
        return self.names

    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'
