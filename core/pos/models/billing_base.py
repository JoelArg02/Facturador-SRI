import base64, time, tempfile
from io import BytesIO
from django.db import models
from django.forms import model_to_dict
from config import settings
from core.pos.choices import (
    ENVIRONMENT_TYPE, INVOICE_STATUS, VOUCHER_TYPE
)
from .catalog import Receipt
from .company import Company

class TransactionSummary(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    date_joined = models.DateField(default=__import__('datetime').datetime.now, verbose_name='Fecha de registro')
    subtotal_without_tax = models.DecimalField(max_digits=9, decimal_places=2, default=0.00, verbose_name='Subtotal sin impuestos')
    subtotal_with_tax = models.DecimalField(max_digits=9, decimal_places=2, default=0.00, verbose_name='Subtotal con impuestos')
    tax = models.DecimalField(max_digits=9, decimal_places=2, default=0.00, verbose_name='IVA')
    total_tax = models.DecimalField(max_digits=9, decimal_places=2, default=0.00, verbose_name='Total de IVA')
    total_discount = models.DecimalField(max_digits=9, decimal_places=2, default=0.00, verbose_name='Valor total del descuento')
    total_amount = models.DecimalField(max_digits=9, decimal_places=2, default=0.00, verbose_name='Total a pagar')
    class Meta:
        abstract = True
    @property
    def subtotal(self):
        return float(self.subtotal_with_tax) + float(self.subtotal_without_tax)
    def formatted_date_joined(self):
        from datetime import datetime
        return (datetime.strptime(self.date_joined, '%Y-%m-%d') if isinstance(self.date_joined, str) else self.date_joined).strftime('%Y-%m-%d')
    def as_dict(self):
        item = model_to_dict(self, exclude=['company'])
        item['date_joined'] = self.formatted_date_joined()
        item['subtotal_without_tax'] = float(self.subtotal_without_tax)
        item['subtotal_with_tax'] = float(self.subtotal_with_tax)
        item['tax'] = float(self.tax)
        item['total_tax'] = float(self.total_tax)
        item['total_discount'] = float(self.total_discount)
        item['total_amount'] = float(self.total_amount)
        item['subtotal'] = self.subtotal
        return item

class ElecBillingBase(TransactionSummary):
    receipt = models.ForeignKey(Receipt, on_delete=models.PROTECT, verbose_name='Tipo de comprobante')
    time_joined = models.DateTimeField(default=__import__('datetime').datetime.now, verbose_name='Fecha y hora de registro')
    receipt_number = models.CharField(max_length=9, null=True, blank=True, verbose_name='Número de comprobante')
    receipt_number_full = models.CharField(max_length=20, null=True, blank=True, verbose_name='Número completo de comprobante')
    environment_type = models.PositiveIntegerField(choices=ENVIRONMENT_TYPE, default=ENVIRONMENT_TYPE[0][0], verbose_name='Entorno de facturación electrónica')
    access_code = models.CharField(max_length=49, null=True, blank=True, verbose_name='Código de acceso')
    authorized_date = models.DateTimeField(null=True, blank=True, verbose_name='Fecha de autorización')
    authorized_xml = models.FileField(upload_to='authorized_xml/%Y/%m/%d', null=True, blank=True, verbose_name='XML Autorizado')
    authorized_pdf = models.FileField(upload_to='pdf_authorized/%Y/%m/%d', null=True, blank=True, verbose_name='PDF Autorizado')
    create_electronic_invoice = models.BooleanField(default=True, verbose_name='Crear factura electrónica')
    additional_info = models.JSONField(default=dict, verbose_name='Información adicional')
    status = models.CharField(max_length=50, choices=INVOICE_STATUS, default=INVOICE_STATUS[0][0], verbose_name='Estado')
    class Meta:
        abstract = True
    @property
    def voucher_type_code(self):
        from .invoice import Invoice
        from .credit_note import CreditNote
        if isinstance(self, Invoice):
            return VOUCHER_TYPE[0][0]
        elif isinstance(self, CreditNote):
            return VOUCHER_TYPE[1][0]
        return VOUCHER_TYPE[2][0]
    @property
    def receipt_template_name(self):
        if self.receipt.voucher_type == VOUCHER_TYPE[0][0]:
            return 'invoice/invoice_pdf.html'
        if self.receipt.voucher_type == VOUCHER_TYPE[1][0]:
            return 'credit_note/invoice_pdf.html'
        return None
    @property
    def access_code_barcode(self):
        import barcode
        buffer = BytesIO()
        barcode_image = barcode.Code128(self.access_code, writer=barcode.writer.ImageWriter())
        barcode_image.write(buffer, options={'text_distance': 3.0, 'font_size': 6})
        encoded_image = base64.b64encode(buffer.getvalue()).decode('ascii')
        return f"data:image/png;base64,{encoded_image}"
    def is_invoice(self):
        return self.receipt.voucher_type == VOUCHER_TYPE[0][0]
    def is_credit_note(self):
        return self.receipt.voucher_type == VOUCHER_TYPE[1][0]
    def formatted_time_joined(self):
        return self.time_joined.strftime('%Y-%m-%d %H:%M:%S')
    def formatted_authorized_date(self):
        return self.authorized_date.strftime('%Y-%m-%d') if self.authorized_date else ''
    def get_authorized_xml(self):
        if self.authorized_xml:
            return f'{settings.MEDIA_URL}{self.authorized_xml}'
        return None
    def get_authorized_pdf(self):
        if self.authorized_pdf:
            return f'{settings.MEDIA_URL}{self.authorized_pdf}'
        return None
    def as_dict(self):
        item = super().as_dict()
        item['receipt'] = self.receipt.as_dict()
        item['time_joined'] = self.formatted_time_joined()
        item['authorized_date'] = self.formatted_authorized_date()
        item['authorized_xml'] = self.get_authorized_xml()
        item['authorized_pdf'] = self.get_authorized_pdf()
        item['status'] = {'id': self.status, 'name': self.get_status_display()}
        item['is_invoice'] = self.is_invoice()
        item['is_credit_note'] = self.is_credit_note()
        return item
    def check_sequential_error(self, errors):
        if 'error' in errors and isinstance(errors['error'], dict):
            if 'errors' in errors['error']:
                for error in errors['error']['errors']:
                    if 'mensaje' in error and error['mensaje'] == 'ERROR SECUENCIAL REGISTRADO':
                        return True
        return False
    def create_receipt_error(self, errors, change_status=True):
        try:
            from .catalog import ReceiptError
            receipt_error = ReceiptError()
            receipt_error.receipt_id = self.receipt_id
            receipt_error.stage = errors['stage'] if isinstance(errors, dict) and 'stage' in errors else ''
            receipt_error.receipt_number_full = self.receipt_number_full
            receipt_error.errors = {'error': errors} if isinstance(errors, str) else errors
            receipt_error.environment_type = self.environment_type
            receipt_error.save()
        except Exception:
            pass
        finally:
            if self.check_sequential_error(errors=errors) and change_status:
                from core.pos.choices import INVOICE_STATUS
                self.status = INVOICE_STATUS[4][0]
                self.edit()
                self.receipt.sequence = self.receipt.sequence + 1
                self.receipt.save()
    def generate_receipt_number(self, increase=True):
        if isinstance(self.receipt.sequence, str):
            self.receipt.sequence = int(self.receipt.sequence)
        number = self.receipt.sequence + 1 if increase else self.receipt.sequence
        return f'{number:09d}'
    def generate_receipt_number_full(self):
        if self.receipt_id is None:
            self.receipt = Receipt.objects.get(voucher_type=self.voucher_type_code, establishment_code=self.company.establishment_code, issuing_point_code=self.company.issuing_point_code)
        self.receipt_number = self.generate_receipt_number()
        return self.get_receipt_number_full()
    def get_receipt_number_full(self):
        return f'{self.receipt.establishment_code}-{self.receipt.issuing_point_code}-{self.receipt_number}'
    def create_authorized_pdf(self):
        try:
            from core.pos.utilities.pdf_creator import PDFCreator
            pdf_file = PDFCreator(template_name=self.receipt_template_name).create(context={'object': self})
            from django.core.files import File
            with tempfile.NamedTemporaryFile(delete=True) as file_temp:
                file_temp.write(pdf_file)
                file_temp.flush()
                self.authorized_pdf.save(name=f'{self.receipt.get_name_file()}-{self.receipt_number_full}.pdf', content=File(file_temp))
        except Exception:
            pass
    def generate_electronic_invoice_document(self):
        from core.pos.utilities.sri import SRI
        sri = SRI()
        response = sri.create_xml(self)
        if response['resp']:
            response = sri.firm_xml(instance=self, xml=response['xml'])
            if response['resp']:
                response = sri.validate_xml(instance=self, xml=response['xml'])
                if response['resp']:
                    response = sri.authorize_xml(instance=self)
                    index = 1
                    while not response['resp'] and index < 3:
                        time.sleep(1)
                        response = sri.authorize_xml(instance=self)
                        index += 1
                    return response
        return response
    def receipt_number_is_null(self):
        return self.receipt_number_full is None or self.receipt_number is None
    def save_sequence_number(self):
        self.receipt.sequence = int(self.receipt_number)
        self.receipt.save()
    def save(self, *args, **kwargs):
        if self.pk is None and not self.receipt_number_is_null():
            self.save_sequence_number()
        super().save(*args, **kwargs)
    def edit(self):
        super().save()

class ElecBillingDetailBase(models.Model):
    product = models.ForeignKey('pos.Product', on_delete=models.PROTECT)
    quantity = models.IntegerField(default=0)
    price = models.DecimalField(max_digits=9, decimal_places=4, default=0.00)
    price_with_tax = models.DecimalField(max_digits=9, decimal_places=4, default=0.00)
    subtotal = models.DecimalField(max_digits=9, decimal_places=4, default=0.00)
    tax = models.DecimalField(max_digits=9, decimal_places=4, default=0.00)
    total_tax = models.DecimalField(max_digits=9, decimal_places=4, default=0.00)
    discount = models.DecimalField(max_digits=9, decimal_places=4, default=0.00)
    total_discount = models.DecimalField(max_digits=9, decimal_places=4, default=0.00)
    total_amount = models.DecimalField(max_digits=9, decimal_places=4, default=0.00)
    class Meta:
        abstract = True
    @property
    def tax_rate(self):
        return self.tax * 100
    @property
    def discount_rate(self):
        return self.discount * 100
    def as_dict(self):
        from .catalog import Product
        item = model_to_dict(self)
        # product relation to dict
        try:
            item['product'] = self.product.as_dict()
        except Exception:
            pass
        item['tax'] = float(self.tax)
        item['price'] = float(self.price)
        item['price_with_tax'] = float(self.price_with_tax)
        item['subtotal'] = float(self.subtotal)
        item['total_tax'] = float(self.total_tax)
        item['discount'] = float(self.discount)
        item['total_discount'] = float(self.total_discount)
        item['total_amount'] = float(self.total_amount)
        return item
