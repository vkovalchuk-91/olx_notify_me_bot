from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = 'web'

urlpatterns = [
    path('login/', auth_views.LoginView.as_view(template_name='web/login.html'), name='login'),
    path('register/', views.register, name='register'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('', views.dashboard, name='dashboard'),
    path('queries/', views.queries_list, name='queries_list'),
    path('queries/add/url/', views.query_add_by_url, name='query_add_url'),
    path('queries/add/text/', views.query_add_by_text, name='query_add_text'),
    path('olx/monitors/', views.olx_queries_list, name='olx_queries'),
    path('olx/add/url/', views.olx_query_add_by_url, name='olx_query_add_url'),
    path('olx/add/text/', views.query_add_by_text, name='olx_query_add_text'),
    path('olx/ads/', views.olx_found_ads_list, name='olx_found_ads'),
    path('rieltor/monitors/', views.rieltor_queries_list, name='rieltor_queries'),
    path('rieltor/add/url/', views.rieltor_query_add_by_url, name='rieltor_query_add_url'),
    path('rieltor/ads/', views.rieltor_found_ads_list, name='rieltor_found_ads'),
    path('queries/<int:query_id>/toggle/', views.query_toggle, name='query_toggle'),
    path('queries/<int:query_id>/delete/', views.query_delete, name='query_delete'),
    path('found-ads/', views.found_ads_list, name='found_ads'),
    path('insta/users/', views.insta_users_list, name='insta_users'),
    path('insta/users/<int:user_id>/toggle/', views.insta_user_toggle, name='insta_user_toggle'),
    path('insta/users/<int:user_id>/delete/', views.insta_user_delete, name='insta_user_delete'),
    path('insta/content/', views.insta_content_list, name='insta_content'),
    path('insta/content/<int:content_id>/preview/', views.insta_content_preview, name='insta_content_preview'),
    path('jobs/check-ads/', views.trigger_check_ads, name='trigger_check_ads'),
    path('jobs/check-olx/', views.trigger_check_olx, name='trigger_check_olx'),
    path('jobs/check-rieltor/', views.trigger_check_rieltor, name='trigger_check_rieltor'),
    path('jobs/check-insta/', views.trigger_check_insta, name='trigger_check_insta'),
    path('admin/users/', views.admin_users, name='admin_users'),
    path('admin/users/<int:user_id>/edit/', views.admin_user_edit, name='admin_user_edit'),
    path('admin/logs/', views.admin_logs, name='admin_logs'),
]
