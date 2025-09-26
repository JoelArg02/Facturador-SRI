import smtplib
from datetime import datetime
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from django.db import models, transaction
from django.db.models import F, FloatField, Sum
from django.db.models.functions import Coalesce

from config import settings
from core.pos.choices import VOUCHER_TYPE
from core.pos.models.invoice import Invoice
from core.pos.models.invoice_detail import InvoiceDetail
from core.pos.models.receipt import Receipt
from core.pos.models.transaction_summary import TransactionSummary
from core.pos.utilities.pdf_creator import PDFCreator


class Quotation(TransactionSummary):
    customer = models.ForeignKey('pos.Customer', on_delete=models.CASCADE, verbose_name='Cliente')
    employee = models.ForeignKey('user.User', on_delete=models.CASCADE, verbose_name='Empleado')
    active = models.BooleanField(default=True, verbose_name='Activo')

    def __str__(self):
        return f'{self.formatted_number} = {self.customer.get_full_name()}'

    @property
    def subtotal_without_taxes(self):
        return float(self.quotationdetail_set.filter().aggregate(result=Coalesce(Sum('subtotal'), 0.00, output_field=FloatField()))['result'])

    @property
    def formatted_number(self):
        return f'{self.id:08d}'

    @property
    def validate_stock(self):
        return not self.quotationdetail_set.filter(product__is_inventoried=True, product__stock__lt=F('quantity')).exists()

    def send_quotation_by_email(self):
        message = MIMEMultipart('alternative')
        message['Subject'] = f'Proforma {self.formatted_number} - {self.customer.get_full_name()}'
        message['From'] = settings.EMAIL_HOST_USER
        message['To'] = self.customer.user.email

        content = f'Estimado(a)\n\n{self.customer.user.names.upper()}\n\n'
        content += 'La cotización solicitada ha sido enviada a su correo electrónico para su revisión.\n\n'
        message.attach(MIMEText(content))

        pdf_file = PDFCreator(template_name='quotation/invoice_pdf.html').create(context={'quotation': self})
        pdf_part = MIMEApplication(pdf_file, _subtype='pdf')
        pdf_part.add_header('Content-Disposition', 'attachment', filename=f'{self.formatted_number}.pdf')
        message.attach(pdf_part)

        server = smtplib.SMTP_SSL(settings.EMAIL_HOST, 465)
        server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
        server.sendmail(settings.EMAIL_HOST_USER, message['To'], message.as_string())
        server.quit()

    def calculate_detail(self):
        for detail in self.quotationdetail_set.filter():
            detail.price = float(detail.price)
            detail.tax = float(self.tax)
            detail.price_with_tax = detail.price + (detail.price * detail.tax)
            detail.subtotal = detail.price * detail.quantity
            detail.total_discount = detail.subtotal * float(detail.discount)
            detail.total_tax = (detail.subtotal - detail.total_discount) * detail.tax
            detail.total_amount = detail.subtotal - detail.total_discount
            detail.save()

    def calculate_invoice(self):
        self.subtotal_without_tax = float(self.quotationdetail_set.filter(product__has_tax=False).aggregate(result=Coalesce(Sum('total_amount'), 0.00, output_field=FloatField()))['result'])
        self.subtotal_with_tax = float(self.quotationdetail_set.filter(product__has_tax=True).aggregate(result=Coalesce(Sum('total_amount'), 0.00, output_field=FloatField()))['result'])
        self.total_tax = round(self.quotationdetail_set.filter(product__has_tax=True).aggregate(result=Coalesce(Sum('total_tax'), 0.00, output_field=FloatField()))['result'], 2)
        self.total_discount = float(self.quotationdetail_set.filter().aggregate(result=Coalesce(Sum('total_discount'), 0.00, output_field=FloatField()))['result'])
        self.total_amount = round(self.subtotal, 2) + float(self.total_tax)
        self.save()

    def recalculate_invoice(self):
        self.calculate_detail()
        self.calculate_invoice()

    def create_invoice(self, is_draft_invoice=False):
        data = dict()
        with transaction.atomic():
            details = list(self.quotationdetail_set.all())
            invoice = Invoice()
            invoice.date_joined = datetime.now().date()
            invoice.company = self.company
            invoice.environment_type = invoice.company.environment_type
            invoice.receipt = Receipt.objects.get(
                voucher_type=VOUCHER_TYPE[0][0],
                establishment_code=invoice.company.establishment_code,
                issuing_point_code=invoice.company.issuing_point_code,
            )
            invoice.receipt_number = invoice.generate_receipt_number()
            invoice.receipt_number_full = invoice.get_receipt_number_full()
            invoice.employee_id = self.employee_id
            invoice.customer_id = self.customer_id
            invoice.tax = invoice.company.tax_rate
            invoice.cash = float(invoice.total_amount)
            invoice.is_draft_invoice = is_draft_invoice
            invoice.create_electronic_invoice = not is_draft_invoice
            invoice.save()
            for quotation_detail in details:
                product = quotation_detail.product
                invoice_detail = InvoiceDetail.objects.create(
                    invoice_id=invoice.id,
                    product_id=product.id,
                    quantity=quotation_detail.quantity,
                    price=quotation_detail.price,
                    discount=quotation_detail.discount,
                )
                invoice_detail.deduct_product_stock()
            invoice.recalculate_invoice()
            if not invoice.is_draft_invoice:
                data = invoice.generate_electronic_invoice_document()
                if not data['resp']:
                    transaction.set_rollback(True)
        if 'error' in data:
            invoice.create_receipt_error(errors=data, change_status=False)
        return data

    def as_dict(self):
        item = super().as_dict()
        item['number'] = self.formatted_number
        item['customer'] = self.customer.as_dict()
        item['employee'] = self.employee.as_dict()
        return item

    class Meta:
        verbose_name = 'Proforma'
        verbose_name_plural = 'Proformas'
        default_permissions = ()
        permissions = (
            ('view_quotation', 'Can view Proforma'),
            ('add_quotation', 'Can add Proforma'),
            ('change_quotation', 'Can change Proforma'),
            ('delete_quotation', 'Can delete Proforman'),
            ('print_quotation', 'Can print Proforma'),
        )

