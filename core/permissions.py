"""
Custom permission classes and decorators for KPA Monitoring system

This module provides role-based access control (RBAC) with data partitioning
by organizational unit and year.
"""

from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from rest_framework import permissions
from functools import wraps
from .models import KPA, OperationalPlanItem


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    """
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed for any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions are only allowed to the owner of the object.
        return obj.created_by == request.user


class KPAPermission(permissions.BasePermission):
    """
    Custom permission for KPA access based on user role and ownership
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        user_profile = getattr(request.user, 'profile', None)
        if not user_profile:
            return False
        
        # System admins and M&E Strategy can access all KPAs
        if user_profile.primary_role in ['SYSTEM_ADMIN', 'ME_STRATEGY']:
            return True
        
        # Senior managers can view KPAs they own
        if user_profile.primary_role == 'SENIOR_MANAGER':
            return True
        
        # Programme managers can view KPAs they're assigned to
        if user_profile.primary_role == 'PROGRAMME_MANAGER':
            return True
        
        return False

    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        
        user_profile = getattr(request.user, 'profile', None)
        if not user_profile:
            return False
        
        # System admins can do anything
        if user_profile.primary_role == 'SYSTEM_ADMIN':
            return True
        
        # M&E Strategy can view and edit all KPAs
        if user_profile.primary_role == 'ME_STRATEGY':
            return True
        
        # Senior managers can edit KPAs they own
        if user_profile.primary_role == 'SENIOR_MANAGER':
            if request.method in permissions.SAFE_METHODS:
                return True  # Can view any KPA
            return obj.owner == request.user  # Can only edit owned KPAs
        
        # Programme managers can only view KPAs they're assigned to
        if user_profile.primary_role == 'PROGRAMME_MANAGER':
            if request.method in permissions.SAFE_METHODS:
                # Check if user is assigned to any plan items in this KPA
                return obj.plan_items.filter(
                    responsible_officer__icontains=request.user.get_full_name()
                ).exists()
            return False  # Cannot edit KPAs
        
        return False


class OperationalPlanItemPermission(permissions.BasePermission):
    """
    Custom permission for Operational Plan Item access
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        user_profile = getattr(request.user, 'profile', None)
        if not user_profile:
            return False
        
        # All authenticated users with profiles can view plan items
        return True

    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        
        user_profile = getattr(request.user, 'profile', None)
        if not user_profile:
            return False
        
        # Use the can_edit_plan_item method from UserProfile
        if request.method in permissions.SAFE_METHODS:
            # For read operations, check if user can access the KPA
            return user_profile.get_accessible_kpas().filter(id=obj.kpa.id).exists()
        else:
            # For write operations, use the specific edit permission
            return user_profile.can_edit_plan_item(obj)


class ProgressUpdatePermission(permissions.BasePermission):
    """
    Custom permission for Progress Update access
    """
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        
        user_profile = getattr(request.user, 'profile', None)
        if not user_profile:
            return False
        
        # Check if user can edit the related plan item
        return user_profile.can_edit_plan_item(obj.target.plan_item)


# Decorator functions for view-based permissions
def require_role(*roles):
    """
    Decorator to require specific user roles
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                raise PermissionDenied("Authentication required")
            
            user_profile = getattr(request.user, 'profile', None)
            if not user_profile:
                raise PermissionDenied("User profile required")
            
            if user_profile.primary_role not in roles:
                raise PermissionDenied(f"Role {user_profile.primary_role} not authorized")
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def require_kpa_access(kpa_param='kpa_id'):
    """
    Decorator to require access to a specific KPA
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                raise PermissionDenied("Authentication required")
            
            user_profile = getattr(request.user, 'profile', None)
            if not user_profile:
                raise PermissionDenied("User profile required")
            
            # Get KPA ID from URL parameters
            kpa_id = kwargs.get(kpa_param)
            if not kpa_id:
                raise PermissionDenied("KPA ID required")
            
            # Check if user can access this KPA
            kpa = get_object_or_404(KPA, id=kpa_id)
            accessible_kpas = user_profile.get_accessible_kpas()
            
            if not accessible_kpas.filter(id=kpa.id).exists():
                raise PermissionDenied("Access to this KPA not authorized")
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def require_plan_item_edit_access(plan_item_param='plan_item_id'):
    """
    Decorator to require edit access to a specific operational plan item
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                raise PermissionDenied("Authentication required")
            
            user_profile = getattr(request.user, 'profile', None)
            if not user_profile:
                raise PermissionDenied("User profile required")
            
            # Get plan item ID from URL parameters
            plan_item_id = kwargs.get(plan_item_param)
            if not plan_item_id:
                raise PermissionDenied("Plan item ID required")
            
            # Check if user can edit this plan item
            plan_item = get_object_or_404(OperationalPlanItem, id=plan_item_id)
            
            if not user_profile.can_edit_plan_item(plan_item):
                raise PermissionDenied("Edit access to this plan item not authorized")
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


# Helper functions for permission checking
def user_can_approve_updates(user):
    """Check if user can approve progress updates"""
    if not user.is_authenticated:
        return False
    
    user_profile = getattr(user, 'profile', None)
    if not user_profile:
        return False
    
    return user_profile.can_approve_updates


def user_can_generate_reports(user):
    """Check if user can generate reports"""
    if not user.is_authenticated:
        return False
    
    user_profile = getattr(user, 'profile', None)
    if not user_profile:
        return False
    
    return user_profile.can_generate_reports


def user_can_view_all_kpas(user):
    """Check if user can view all KPAs"""
    if not user.is_authenticated:
        return False
    
    user_profile = getattr(user, 'profile', None)
    if not user_profile:
        return False
    
    return user_profile.can_view_all_kpas or user_profile.primary_role in [
        'SYSTEM_ADMIN', 'SENIOR_MANAGER', 'ME_STRATEGY'
    ]


# Data filtering functions for queryset-level permissions
def filter_kpas_for_user(queryset, user):
    """Filter KPAs based on user permissions"""
    if not user.is_authenticated:
        return queryset.none()
    
    user_profile = getattr(user, 'profile', None)
    if not user_profile:
        return queryset.none()
    
    return user_profile.get_accessible_kpas().filter(id__in=queryset.values_list('id', flat=True))


def filter_plan_items_for_user(queryset, user):
    """Filter operational plan items based on user permissions"""
    if not user.is_authenticated:
        return queryset.none()

    user_profile = getattr(user, 'profile', None)
    if not user_profile:
        return queryset.none()

    accessible_kpas = user_profile.get_accessible_kpas()
    return queryset.filter(kpa__in=accessible_kpas)


def require_manager_role(view_func):
    """
    Decorator to require manager role (Senior Manager, Programme Manager, or staff marked as manager)
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            raise PermissionDenied("Authentication required")

        user_profile = getattr(request.user, 'profile', None)

        # Check if user has manager role in profile
        if user_profile and user_profile.primary_role in ['SENIOR_MANAGER', 'PROGRAMME_MANAGER']:
            return view_func(request, *args, **kwargs)

        # Check if user is marked as manager in staff records
        try:
            from .models import Staff
            staff_record = Staff.objects.get(email=request.user.email, is_active=True, is_manager=True)
            return view_func(request, *args, **kwargs)
        except Staff.DoesNotExist:
            pass

        # Check if user owns any KPAs (makes them a manager)
        from .models import KPA
        if KPA.objects.filter(owner=request.user, is_active=True).exists():
            return view_func(request, *args, **kwargs)

        raise PermissionDenied("Manager role required")

    return wrapper
