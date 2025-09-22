import json

from django.db.models import Q
from django.http import HttpResponse
from django.views.generic import ListView

from core.pos.models import AccountPayable
from core.report.forms import ReportForm
from core.security.mixins import GroupModuleMixin


class AccountPayableReportView(GroupModuleMixin, ListView):
    model = AccountPayable
    template_name = 'account_payable_report/report.html'

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
                for i in self.model.objects.filter(filters):
                    data.append(i.as_dict())
            else:
                data['error'] = 'No ha seleccionado ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Reporte de {self.model._meta.verbose_name_plural}'
        context['form'] = ReportForm()
        return context
