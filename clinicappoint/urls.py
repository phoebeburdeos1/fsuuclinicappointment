"""
URL configuration for clinicappoint project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from admin_dashboard.views import inventory_view, staff_dashboard

urlpatterns = [
    path('', include('accounts.urls')),
    path('admin-dashboard/', include('admin_dashboard.urls')),
    path('staff-dashboard/', staff_dashboard, name='staff_dashboard'),
    path('inventory/', inventory_view, name='inventory'),
    path('dashboard/', include('patient_dashboard.urls')),
    path('admin/', admin.site.urls),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
