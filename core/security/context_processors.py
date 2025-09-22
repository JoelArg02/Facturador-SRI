from datetime import datetime

from core.pos.models import Company
from core.security.models import Dashboard


def site_settings(request):
    dashboard = Dashboard.objects.first()
    params = {
        'dashboard': dashboard,
        'date_joined': datetime.now(),
        'company': Company.objects.first(),
        'menu': dashboard.get_template_from_layout() if dashboard else 'hzt_body.html'
    }
    return params
