from django.urls import path

from core.report.views.account_payable_report.views import AccountPayableReportView
from core.report.views.account_receivable_report.views import AccountReceivableReportView
from core.report.views.earning_report.views import EarningReportView
from core.report.views.expense_report.views import ExpenseReportView
from core.report.views.invoice_report.views import InvoiceReportView
from core.report.views.purchase_report.views import PurchaseReportView
from core.report.views.result_report.views import ResultReportView

urlpatterns = [
    path('invoice/', InvoiceReportView.as_view(), name='invoice_report'),
    path('purchase/', PurchaseReportView.as_view(), name='purchase_report'),
    path('expense/', ExpenseReportView.as_view(), name='expense_report'),
    path('account/payable/', AccountPayableReportView.as_view(), name='account_payable_report'),
    path('account/receivable/', AccountReceivableReportView.as_view(), name='account_receivable_report'),
    path('result/', ResultReportView.as_view(), name='result_report'),
    path('earning/', EarningReportView.as_view(), name='earning_report'),
]
