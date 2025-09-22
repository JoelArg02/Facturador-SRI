import json

from django.db.models import Q
from django.http import HttpResponse
from django.views.generic import FormView

from core.pos.models import Product
from core.report.forms import ReportForm
from core.security.mixins import GroupModuleMixin


class EarningReportView(GroupModuleMixin, FormView):
    template_name = 'earning_report/report.html'
    form_class = ReportForm

    def post(self, request, *args, **kwargs):
        action = request.POST['action']
        data = {}
        try:
            if action == 'search':
                data = []
                product_id = json.loads(request.POST['product_id'])
                filters = Q()
                if len(product_id):
                    filters &= Q(id__in=product_id)
                for i in Product.objects.filter(filters):
                    item = i.as_dict()
                    item['benefit'] = float(i.get_benefit())
                    data.append(item)
            elif action == 'search_graph':
                product_id = json.loads(request.POST['product_id'])
                filters = Q()
                if len(product_id):
                    filters &= Q(id__in=product_id)
                queryset = Product.objects.filter(filters).order_by('name')
                categories = [i.name for i in queryset]
                series = []
                series.append({'name': 'P./Compra', 'data': [float(i.price) for i in queryset]})
                series.append({'name': 'P./Venta', 'data': [float(i.pvp) for i in queryset]})
                series.append({'name': 'Ganancia', 'data': [float(i.get_benefit()) for i in queryset]})
                data = {'categories': categories, 'series': series}
            else:
                data['error'] = 'No ha seleccionado ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Reporte de Ganancias de Productos'
        return context
