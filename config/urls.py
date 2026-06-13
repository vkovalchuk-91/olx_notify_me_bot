from django.contrib import admin
from django.urls import include, path

from apps.web import views as web_views

urlpatterns = [
    path('admin/logs/', web_views.admin_logs, name='admin_logs'),
    path('admin/users/', web_views.admin_users, name='admin_users'),
    path('admin/users/<int:user_id>/edit/', web_views.admin_user_edit, name='admin_user_edit'),
    path('admin/', admin.site.urls),
    path('api/', include('apps.api.urls')),
    path('', include('apps.web.urls')),
]
