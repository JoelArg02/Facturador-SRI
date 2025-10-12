from django.urls import path
from core.api.views import InvoiceAPIView

urlpatterns = [
    path('invoice/create/', InvoiceAPIView.as_view(), name='api_invoice_create'),
]
