from datetime import datetime

from core.pos.models import Company
from core.security.models import Dashboard
from core.security.choices import LAYOUT_OPTIONS


def site_settings(request):
    dashboard = Dashboard.objects.first()
    # Elegir layout a usar: si usuario autenticado tiene preferencia, usarla; de lo contrario usar del dashboard
    template_menu = 'hzt_body.html'
    try:
        if request.user.is_authenticated:
            user_layout = getattr(request.user, 'layout', None)
            if user_layout == LAYOUT_OPTIONS[0][0]:
                template_menu = 'vtc_body.html'
            elif user_layout == LAYOUT_OPTIONS[1][0]:
                template_menu = 'hzt_body.html'
            else:
                # fallback a dashboard
                template_menu = dashboard.get_template_from_layout() if dashboard else 'hzt_body.html'
        else:
            template_menu = dashboard.get_template_from_layout() if dashboard else 'hzt_body.html'
    except Exception:
        template_menu = dashboard.get_template_from_layout() if dashboard else 'hzt_body.html'

    params = {
        'dashboard': dashboard,
        'date_joined': datetime.now(),
        'company': Company.objects.first(),
        'menu': template_menu,
    }
    return params
