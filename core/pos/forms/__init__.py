# Re-export de formularios y constantes para compatibilidad
from .company import CompanyForm, CompanyOnboardingForm
from .provider import ProviderForm
from .category import CategoryForm
from .product import ProductForm
from .purchase import PurchaseForm
from .account_payable import AccountPayablePaymentForm
from .customer import CustomerForm, CustomerUserForm
from .receipt import ReceiptForm
from .expense_type import ExpenseTypeForm
from .expense import ExpenseForm
from .promotion import PromotionForm
from .invoice import InvoiceForm
from .account_receivable import AccountReceivablePaymentForm
from .quotation import QuotationForm
from .credit_note import CreditNoteForm

from core.pos.models import (
    Company,
    Provider,
    Category,
    Product,
    Purchase,
    PurchaseDetail,
    AccountPayable,
    AccountPayablePayment,
    AccountReceivable,
    AccountReceivablePayment,
    Customer,
    Receipt,
    ExpenseType,
    Expense,
    Promotion,
    PromotionDetail,
    Invoice,
    InvoiceDetail,
    CreditNote,
    CreditNoteDetail,
    Quotation,
    QuotationDetail,
)

# Constantes
from core.pos.choices import (
    VOUCHER_TYPE,
    INVOICE_STATUS,
    IDENTIFICATION_TYPE,
    PAYMENT_TYPE,
)

__all__ = [
    # Forms
    'CompanyForm', 'CompanyOnboardingForm', 'ProviderForm', 'CategoryForm', 'ProductForm', 'PurchaseForm',
    'AccountPayablePaymentForm', 'CustomerForm', 'CustomerUserForm', 'ReceiptForm', 'ExpenseTypeForm',
    'ExpenseForm', 'PromotionForm', 'InvoiceForm', 'AccountReceivablePaymentForm', 'QuotationForm',
    'CreditNoteForm',
    # Modelos (back-compat)
    'Company', 'Provider', 'Category', 'Product', 'Purchase', 'PurchaseDetail', 'AccountPayable',
    'AccountPayablePayment', 'AccountReceivable', 'AccountReceivablePayment', 'Customer', 'Receipt',
    'ExpenseType', 'Expense', 'Promotion', 'PromotionDetail', 'Invoice', 'InvoiceDetail', 'CreditNote',
    'CreditNoteDetail', 'Quotation', 'QuotationDetail',
    # Constantes
    'VOUCHER_TYPE', 'INVOICE_STATUS', 'IDENTIFICATION_TYPE', 'PAYMENT_TYPE'
]