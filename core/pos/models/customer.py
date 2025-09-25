from django.db import models
from .billing_base import TransactionSummary

class Customer(TransactionSummary):
    # company opcional sólo para Customer (el campo original en TransactionSummary es requerido)
    company = models.ForeignKey('pos.Company', on_delete=models.CASCADE, null=True, blank=True, help_text='Asignar luego si aplica')
    user = models.OneToOneField('user.User', on_delete=models.CASCADE, verbose_name='Usuario')
    mobile = models.CharField(max_length=10, null=True, blank=True, verbose_name='Celular')
    address = models.CharField(max_length=500, null=True, blank=True, verbose_name='Dirección')
    business_name = models.CharField(max_length=250, null=True, blank=True, verbose_name='Razón Social')
    commercial_name = models.CharField(max_length=250, null=True, blank=True, verbose_name='Nombre Comercial')
    tradename = models.CharField(max_length=200, null=True, blank=True, verbose_name='Nombre Comercial Facturación')
    ruc = models.CharField(max_length=13, null=True, blank=True, unique=True, verbose_name='RUC')
    dni = models.CharField(max_length=10, null=True, blank=True, unique=True, verbose_name='Cédula')
    is_business = models.BooleanField(default=False, verbose_name='Es Empresa')
    is_credit_authorized = models.BooleanField(default=False, verbose_name='Está autorizado para crédito')
    credit_limit = models.DecimalField(default=0.00, decimal_places=2, max_digits=9, verbose_name='Límite de crédito')
    def __str__(self):
        return self.user.get_full_name()
    
    @property
    def identification_type(self):
        """Determina el tipo de identificación basado en RUC o DNI"""
        if self.ruc:
            return '04'  # RUC
        elif self.dni:
            return '05'  # CEDULA
        else:
            return ''    # Sin identificación
    
    @property
    def send_email_invoice(self):
        """Property que simula el campo send_email_invoice sin tocas la BD"""
        return True
    
    def as_dict(self):
        item = super().as_dict()
        item['user'] = self.user.toJSON()
        
        # Campo 'text' requerido para Select2
        display_name = self.user.get_full_name()
        if self.ruc:
            display_name += f" (RUC: {self.ruc})"
        elif self.dni:
            display_name += f" (CI: {self.dni})"
        item['text'] = display_name
        
        # Derivar identificación: priorizar RUC si existe
        identification_type_code = self.identification_type
        if identification_type_code == '04':
            item['identification_type'] = {'id': '04', 'name': 'RUC'}
            item['dni'] = self.ruc  # Para la tabla mostramos el valor usado
        elif identification_type_code == '05':
            item['identification_type'] = {'id': '05', 'name': 'CEDULA'}
            item['dni'] = self.dni
        else:
            item['identification_type'] = {'id': '', 'name': ''}
        item['business_name'] = self.business_name
        item['tradename'] = self.tradename
        item['ruc'] = self.ruc
        item['is_business'] = self.is_business
        item['is_credit_authorized'] = self.is_credit_authorized
        item['credit_limit'] = float(self.credit_limit)
        if self.mobile:
            item['mobile'] = self.mobile
        if self.address:
            item['address'] = self.address
        return item
    class Meta:
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'
        default_permissions = ()
        permissions = (
            ('view_customer', 'Can view Cliente'),
            ('add_customer', 'Can add Cliente'),
            ('change_customer', 'Can change Cliente'),
            ('delete_customer', 'Can delete Cliente'),
        )
