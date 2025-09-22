import calendar
import json
from datetime import datetime

from django.db.models import Sum, FloatField, Q
from django.db.models.functions import Coalesce
from django.http import HttpResponse
from django.views.generic import FormView

from core.pos.models import Purchase, Invoice, Expense
from core.report.forms import ReportForm
from core.security.mixins import GroupModuleMixin


class ResultReportView(GroupModuleMixin, FormView):
    template_name = 'result_report/report.html'
    form_class = ReportForm

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        date_joined = datetime.now().date()
        month_range = list(calendar.monthrange(date_joined.year, date_joined.month))[-1]
        month = f'0{date_joined.month}' if date_joined.month < 10 else date_joined.month
        form.fields['date_range'].initial = f"{date_joined.year}-{month}-01 - {date_joined.year}-{month}-{month_range}"
        return form

    def post(self, request, *args, **kwargs):
        action = request.POST['action']
        data = {}
        try:
            if action == 'search':
                data = []
                start_date = request.POST['start_date']
                end_date = request.POST['end_date']
                filters = Q()
                if len(start_date) and len(end_date):
                    filters &= Q(date_joined__range=[start_date, end_date])
                total_purchase = float(Purchase.objects.filter(filters).aggregate(result=Coalesce(Sum('total_amount'), 0.00, output_field=FloatField()))['result'])
                total_invoice = float(Invoice.objects.filter(filters).aggregate(result=Coalesce(Sum('total_amount'), 0.00, output_field=FloatField()))['result'])
                total_expense = float(Expense.objects.filter(filters).aggregate(result=Coalesce(Sum('amount'), 0.00, output_field=FloatField()))['result'])
                data.append({'name': 'Compras', 'y': total_purchase})
                data.append({'name': 'Ventas', 'y': total_invoice})
                data.append({'name': 'Gastos', 'y': total_expense})
            else:
                data['error'] = 'No ha seleccionado ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Reporte de Resultados'
        return context
