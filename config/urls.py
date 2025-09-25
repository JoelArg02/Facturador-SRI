from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

from config import settings
from core.dashboard.views import *

urlpatterns = [
    path('admin/', admin.site.urls),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('login/', include('core.login.urls')),
    path('pos/', include('core.pos.urls')),
    path('report/', include('core.report.urls')),
    path('security/', include('core.security.urls')),
    path('user/', include('core.user.urls')),
    path('subscription/', include('core.subscription.urls')),
    path('', DashboardView.as_view(), name='dashboard'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
