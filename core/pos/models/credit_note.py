from django.db import models
from django.db.models import Sum, FloatField
from django.db.models.functions import Coalesce
from core.pos.choices import TAX_CODES, RETENTION_AGENT, VOUCHER_TYPE
from .billing_base import ElecBillingBase, ElecBillingDetailBase

class CreditNote(ElecBillingBase):
    invoice = models.ForeignKey('pos.Invoice', on_delete=models.PROTECT, verbose_name='Factura')
    motive = models.CharField(max_length=300, null=True, blank=True, help_text='Ingrese una descripción', verbose_name='Motivo')
    def __str__(self):
        return self.motive
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
        self.total_tax = round(float(self.creditnotedetail_set.filter(product__has_tax=True).aggregate(result=Coalesce(Sum('total_tax'), 0.00, output_field=FloatField()))['result']), 2)
        self.total_discount = float(self.creditnotedetail_set.filter().aggregate(result=Coalesce(Sum('total_discount'), 0.00, output_field=FloatField()))['result'])
        self.total_amount = round(self.subtotal, 2) + round(self.total_tax, 2)
        self.save()
    def recalculate_invoice(self):
        self.calculate_detail(); self.calculate_invoice()
    def create_invoice_pdf(self):
        from core.pos.utilities.pdf_creator import PDFCreator
        template_name = 'credit_note/invoice_pdf.html'
        return PDFCreator(template_name=template_name).create(context={'object': self})
    def return_product_stock(self):
        for detail in self.creditnotedetail_set.filter(product__is_inventoried=True):
            detail.product.stock += detail.quantity
            detail.product.save()
    def save(self, *args, **kwargs):
        from core.pos.choices import INVOICE_STATUS
        if self.pk and self.status == INVOICE_STATUS[1][0]:
            self.return_product_stock()
        super().save(*args, **kwargs)
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

class CreditNoteDetail(ElecBillingDetailBase):
    credit_note = models.ForeignKey(CreditNote, on_delete=models.CASCADE)
    invoice_detail = models.ForeignKey('pos.InvoiceDetail', on_delete=models.CASCADE)
    def __str__(self):
        return self.product.name
    def as_dict(self):
        return super().as_dict()
    class Meta:
        verbose_name = 'Detalle Devolución Ventas'
        verbose_name_plural = 'Detalle Devoluciones Ventas'
        default_permissions = ()
        ordering = ['id']
