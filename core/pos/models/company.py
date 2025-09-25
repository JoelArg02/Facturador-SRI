import base64
import os
from django.db import models
from django.forms import model_to_dict
from config import settings
from core.pos.choices import (
    OBLIGATED_ACCOUNTING, ENVIRONMENT_TYPE, EMISSION_TYPE,
    RETENTION_AGENT, REGIMEN_RIMPE, TAX_PERCENTAGE
)

class Company(models.Model):
    ruc = models.CharField(max_length=13, help_text='Ingrese un número de RUC', verbose_name='Número de RUC')
    company_name = models.CharField(max_length=50, help_text='Ingrese la razón social', verbose_name='Razón social')
    commercial_name = models.CharField(max_length=50, help_text='Ingrese el nombre comercial', verbose_name='Nombre Comercial')
    main_address = models.CharField(max_length=200, help_text='Ingrese la dirección del Establecimiento Matriz', verbose_name='Dirección del Establecimiento Matriz')
    establishment_address = models.CharField(max_length=200, help_text='Ingrese la dirección del Establecimiento Emisor', verbose_name='Dirección del Establecimiento Emisor')
    establishment_code = models.CharField(max_length=3, help_text='Ingrese el código del Establecimiento Emisor', verbose_name='Código del Establecimiento Emisor')
    issuing_point_code = models.CharField(max_length=3, help_text='Ingrese el código del Punto de Emisión', verbose_name='Código del Punto de Emisión')
    special_taxpayer = models.CharField(max_length=13, help_text='Ingrese el número de Resolución del Contribuyente Especial', verbose_name='Contribuyente Especial (Número de Resolución)')
    obligated_accounting = models.CharField(max_length=2, choices=OBLIGATED_ACCOUNTING, default=OBLIGATED_ACCOUNTING[1][0], verbose_name='Obligado a Llevar Contabilidad')
    image = models.ImageField(upload_to='company/%Y/%m/%d', null=True, blank=True, verbose_name='Logotipo')
    environment_type = models.PositiveIntegerField(choices=ENVIRONMENT_TYPE, default=1, verbose_name='Tipo de Ambiente')
    emission_type = models.PositiveIntegerField(choices=EMISSION_TYPE, default=1, verbose_name='Tipo de Emisión')
    retention_agent = models.CharField(max_length=2, choices=RETENTION_AGENT, default=RETENTION_AGENT[1][0], verbose_name='Agente de Retención')
    regimen_rimpe = models.CharField(max_length=50, choices=REGIMEN_RIMPE, default=REGIMEN_RIMPE[0][0], verbose_name='Regimen Tributario')
    mobile = models.CharField(max_length=10, null=True, blank=True, help_text='Ingrese el teléfono celular', verbose_name='Teléfono celular')
    phone = models.CharField(max_length=9, null=True, blank=True, help_text='Ingrese el teléfono convencional', verbose_name='Teléfono convencional')
    email = models.CharField(max_length=50, help_text='Ingrese la dirección de correo electrónico', verbose_name='Email')
    website = models.CharField(max_length=250, help_text='Ingrese la dirección de la página web', verbose_name='Dirección de página web')
    description = models.CharField(max_length=500, null=True, blank=True, help_text='Ingrese una breve descripción', verbose_name='Descripción')
    tax = models.DecimalField(default=0.00, decimal_places=2, max_digits=9, verbose_name='Impuesto IVA')
    tax_percentage = models.IntegerField(choices=TAX_PERCENTAGE, default=TAX_PERCENTAGE[3][0], verbose_name='Porcentaje del impuesto IVA')
    electronic_signature = models.FileField(null=True, blank=True, upload_to='company/%Y/%m/%d', verbose_name='Firma electrónica (Archivo P12)')
    electronic_signature_key = models.CharField(max_length=100, help_text='Ingrese la clave de firma electrónica', verbose_name='Clave de firma electrónica')
    email_host = models.CharField(max_length=30, default='smtp.gmail.com', verbose_name='Servidor de correo')
    email_port = models.IntegerField(default=587, verbose_name='Puerto del servidor de correo')
    email_host_user = models.CharField(max_length=100, help_text='Ingrese el nombre de usuario del servidor de correo', verbose_name='Username del servidor de correo')
    email_host_password = models.CharField(max_length=30, help_text='Ingrese la contraseña del servidor de correo', verbose_name='Password del servidor de correo')
    # Nota: related_name cambiado de 'company' a 'owned_company' para no chocar con User.company (FK)
    owner = models.OneToOneField('user.User', null=True, blank=True, related_name='owned_company', on_delete=models.SET_NULL, verbose_name='Propietario')

    def __str__(self):
        return self.commercial_name

    @property
    def is_popular_business(self):
        return self.regimen_rimpe == REGIMEN_RIMPE[2][0]

    @property
    def is_popular_regime(self):
        return self.regimen_rimpe == REGIMEN_RIMPE[0][0]

    @property
    def is_retention_agent(self):
        return self.retention_agent == RETENTION_AGENT[0][0]

    @property
    def base64_image(self):
        try:
            if self.image:
                with open(self.image.path, 'rb') as image_file:
                    import base64
                    base64_data = base64.b64encode(image_file.read()).decode('utf-8')
                    extension = os.path.splitext(self.image.name)[1]
                    content_type = f'image/{extension.lstrip(".")}'
                    return f"data:{content_type};base64,{base64_data}"
        except Exception:
            pass
        return None

    @property
    def tax_rate(self):
        return float(self.tax) / 100

    def get_image(self):
        if self.image:
            return f'{settings.MEDIA_URL}{self.image}'
        return f'{settings.STATIC_URL}img/default/empty.png'

    def get_full_path_image(self):
        if self.image:
            return self.image.path
        return f'{settings.BASE_DIR}{settings.STATIC_URL}img/default/empty.png'

    def get_electronic_signature(self):
        if self.electronic_signature:
            return f'{settings.MEDIA_URL}{self.electronic_signature}'
        return None

    def as_dict(self):
        item = model_to_dict(self)
        item['image'] = self.get_image()
        item['electronic_signature'] = self.get_electronic_signature()
        item['tax'] = float(self.tax)
        item['owner'] = self.owner_id
        return item

    def active_subscription(self):
        from core.subscription.models import get_active_subscription
        return get_active_subscription(self)

    def can_create(self, kind: str):
        from core.subscription.services import ensure_quota, QuotaExceeded
        try:
            ensure_quota(self, kind)
            return True, None
        except QuotaExceeded as e:
            return False, str(e)

    def save(self, *args, **kwargs):
        if self.pk:
            from .catalog import Receipt
            Receipt.objects.update(establishment_code=self.establishment_code, issuing_point_code=self.issuing_point_code)
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'Compañia'
        verbose_name_plural = 'Compañias'
        default_permissions = ()
        permissions = (('change_company', 'Can change Compañia'),)
