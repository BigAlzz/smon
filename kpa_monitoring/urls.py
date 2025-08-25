"""
URL configuration for kpa_monitoring project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
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
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect
from accounts.views import (
    LoginView, logout_view, register_view, password_reset_view,
    password_reset_confirm_view, check_username_availability, check_persal_validity,
    change_password_view
)
from core.views import (
    dashboard_view,
    kpa_drilldown_view,
    plan_grid_view,
    plan_item_update_field,
    plan_item_create_view,
    kpa_list_view,
    kpa_create_view,
    kpa_edit_view,
    kpa_delete_view,
    target_create_view,
    item_detail_view,
    update_wizard_view,
    csrf_debug_view,
    csrf_test_view,
)
from core.views_orgchart import org_chart_view, org_chart_data_api, admin_org_chart_view, org_chart_simple_view, org_unit_detail_view, staff_detail_view, staff_accounts_view, staff_edit_phone_view
from core.views_manager import (
    manager_dashboard_view,
    manager_kpa_detail_view,
    manager_progress_update_view,
    manager_targets_overview_view,
    manager_evidence_delete_view,
    manager_approval_dashboard_view,
    manager_progress_approval_view,
    progress_success_view,
)

# API router
from rest_framework.routers import DefaultRouter
from core.api_views import (
    FinancialYearViewSet, KPAViewSet, OperationalPlanItemViewSet,
    TargetViewSet, ProgressUpdateViewSet,
)
router = DefaultRouter()
router.register(r'financial-years', FinancialYearViewSet)
router.register(r'kpas', KPAViewSet)
router.register(r'plan-items', OperationalPlanItemViewSet)
router.register(r'targets', TargetViewSet)
router.register(r'progress-updates', ProgressUpdateViewSet)


urlpatterns = [
    path('admin/', admin.site.urls),

    # Root -> dashboard (if not authenticated, login view handles redirect link)
    path('', dashboard_view, name='home'),

    # Authentication views
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', logout_view, name='logout'),
    path('register/', register_view, name='register'),
    path('password-reset/', password_reset_view, name='password_reset'),
    path('password-reset-confirm/<uidb64>/<token>/', password_reset_confirm_view, name='password_reset_confirm'),

    # Password management
    path('change-password/', change_password_view, name='change_password'),

    # AJAX endpoints
    path('accounts/check-username/', check_username_availability, name='check_username'),
    path('accounts/check-persal/', check_persal_validity, name='check_persal'),

    # Legacy aliases (avoid 404s if /accounts/login is used)
    path('accounts/login/', lambda request: redirect('login')),
    path('accounts/logout/', lambda request: redirect('logout')),

    # Account management
    path('accounts/', include('accounts.urls')),

    # Notifications
    path('notifications/', include('notifications.urls')),

    # Dashboard
    path('dashboard/', dashboard_view, name='dashboard'),

    # KPA management
    path('kpa/', kpa_list_view, name='kpa_list'),
    path('kpa/new/', kpa_create_view, name='kpa_create'),
    path('kpa/<uuid:kpa_id>/edit/', kpa_edit_view, name='kpa_edit'),
    path('kpa/<uuid:kpa_id>/delete/', kpa_delete_view, name='kpa_delete'),

    # Operational Plan grid
    path('plan/', plan_grid_view, name='plan_grid'),
    path('plan/new/', plan_item_create_view, name='plan_item_create'),

    # KPA Drilldown
    path('kpa/<uuid:kpa_id>/', kpa_drilldown_view, name='kpa_drilldown'),
    path('plan/item/<uuid:item_id>/target/new/', target_create_view, name='target_create'),
    path('plan/item/<uuid:item_id>/', item_detail_view, name='item_detail'),
    path('progress/update/<uuid:target_id>/', update_wizard_view, name='update_wizard'),

    # Organizational Chart
    path('org-chart/', org_chart_view, name='org_chart'),
    path('org-chart/simple/', org_chart_simple_view, name='org_chart_simple'),
    path('org-chart/data/', org_chart_data_api, name='org_chart_data'),
    path('org-unit/<uuid:unit_id>/', org_unit_detail_view, name='org_unit_detail'),
    path('admin/core/org-chart/', admin_org_chart_view, name='admin_org_chart'),

    # Staff User Accounts (consolidated)
    path('staff/', staff_accounts_view, name='staff_accounts'),
    path('staff/', staff_accounts_view, name='staff_directory'),  # Redirect old staff_directory to consolidated view
    path('staff/<uuid:staff_id>/', staff_detail_view, name='staff_detail'),
    path('staff/<uuid:staff_id>/edit-phone/', staff_edit_phone_view, name='staff_edit_phone'),
    path('user-management/', staff_accounts_view, name='user_management'),  # Alias for user management

    # API endpoints
    path('api/accounts/', include('accounts.urls')),
    path('api/', include(router.urls)),

    # Inline update for plan items
    path('plan/item/<uuid:item_id>/update-field', plan_item_update_field, name='plan_item_update_field'),

    # Manager Interface
    path('manager/', manager_dashboard_view, name='manager_dashboard'),
    path('manager/kpa/<uuid:kpa_id>/', manager_kpa_detail_view, name='manager_kpa_detail'),
    path('manager/target/<uuid:target_id>/update/', manager_progress_update_view, name='manager_progress_update'),
    path('manager/evidence/<uuid:evidence_id>/delete/', manager_evidence_delete_view, name='manager_evidence_delete'),
    path('manager/approvals/', manager_approval_dashboard_view, name='manager_approval_dashboard'),
    path('manager/approve/<uuid:update_id>/', manager_progress_approval_view, name='manager_progress_approval'),
    path('manager/targets/', manager_targets_overview_view, name='manager_targets_overview'),
    path('manager/success/<uuid:target_id>/', progress_success_view, name='progress_success'),

    # Debug endpoints
    path('debug/csrf/', csrf_debug_view, name='csrf_debug'),
    path('debug/csrf-test/', csrf_test_view, name='csrf_test'),
]

if settings.DEBUG:
    # Debug Toolbar
    try:
        import debug_toolbar
        urlpatterns = [path('__debug__/', include(debug_toolbar.urls))] + urlpatterns
    except Exception:
        pass

    # Static and media in development
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
