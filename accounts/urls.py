"""
URL configuration for accounts app
"""

from django.urls import path
from .views import api_login, api_logout, api_profile, LoginView, logout_view, profile_view, change_password_view, user_management_view, user_detail_view, admin_edit_user_view

urlpatterns = [
    # Web views
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', logout_view, name='logout'),
    path('profile/', profile_view, name='profile'),
    path('change-password/', change_password_view, name='change_password'),
    path('users/', user_management_view, name='user_management'),
    path('users/<int:user_id>/', user_detail_view, name='user_detail'),
    path('users/<int:user_id>/edit/', admin_edit_user_view, name='admin_edit_user'),
    
    # API endpoints
    path('api/login/', api_login, name='api_login'),
    path('api/logout/', api_logout, name='api_logout'),
    path('api/profile/', api_profile, name='api_profile'),
]
