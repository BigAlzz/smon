"""
URL patterns for notifications app
"""

from django.urls import path
from . import views

urlpatterns = [
    # Main notification views
    path('', views.notification_inbox, name='notification_inbox'),
    path('inbox/', views.notification_inbox, name='notification_inbox'),
    path('compose/', views.compose_message, name='compose_message'),
    path('<uuid:notification_id>/', views.notification_detail, name='notification_detail'),
    
    # AJAX actions
    path('mark-read/<uuid:notification_id>/', views.mark_as_read, name='mark_notification_read'),
    path('acknowledge/<uuid:notification_id>/', views.acknowledge_notification, name='acknowledge_notification'),
    path('archive/<uuid:notification_id>/', views.archive_notification, name='archive_notification'),
    
    # API endpoints
    path('api/unread-count/', views.get_unread_count, name='api_unread_count'),
    path('api/recent/', views.get_recent_notifications, name='api_recent_notifications'),
]
