from datetime import datetime
from xml.etree import ElementTree

from django.db import models
from django.db.models import FloatField, Sum
from django.db.models.functions import Coalesce

from core.pos.choices import INVOICE_STATUS, RETENTION_AGENT, TAX_CODES
from core.pos.models.elec_billing_base import ElecBillingBase
from core.pos.utilities.pdf_creator import PDFCreator
from core.pos.utilities.sri import SRI


class CreditNote(ElecBillingBase):
    invoice = models.ForeignKey('pos.Invoice', on_delete=models.PROTECT, verbose_name='Factura')
    motive = models.CharField(max_length=300, null=True, blank=True, help_text='Ingrese una descripción', verbose_name='Motivo')

    def __str__(self):
        return self.motive or ''

    @property
    def subtotal_without_taxes(self):
        return float(self.creditnotedetail_set.filter().aggregate(result=Coalesce(Sum('subtotal'), 0.00, output_field=FloatField()))['result'])

    def calculate_detail(self):
        for detail in self.creditnotedetail_set.filter():
            detail.price = float(detail.price)
            detail.tax = float(self.tax)
            detail.price_with_tax = detail.price + (detail.price * detail.tax)
            detail.subtotal = detail.price * detail.quantity
            detail.total_discount = detail.subtotal * float(detail.discount)
            detail.total_tax = (detail.subtotal - detail.total_discount) * detail.tax
            detail.total_amount = detail.subtotal - detail.total_discount
            detail.save()

    def calculate_invoice(self):
        self.subtotal_without_tax = float(self.creditnotedetail_set.filter(product__has_tax=False).aggregate(result=Coalesce(Sum('total_amount'), 0.00, output_field=FloatField()))['result'])
        self.subtotal_with_tax = float(self.creditnotedetail_set.filter(product__has_tax=True).aggregate(result=Coalesce(Sum('total_amount'), 0.00, output_field=FloatField()))['result'])
        self.total_tax = round(self.creditnotedetail_set.filter(product__has_tax=True).aggregate(result=Coalesce(Sum('total_tax'), 0.00, output_field=FloatField()))['result'], 2)
        self.total_discount = float(self.creditnotedetail_set.filter().aggregate(result=Coalesce(Sum('total_discount'), 0.00, output_field=FloatField()))['result'])
        self.total_amount = round(self.subtotal, 2) + round(self.total_tax, 2)
        self.save()

    def recalculate_invoice(self):
        self.calculate_detail()
        self.calculate_invoice()

    def create_xml_document(self):
        access_key = SRI().create_access_key(self)
        root = ElementTree.Element('notaCredito', id='comprobante', version='1.1.0')
        xml_tax_info = ElementTree.SubElement(root, 'infoTributaria')
        ElementTree.SubElement(xml_tax_info, 'ambiente').text = str(self.company.environment_type)
        ElementTree.SubElement(xml_tax_info, 'tipoEmision').text = str(self.company.emission_type)
        ElementTree.SubElement(xml_tax_info, 'razonSocial').text = self.company.company_name
        ElementTree.SubElement(xml_tax_info, 'nombreComercial').text = self.company.commercial_name
        ElementTree.SubElement(xml_tax_info, 'ruc').text = self.company.ruc
        ElementTree.SubElement(xml_tax_info, 'claveAcceso').text = access_key
        ElementTree.SubElement(xml_tax_info, 'codDoc').text = self.receipt.voucher_type
        ElementTree.SubElement(xml_tax_info, 'estab').text = self.receipt.establishment_code
        ElementTree.SubElement(xml_tax_info, 'ptoEmi').text = self.receipt.issuing_point_code
        ElementTree.SubElement(xml_tax_info, 'secuencial').text = self.receipt_number
        ElementTree.SubElement(xml_tax_info, 'dirMatriz').text = self.company.main_address
        if not self.company.is_popular_regime:
            ElementTree.SubElement(xml_tax_info, 'contribuyenteRimpe').text = self.company.regimen_rimpe
        if self.company.retention_agent == RETENTION_AGENT[0][0]:
            ElementTree.SubElement(xml_tax_info, 'agenteRetencion').text = '1'

        xml_info_invoice = ElementTree.SubElement(root, 'infoNotaCredito')
        ElementTree.SubElement(xml_info_invoice, 'fechaEmision').text = datetime.now().strftime('%d/%m/%Y')
        ElementTree.SubElement(xml_info_invoice, 'dirEstablecimiento').text = self.company.establishment_address
        ElementTree.SubElement(xml_info_invoice, 'tipoIdentificacionComprador').text = self.invoice.customer.identification_type
        ElementTree.SubElement(xml_info_invoice, 'razonSocialComprador').text = self.invoice.customer.user.names
        ElementTree.SubElement(xml_info_invoice, 'identificacionComprador').text = self.invoice.customer.dni
        if self.company.special_taxpayer != '000':
            ElementTree.SubElement(xml_info_invoice, 'contribuyenteEspecial').text = self.company.special_taxpayer
        ElementTree.SubElement(xml_info_invoice, 'obligadoContabilidad').text = self.company.obligated_accounting
        ElementTree.SubElement(xml_info_invoice, 'rise').text = 'Contribuyente Régimen Simplificado RISE'
        ElementTree.SubElement(xml_info_invoice, 'codDocModificado').text = self.invoice.receipt.voucher_type
        ElementTree.SubElement(xml_info_invoice, 'numDocModificado').text = self.invoice.receipt_number_full
        ElementTree.SubElement(xml_info_invoice, 'fechaEmisionDocSustento').text = self.invoice.date_joined.strftime('%d/%m/%Y')
        ElementTree.SubElement(xml_info_invoice, 'totalSinImpuestos').text = f'{self.subtotal:.2f}'
        ElementTree.SubElement(xml_info_invoice, 'valorModificacion').text = f'{self.total_amount:.2f}'
        ElementTree.SubElement(xml_info_invoice, 'moneda').text = 'DOLAR'

        xml_total_with_taxes = ElementTree.SubElement(xml_info_invoice, 'totalConImpuestos')
        if self.subtotal_without_tax != 0.0000:
            xml_total_tax = ElementTree.SubElement(xml_total_with_taxes, 'totalImpuesto')
            ElementTree.SubElement(xml_total_tax, 'codigo').text = str(TAX_CODES[0][0])
            ElementTree.SubElement(xml_total_tax, 'codigoPorcentaje').text = '0'
            ElementTree.SubElement(xml_total_tax, 'baseImponible').text = f'{self.subtotal_without_tax:.2f}'
            ElementTree.SubElement(xml_total_tax, 'valor').text = f'{0:.2f}'
        if self.subtotal_with_tax != 0.0000:
            xml_total_tax2 = ElementTree.SubElement(xml_total_with_taxes, 'totalImpuesto')
            ElementTree.SubElement(xml_total_tax2, 'codigo').text = str(TAX_CODES[0][0])
            ElementTree.SubElement(xml_total_tax2, 'codigoPorcentaje').text = str(self.company.tax_percentage)
            ElementTree.SubElement(xml_total_tax2, 'baseImponible').text = f'{self.subtotal_with_tax:.2f}'
            ElementTree.SubElement(xml_total_tax2, 'valor').text = f'{self.total_tax:.2f}'
        ElementTree.SubElement(xml_info_invoice, 'motivo').text = self.motive

        xml_details = ElementTree.SubElement(root, 'detalles')
        for detail in self.creditnotedetail_set.all():
            xml_detail = ElementTree.SubElement(xml_details, 'detalle')
            ElementTree.SubElement(xml_detail, 'codigoInterno').text = detail.product.code
            ElementTree.SubElement(xml_detail, 'descripcion').text = detail.product.name
            ElementTree.SubElement(xml_detail, 'cantidad').text = f'{detail.quantity:.2f}'
            ElementTree.SubElement(xml_detail, 'precioUnitario').text = f'{detail.price:.2f}'
            ElementTree.SubElement(xml_detail, 'descuento').text = f'{detail.total_discount:.2f}'
            ElementTree.SubElement(xml_detail, 'precioTotalSinImpuesto').text = f'{detail.total_amount:.2f}'
            xml_taxes = ElementTree.SubElement(xml_detail, 'impuestos')
            xml_tax = ElementTree.SubElement(xml_taxes, 'impuesto')
            ElementTree.SubElement(xml_tax, 'codigo').text = str(TAX_CODES[0][0])
            if detail.product.has_tax:
                ElementTree.SubElement(xml_tax, 'codigoPorcentaje').text = str(self.company.tax_percentage)
                ElementTree.SubElement(xml_tax, 'tarifa').text = f'{detail.tax_rate:.2f}'
                ElementTree.SubElement(xml_tax, 'baseImponible').text = f'{detail.total_amount:.2f}'
                ElementTree.SubElement(xml_tax, 'valor').text = f'{detail.total_tax:.2f}'
            else:
                ElementTree.SubElement(xml_tax, 'codigoPorcentaje').text = '0'
                ElementTree.SubElement(xml_tax, 'tarifa').text = '0'
                ElementTree.SubElement(xml_tax, 'baseImponible').text = f'{detail.total_amount:.2f}'
                ElementTree.SubElement(xml_tax, 'valor').text = '0'

        xml_additional_info = ElementTree.SubElement(root, 'infoAdicional')
        if self.invoice.customer.address:
            ElementTree.SubElement(xml_additional_info, 'campoAdicional', nombre='dirCliente').text = self.invoice.customer.address
        if self.invoice.customer.mobile:
            ElementTree.SubElement(xml_additional_info, 'campoAdicional', nombre='telfCliente').text = self.invoice.customer.mobile
        ElementTree.SubElement(xml_additional_info, 'campoAdicional', nombre='Observacion').text = f'NOTA_CREDITO # {self.receipt_number}'
        return ElementTree.tostring(root, xml_declaration=True, encoding='UTF-8').decode('UTF-8').replace("'", '"'), access_key

    def create_invoice_pdf(self):
        template_name = 'credit_note/invoice_pdf.html'
        return PDFCreator(template_name=template_name).create(context={'object': self})

    def return_product_stock(self):
        for detail in self.creditnotedetail_set.filter(product__is_inventoried=True):
            detail.product.stock += detail.quantity
            detail.product.save()

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        if self.pk and self.status == INVOICE_STATUS[1][0]:
            self.return_product_stock()
        super().save(force_insert=force_insert, force_update=force_update, using=using, update_fields=update_fields)

    def as_dict(self):
        item = super().as_dict()
        item['invoice'] = self.invoice.as_dict()
        item['motive'] = self.motive
        return item

    class Meta:
        verbose_name = 'Nota de Crédito'
        verbose_name_plural = 'Notas de Crédito'
        default_permissions = ()
        permissions = (
            ('view_credit_note_admin', 'Can view Nota de Crédito'),
            ('add_credit_note_admin', 'Can add Nota de Crédito'),
            ('delete_credit_note_admin', 'Can delete Nota de Crédito'),
            ('view_credit_note_customer', 'Can view Nota de Crédito | Cliente'),
            ('print_credit_note', 'Can print Nota de Crédito'),
        )
        ordering = ['id']
