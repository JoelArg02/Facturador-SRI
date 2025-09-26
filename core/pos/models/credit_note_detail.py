from django.db import models

from core.pos.models.elec_billing_detail_base import ElecBillingDetailBase


class CreditNoteDetail(ElecBillingDetailBase):
    credit_note = models.ForeignKey('pos.CreditNote', on_delete=models.CASCADE)
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
