from django.db import models

from core.pos.models.elec_billing_detail_base import ElecBillingDetailBase


class InvoiceDetail(ElecBillingDetailBase):
    invoice = models.ForeignKey('pos.Invoice', on_delete=models.CASCADE)

    def __str__(self):
        return self.product.name

    def deduct_product_stock(self):
        invoice = self.invoice
        if (not invoice.is_draft_invoice and invoice.create_electronic_invoice) or invoice.receipt.is_ticket:
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
