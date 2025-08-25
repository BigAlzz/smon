"""
Organizational Chart Views
"""

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_POST
from django.db.models import Count, Q
from django.contrib import messages
from .models import OrgUnit, Staff, KPA, OperationalPlanItem


@login_required
def org_chart_view(request):
    """Display the organizational chart page"""
    return render(request, 'core/org_chart.html')


def org_chart_simple_view(request):
    """Simple test version of org chart"""
    return render(request, 'core/org_chart_simple.html')


@require_http_methods(["GET"])
def org_chart_data_api(request):
    """API endpoint to get organizational chart data as JSON"""
    
    def build_tree_node(org_unit):
        """Recursively build tree structure for an org unit"""
        children = OrgUnit.objects.filter(parent=org_unit, is_active=True).order_by('name')

        # Get staff counts
        total_staff = Staff.objects.filter(org_unit=org_unit, is_active=True).count()
        permanent_staff = Staff.objects.filter(org_unit=org_unit, is_active=True, employment_type='PERMANENT').count()
        contract_staff = Staff.objects.filter(org_unit=org_unit, is_active=True, employment_type='CONTRACT').count()
        managers = Staff.objects.filter(org_unit=org_unit, is_active=True, is_manager=True).count()

        node = {
            'id': str(org_unit.id),
            'name': org_unit.name,
            'type': org_unit.unit_type,
            'type_display': org_unit.get_unit_type_display(),
            'staff_count': total_staff,
            'staff_breakdown': {
                'total': total_staff,
                'permanent': permanent_staff,
                'contract': contract_staff,
                'managers': managers
            },
            'children': []
        }

        for child in children:
            node['children'].append(build_tree_node(child))

        return node
    
    # Get all root nodes (CEO Office and Chief Directorates with no parent)
    root_units = OrgUnit.objects.filter(
        parent__isnull=True, 
        is_active=True
    ).order_by('unit_type', 'name')
    
    # Build the tree structure
    tree_data = []
    for root_unit in root_units:
        tree_data.append(build_tree_node(root_unit))
    
    return JsonResponse({
        'success': True,
        'data': tree_data,
        'total_units': OrgUnit.objects.filter(is_active=True).count()
    })


@login_required
def org_unit_detail_view(request, unit_id):
    """Detailed view of an organizational unit"""
    try:
        unit = get_object_or_404(OrgUnit, id=unit_id, is_active=True)
    except:
        # If unit not found, redirect to org chart with error message
        from django.contrib import messages
        from django.shortcuts import redirect
        messages.error(request, f'Organizational unit not found. The unit may have been reorganized.')
        return redirect('org_chart')

    # Get staff members
    staff_members = Staff.objects.filter(org_unit=unit, is_active=True).order_by('last_name', 'first_name')

    # Get staff statistics
    staff_stats = {
        'total': staff_members.count(),
        'permanent': staff_members.filter(employment_type='PERMANENT').count(),
        'contract': staff_members.filter(employment_type='CONTRACT').count(),
        'temporary': staff_members.filter(employment_type='TEMPORARY').count(),
        'managers': staff_members.filter(is_manager=True).count(),
    }

    # Get KPAs associated with this unit
    kpas = KPA.objects.filter(org_units=unit, is_active=True).order_by('order', 'title')

    # Get operational plan items
    operational_items = OperationalPlanItem.objects.filter(
        kpa__org_units=unit,
        is_active=True
    ).order_by('kpa__order', 'output')

    # Get child units
    child_units = OrgUnit.objects.filter(parent=unit, is_active=True).order_by('name')

    # Get parent hierarchy
    hierarchy = []
    current = unit
    while current:
        hierarchy.insert(0, current)
        current = current.parent

    context = {
        'unit': unit,
        'staff_members': staff_members,
        'staff_stats': staff_stats,
        'kpas': kpas,
        'operational_items': operational_items,
        'child_units': child_units,
        'hierarchy': hierarchy,
    }

    return render(request, 'core/org_unit_detail.html', context)


@staff_member_required
def admin_org_chart_view(request):
    """Admin-accessible organizational chart view"""
    return render(request, 'admin/core/org_chart.html', {
        'title': 'Organizational Chart',
        'opts': OrgUnit._meta,
        'has_view_permission': True,
    })


# @login_required
def staff_directory_view_deprecated(request):
    """Staff directory with search and filtering"""
    from django.core.paginator import Paginator
    from django.db.models import Q

    # Get filter parameters
    unit_filter = request.GET.get('unit', '')
    level_filter = request.GET.get('level', '')
    search_query = request.GET.get('search', '')

    # Base queryset
    staff = Staff.objects.filter(is_active=True).select_related('org_unit')

    # Apply filters
    if unit_filter:
        staff = staff.filter(org_unit_id=unit_filter)

    if level_filter:
        staff = staff.filter(salary_level=level_filter)

    if search_query:
        staff = staff.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(persal_number__icontains=search_query) |
            Q(job_title__icontains=search_query)
        )

    # Handle sorting
    sort_field = request.GET.get('sort', 'last_name')
    sort_order = request.GET.get('order', 'asc')

    # Define allowed sort fields to prevent SQL injection
    allowed_sort_fields = {
        'name': 'last_name',
        'first_name': 'first_name',
        'last_name': 'last_name',
        'job_title': 'job_title',
        'org_unit': 'org_unit__name',
        'persal_number': 'persal_number',
        'start_date': 'start_date',
        'salary_level': 'salary_level',
    }

    if sort_field in allowed_sort_fields:
        order_by = allowed_sort_fields[sort_field]
        if sort_order == 'desc':
            order_by = f'-{order_by}'
    else:
        order_by = 'last_name'

    # Add secondary sort to ensure consistent ordering
    if sort_field not in ['last_name', 'name']:
        order_by = [order_by, 'last_name', 'first_name']
    else:
        order_by = [order_by, 'first_name']

    staff = staff.order_by(*order_by)

    # Pagination
    paginator = Paginator(staff, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Get filter options
    org_units = OrgUnit.objects.filter(is_active=True).order_by('name')
    salary_levels = Staff.SALARY_LEVEL_CHOICES

    # Statistics
    total_staff = Staff.objects.filter(is_active=True).count()
    managers_count = Staff.objects.filter(is_active=True, is_manager=True).count()

    context = {
        'page_obj': page_obj,
        'org_units': org_units,
        'salary_levels': salary_levels,
        'current_filters': {
            'unit': unit_filter,
            'level': level_filter,
            'search': search_query,
        },
        'statistics': {
            'total_staff': total_staff,
            'managers_count': managers_count,
        }
    }

    return render(request, 'core/staff_directory.html', context)


@login_required
def staff_detail_view(request, staff_id):
    """Individual staff member detail view"""
    staff = get_object_or_404(Staff, id=staff_id, is_active=True)

    # Get colleagues in the same unit
    colleagues = Staff.objects.filter(
        org_unit=staff.org_unit,
        is_active=True
    ).exclude(id=staff.id).order_by('last_name', 'first_name')[:10]

    # Get direct reports if this person is a manager
    direct_reports = Staff.objects.filter(
        org_unit__parent=staff.org_unit,
        is_active=True
    ).order_by('last_name', 'first_name') if staff.is_manager else None

    context = {
        'staff': staff,
        'colleagues': colleagues,
        'direct_reports': direct_reports,
    }

    return render(request, 'core/staff_detail.html', context)


@login_required
def staff_accounts_view(request):
    """Comprehensive staff and user account management view"""
    from django.contrib.auth.models import User
    from accounts.models import UserProfile
    from django.core.paginator import Paginator
    from django.db.models import Q

    # Get filter parameters
    unit_filter = request.GET.get('unit', '')
    account_status = request.GET.get('account_status', 'all')  # all, linked, unlinked
    search_query = request.GET.get('search', '')

    # Base queryset - all active staff with their user accounts
    staff_queryset = Staff.objects.filter(is_active=True).select_related(
        'user_profile__user', 'org_unit'
    )

    # Apply filters
    if unit_filter:
        staff_queryset = staff_queryset.filter(org_unit_id=unit_filter)

    if account_status == 'linked':
        staff_queryset = staff_queryset.filter(user_profile__isnull=False)
    elif account_status == 'unlinked':
        staff_queryset = staff_queryset.filter(user_profile__isnull=True)

    if search_query:
        staff_queryset = staff_queryset.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(persal_number__icontains=search_query) |
            Q(job_title__icontains=search_query) |
            Q(user_profile__user__username__icontains=search_query) |
            Q(user_profile__user__email__icontains=search_query)
        )

    # Handle sorting
    sort_field = request.GET.get('sort', 'last_name')
    sort_order = request.GET.get('order', 'asc')

    allowed_sort_fields = {
        'name': 'last_name',
        'job_title': 'job_title',
        'org_unit': 'org_unit__name',
        'persal_number': 'persal_number',
        'account_status': 'user_profile__user__username',
    }

    if sort_field in allowed_sort_fields:
        order_by = allowed_sort_fields[sort_field]
        if sort_order == 'desc':
            order_by = f'-{order_by}'
    else:
        order_by = 'last_name'

    staff_queryset = staff_queryset.order_by(order_by, 'first_name')

    # Get users without staff links
    users_without_staff = User.objects.filter(
        profile__staff_member__isnull=True,
        is_active=True
    ).select_related('profile').order_by('last_name', 'first_name')

    # Pagination
    paginator = Paginator(staff_queryset, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Statistics
    total_staff = Staff.objects.filter(is_active=True).count()
    staff_with_accounts = Staff.objects.filter(
        user_profile__isnull=False,
        is_active=True
    ).count()
    managers_count = Staff.objects.filter(is_manager=True, is_active=True).count()

    # Get organizational units for filtering
    org_units = OrgUnit.objects.filter(
        staff_members__is_active=True
    ).distinct().order_by('name')

    # Determine user capabilities
    current_user_profile = getattr(request.user, 'profile', None)
    user_capabilities = {
        'can_edit_profiles': current_user_profile and current_user_profile.primary_role in [
            'SYSTEM_ADMIN', 'SENIOR_MANAGER', 'PROGRAMME_MANAGER'
        ],
        'can_link_accounts': current_user_profile and current_user_profile.primary_role in [
            'SYSTEM_ADMIN', 'SENIOR_MANAGER'
        ],
        'can_create_accounts': current_user_profile and current_user_profile.primary_role in [
            'SYSTEM_ADMIN', 'SENIOR_MANAGER'
        ],
        'can_reset_passwords': current_user_profile and current_user_profile.primary_role in [
            'SYSTEM_ADMIN', 'SENIOR_MANAGER'
        ],
        'current_user_role': current_user_profile.get_primary_role_display() if current_user_profile else 'Unknown',
    }

    context = {
        'page_obj': page_obj,
        'users_without_staff': users_without_staff,
        'org_units': org_units,
        'current_filters': {
            'unit': unit_filter,
            'account_status': account_status,
            'search': search_query,
            'sort': sort_field,
            'order': sort_order,
        },
        'statistics': {
            'total_staff': total_staff,
            'staff_with_accounts': staff_with_accounts,
            'staff_without_accounts': total_staff - staff_with_accounts,
            'managers_count': managers_count,
            'coverage_percentage': round((staff_with_accounts / total_staff * 100), 1) if total_staff > 0 else 0,
            'users_without_staff_count': users_without_staff.count(),
        },
        'user_capabilities': user_capabilities,
    }

    return render(request, 'core/staff_accounts.html', context)


@login_required
@require_POST
def staff_edit_phone_view(request, staff_id):
    """Edit staff member phone numbers"""
    staff = get_object_or_404(Staff, id=staff_id, is_active=True)

    # Check permissions: staff member can edit their own, or user has change_staff permission
    can_edit = False
    if hasattr(staff, 'user_profile') and staff.user_profile and staff.user_profile.user == request.user:
        can_edit = True
    elif request.user.has_perm('core.change_staff'):
        can_edit = True

    if not can_edit:
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)

    try:
        # Update Staff model phone numbers
        staff.cell_number = request.POST.get('cell_number', '').strip()
        staff.phone = request.POST.get('phone', '').strip()
        staff.extension = request.POST.get('extension', '').strip()
        staff.save()

        # Update UserProfile phone numbers if they exist
        if hasattr(staff, 'user_profile') and staff.user_profile:
            profile = staff.user_profile
            profile.mobile_number = request.POST.get('profile_mobile', '').strip()
            profile.phone_number = request.POST.get('profile_phone', '').strip()
            profile.save()

        return JsonResponse({
            'success': True,
            'message': 'Contact information updated successfully'
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Failed to update contact information: {str(e)}'
        }, status=500)
