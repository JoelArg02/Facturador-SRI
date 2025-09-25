from django.db import models, transaction
from django.db.models import Sum, FloatField
from django.db.models.functions import Coalesce
from django.forms import model_to_dict
from core.pos.choices import PAYMENT_TYPE, INVOICE_PAYMENT_METHOD, VOUCHER_TYPE, TAX_CODES, RETENTION_AGENT
from .billing_base import ElecBillingBase, ElecBillingDetailBase
from .catalog import Receipt
from .company import Company

class Invoice(ElecBillingBase):
    customer = models.ForeignKey('pos.Customer', on_delete=models.PROTECT, verbose_name='Cliente')
    employee = models.ForeignKey('user.User', null=True, blank=True, on_delete=models.PROTECT, verbose_name='Empleado')
    payment_type = models.CharField(choices=PAYMENT_TYPE, max_length=50, default=PAYMENT_TYPE[0][0], verbose_name='Forma de pago')
    payment_method = models.CharField(choices=INVOICE_PAYMENT_METHOD, max_length=50, default=INVOICE_PAYMENT_METHOD[5][0], verbose_name='Método de pago')
    time_limit = models.IntegerField(default=31, verbose_name='Plazo')
    end_credit = models.DateField(default=__import__('datetime').datetime.now, verbose_name='Fecha limite de crédito')
    cash = models.DecimalField(max_digits=9, decimal_places=2, default=0.00, verbose_name='Efectivo recibido')
    change = models.DecimalField(max_digits=9, decimal_places=2, default=0.00, verbose_name='Cambio')
    is_draft_invoice = models.BooleanField(default=False, verbose_name='Factura borrador')
    def __str__(self):
        return self.get_full_name()
    @property
    def subtotal_without_taxes(self):
        return float(self.invoicedetail_set.filter().aggregate(result=Coalesce(Sum('subtotal'), 0.00, output_field=FloatField()))['result'])
    def get_full_name(self):
        return f'{self.receipt_number_full} / {self.customer.user.names})'
    def calculate_detail(self):
        for detail in self.invoicedetail_set.filter():
            detail.price = float(detail.price)
            detail.tax = float(self.tax)
            detail.price_with_tax = detail.price + (detail.price * detail.tax)
            detail.subtotal = detail.price * detail.quantity
            detail.total_discount = detail.subtotal * float(detail.discount)
            detail.total_tax = (detail.subtotal - detail.total_discount) * detail.tax
            detail.total_amount = detail.subtotal - detail.total_discount
            detail.save()
    def calculate_invoice(self):
        self.subtotal_without_tax = float(self.invoicedetail_set.filter(product__has_tax=False).aggregate(result=Coalesce(Sum('total_amount'), 0.00, output_field=FloatField()))['result'])
        self.subtotal_with_tax = float(self.invoicedetail_set.filter(product__has_tax=True).aggregate(result=Coalesce(Sum('total_amount'), 0.00, output_field=FloatField()))['result'])
        self.total_tax = round(float(self.invoicedetail_set.filter(product__has_tax=True).aggregate(result=Coalesce(Sum('total_tax'), 0.00, output_field=FloatField()))['result']), 2)
        self.total_discount = float(self.invoicedetail_set.filter().aggregate(result=Coalesce(Sum('total_discount'), 0.00, output_field=FloatField()))['result'])
        self.total_amount = round(self.subtotal, 2) + float(self.total_tax)
        self.save()
    def recalculate_invoice(self):
        self.calculate_detail(); self.calculate_invoice()
    def create_xml_document(self):
        from core.pos.utilities.sri import SRI
        access_key = SRI().create_access_key(self)
        from xml.etree import ElementTree
        root = ElementTree.Element('factura', id="comprobante", version="1.0.0")
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
        if self.company.retention_agent == RETENTION_AGENT[0][0]:
            ElementTree.SubElement(xml_tax_info, 'agenteRetencion').text = '1'
        xml_info_invoice = ElementTree.SubElement(root, 'infoFactura')
        ElementTree.SubElement(xml_info_invoice, 'fechaEmision').text = __import__('datetime').datetime.now().strftime('%d/%m/%Y')
        ElementTree.SubElement(xml_info_invoice, 'dirEstablecimiento').text = self.company.establishment_address
        ElementTree.SubElement(xml_info_invoice, 'obligadoContabilidad').text = self.company.obligated_accounting
        ElementTree.SubElement(xml_info_invoice, 'tipoIdentificacionComprador').text = self.customer.identification_type
        ElementTree.SubElement(xml_info_invoice, 'razonSocialComprador').text = self.customer.user.names
        ElementTree.SubElement(xml_info_invoice, 'identificacionComprador').text = self.customer.dni
        ElementTree.SubElement(xml_info_invoice, 'direccionComprador').text = self.customer.address
        ElementTree.SubElement(xml_info_invoice, 'totalSinImpuestos').text = f'{self.subtotal:.2f}'
        ElementTree.SubElement(xml_info_invoice, 'totalDescuento').text = f'{self.total_discount:.2f}'
        xml_total_with_taxes = ElementTree.SubElement(xml_info_invoice, 'totalConImpuestos')
        if self.subtotal_without_tax != 0.0000:
            subtotal_without_tax = ElementTree.SubElement(xml_total_with_taxes, 'totalImpuesto')
            ElementTree.SubElement(subtotal_without_tax, 'codigo').text = str(TAX_CODES[0][0])
            ElementTree.SubElement(subtotal_without_tax, 'codigoPorcentaje').text = '0'
            ElementTree.SubElement(subtotal_without_tax, 'baseImponible').text = f'{self.subtotal_without_tax:.2f}'
            ElementTree.SubElement(subtotal_without_tax, 'valor').text = '0.00'
        if self.subtotal_with_tax != 0.0000:
            subtotal_with_tax = ElementTree.SubElement(xml_total_with_taxes, 'totalImpuesto')
            ElementTree.SubElement(subtotal_with_tax, 'codigo').text = str(TAX_CODES[0][0])
            ElementTree.SubElement(subtotal_with_tax, 'codigoPorcentaje').text = str(self.company.tax_percentage)
            ElementTree.SubElement(subtotal_with_tax, 'baseImponible').text = f'{self.subtotal_with_tax:.2f}'
            ElementTree.SubElement(subtotal_with_tax, 'valor').text = f'{self.total_tax:.2f}'
        ElementTree.SubElement(xml_info_invoice, 'propina').text = '0.00'
        ElementTree.SubElement(xml_info_invoice, 'importeTotal').text = f'{self.total_amount:.2f}'
        ElementTree.SubElement(xml_info_invoice, 'moneda').text = 'DOLAR'
        xml_payments = ElementTree.SubElement(xml_info_invoice, 'pagos')
        xml_payment = ElementTree.SubElement(xml_payments, 'pago')
        ElementTree.SubElement(xml_payment, 'formaPago').text = self.payment_method
        ElementTree.SubElement(xml_payment, 'total').text = f'{self.total_amount:.2f}'
        ElementTree.SubElement(xml_payment, 'plazo').text = str(self.time_limit)
        ElementTree.SubElement(xml_payment, 'unidadTiempo').text = 'dias'
        xml_details = ElementTree.SubElement(root, 'detalles')
        for detail in self.invoicedetail_set.all():
            xml_detail = ElementTree.SubElement(xml_details, 'detalle')
            ElementTree.SubElement(xml_detail, 'codigoPrincipal').text = detail.product.code
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
        return ElementTree.tostring(root, xml_declaration=True, encoding='utf-8').decode('utf-8').replace("'", '"'), access_key
    def create_invoice_pdf(self):
        from core.pos.utilities.pdf_creator import PDFCreator
        template_name = 'invoice/invoice_pdf.html'
        return PDFCreator(template_name=template_name).create(context={'object': self})
    def as_dict(self):
        item = super().as_dict()
        item['text'] = self.get_full_name()
        item['customer'] = self.customer.as_dict()
        item['employee'] = self.employee.as_dict() if self.employee else dict()
        item['payment_method'] = {'id': self.payment_method, 'name': self.get_payment_method_display()}
        item['payment_type'] = {'id': self.payment_type, 'name': self.get_payment_type_display()}
        item['end_credit'] = self.end_credit.strftime('%Y-%m-%d')
        item['cash'] = float(self.cash)
        item['change'] = float(self.change)
        return item
    class Meta:
        verbose_name = 'Factura'
        verbose_name_plural = 'Facturas'
        default_permissions = ()
        permissions = (
            ('view_invoice_admin', 'Can view Factura'),
            ('add_invoice_admin', 'Can add Factura'),
            ('change_invoice_admin', 'Can update Factura'),
            ('delete_invoice_admin', 'Can delete Factura'),
            ('view_invoice_customer', 'Can view Factura | Cliente'),
            ('print_invoice', 'Can print Factura'),
        )
        ordering = ['id']

class InvoiceDetail(ElecBillingDetailBase):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE)
    def __str__(self):
        return self.product.name
    def deduct_product_stock(self):
        if (not self.invoice.is_draft_invoice and self.invoice.create_electronic_invoice) or self.invoice.receipt.is_ticket:
            if self.product.is_inventoried:
                self.product.stock -= self.quantity
                self.product.save()
    def as_dict(self):
        return super().as_dict()
    class Meta:
        verbose_name = 'Detalle de Factura'
        verbose_name_plural = 'Detalle de Facturas'
        default_permissions = ()
        ordering = ['id']
