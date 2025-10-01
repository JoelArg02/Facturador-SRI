import base64
import smtplib
import tempfile
import time
from datetime import datetime
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from io import BytesIO
from xml.etree import ElementTree

import barcode
from barcode import writer
from django.core.files.base import File
from django.db import models

from config import settings
from core.pos.choices import ENVIRONMENT_TYPE, INVOICE_STATUS, VOUCHER_STAGE, VOUCHER_TYPE
from core.pos.models.transaction_summary import TransactionSummary
from core.pos.utilities.pdf_creator import PDFCreator
from core.pos.utilities.sri import SRI


class ElecBillingBase(TransactionSummary):
    receipt = models.ForeignKey('pos.Receipt', on_delete=models.PROTECT, verbose_name='Tipo de comprobante')
    time_joined = models.DateTimeField(default=datetime.now, verbose_name='Fecha y hora de registro')
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
        name = self.__class__.__name__
        if name == 'Invoice':
            return VOUCHER_TYPE[0][0]
        if name == 'CreditNote':
            return VOUCHER_TYPE[1][0]
        return VOUCHER_TYPE[2][0]

    @property
    def receipt_template_name(self):
        voucher_type = self.receipt.voucher_type
        if voucher_type == VOUCHER_TYPE[0][0]:
            return 'invoice/invoice_pdf.html'
        if voucher_type == VOUCHER_TYPE[1][0]:
            return 'credit_note/invoice_pdf.html'
        return None

    @property
    def access_code_barcode(self):
        buffer = BytesIO()
        barcode_image = barcode.Code128(self.access_code, writer=writer.ImageWriter())
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
            from core.pos.models.receipt_error import ReceiptError

            receipt_error = ReceiptError()
            receipt_error.receipt_id = self.receipt_id
            receipt_error.stage = errors['stage'] if isinstance(errors, dict) and 'stage' in errors else ''
            receipt_error.receipt_number_full = self.receipt_number_full
            if isinstance(errors, str):
                receipt_error.errors = {'error': errors}
            else:
                receipt_error.errors = errors
            receipt_error.environment_type = self.environment_type
            receipt_error.save()
        except Exception:  # pragma: no cover
            pass
        finally:
            if self.check_sequential_error(errors=errors) and change_status:
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
            from core.pos.models.receipt import Receipt

            self.receipt = Receipt.objects.get(
                company=self.company,
                voucher_type=self.voucher_type_code,
                establishment_code=self.company.establishment_code,
                issuing_point_code=self.company.issuing_point_code,
            )
        self.receipt_number = self.generate_receipt_number()
        return self.get_receipt_number_full()

    def get_receipt_number_full(self):
        return f'{self.receipt.establishment_code}-{self.receipt.issuing_point_code}-{self.receipt_number}'

    def create_authorized_pdf(self):
        try:
            template = self.receipt_template_name
            if not template:
                return
            pdf_file = PDFCreator(template_name=template).create(context={'object': self})
            with tempfile.NamedTemporaryFile(delete=True) as file_temp:
                file_temp.write(pdf_file)
                file_temp.flush()
                self.authorized_pdf.save(
                    name=f'{self.receipt.get_name_file()}-{self.receipt_number_full}.pdf',
                    content=File(file_temp),
                )
        except Exception:  # pragma: no cover
            pass

    def generate_electronic_invoice_document(self):
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

    def get_client_from_model(self):
        if hasattr(self, 'customer'):
            return getattr(self, 'customer')
        if hasattr(self, 'invoice') and hasattr(self.invoice, 'customer'):
            return self.invoice.customer
        return None

    def send_invoice_files_to_customer(self):
        response = {'resp': True}
        try:
            customer = self.get_client_from_model()
            message = MIMEMultipart('alternative')
            message['Subject'] = f'Factura electrónica – {self.receipt_number_full}'
            message['From'] = formataddr(('OptimusPos Facturación', settings.EMAIL_HOST_USER))
            message['To'] = customer.user.email

            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body {{
                margin:0;
                padding:0;
                background:#f6f8fa;
                font-family:'Segoe UI',Roboto,Arial,sans-serif;
                color:#333;
                }}
                .container {{
                max-width:600px;
                margin:20px auto;
                background:#ffffff;
                border-radius:12px;
                box-shadow:0 4px 12px rgba(0,0,0,0.1);
                overflow:hidden;
                }}
                .header {{
                background:linear-gradient(135deg,#4e73df,#2e59d9);
                color:#fff;
                text-align:center;
                padding:30px 20px;
                }}
                .header h1 {{
                margin:0;
                font-size:28px;
                letter-spacing:0.5px;
                }}
                .content {{
                padding:25px 20px;
                }}
                .content h2 {{
                margin-top:0;
                color:#2e59d9;
                }}
                .info-table {{
                width:100%;
                border-collapse:collapse;
                margin:20px 0;
                }}
                .info-table td {{
                padding:10px;
                border-top:1px solid #e1e4e8;
                }}
                .btn {{
                display:inline-block;
                margin-top:20px;
                background:#2e59d9;
                color:#fff !important;
                text-decoration:none;
                padding:12px 24px;
                border-radius:6px;
                font-weight:600;
                }}
                .footer {{
                text-align:center;
                padding:20px;
                font-size:12px;
                color:#888;
                }}
                @media screen and (max-width: 600px) {{
                .header h1 {{ font-size:24px; }}
                .content h2 {{ font-size:20px; }}
                }}
            </style>
            </head>
            <body>
            <div class="container">
                <div class="header">
                <h1>OptimusPos Facturación</h1>
                </div>
                <div class="content">
                <h2>Hola {customer.user.names.title()}</h2>
                <p>
                    Gracias por confiar en <strong>{self.company.commercial_name}</strong>.
                    Adjuntamos su documento electrónico en formato <strong>PDF</strong> y <strong>XML</strong>.
                </p>
                <table class="info-table">
                    <tr><td><strong>Documento:</strong></td><td>{self.receipt.name} {self.receipt_number_full}</td></tr>
                    <tr><td><strong>Fecha:</strong></td><td>{self.formatted_date_joined()}</td></tr>
                    <tr><td><strong>Monto:</strong></td><td>${float(round(self.total_amount, 2))}</td></tr>
                    <tr><td><strong>Código de acceso:</strong></td><td>{self.access_code}</td></tr>
                    <tr><td><strong>Autorización:</strong></td><td>{self.access_code}</td></tr>
                </table>
                <p>
                    Puede descargar los archivos directamente desde este correo o desde su cuenta en nuestro sistema.
                </p>
                
                </div>
                <div class="footer">
                © {self.company.commercial_name} – Todos los derechos reservados
                </div>
            </div>
            </body>
            </html>
            """
            message.attach(MIMEText(html_content, 'html'))

            pdf_file = self.create_invoice_pdf()
            pdf_part = MIMEApplication(pdf_file, _subtype='pdf')
            pdf_part.add_header('Content-Disposition', 'attachment', filename=f'{self.access_code}.pdf')
            message.attach(pdf_part)

            with open(f'{settings.BASE_DIR}{self.get_authorized_xml()}', 'rb') as file_xml:
                xml_part = MIMEApplication(file_xml.read())
                xml_part.add_header('Content-Disposition', 'attachment', filename=f'{self.access_code}.xml')
                message.attach(xml_part)

            server = smtplib.SMTP_SSL(settings.EMAIL_HOST, 465)
            server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
            server.sendmail(settings.EMAIL_HOST_USER, [customer.user.email], message.as_string())
            server.quit()

        except Exception as exc:  # pragma: no cover
            response = {'resp': False, 'error': str(exc)}
        return response

    def receipt_number_is_null(self):
        return not self.receipt_number_full or not self.receipt_number

    def save_sequence_number(self):
        self.receipt.sequence = int(self.receipt_number)
        self.receipt.save()

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        if self.pk is None and not self.receipt_number_is_null():
            self.save_sequence_number()
        super().save(force_insert=force_insert, force_update=force_update, using=using, update_fields=update_fields)

    def edit(self):
        super().save()
