from django.db import models

from core.pos.models.elec_billing_detail_base import ElecBillingDetailBase


class QuotationDetail(ElecBillingDetailBase):
    quotation = models.ForeignKey('pos.Quotation', on_delete=models.CASCADE)

    def __str__(self):
        return self.quotation.__str__()

    def as_dict(self):
        return super().as_dict()

    class Meta:
        verbose_name = 'Proforma Detalle'
        verbose_name_plural = 'Proforma Detalles'
        default_permissions = ()
