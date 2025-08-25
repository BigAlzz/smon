"""
Admin configuration for accounts models
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.contrib.auth.forms import AdminPasswordChangeForm
from django.utils.html import format_html
from django.urls import path, reverse
from django.shortcuts import redirect, get_object_or_404, render
from django.contrib import messages
from django.http import HttpResponseRedirect
from .models import UserProfile, AuditLog


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    fk_name = 'user'
    can_delete = False
    verbose_name_plural = 'Profile'
    readonly_fields = ['id', 'created_at', 'updated_at']

    fieldsets = (
        ('Role & Department', {
            'fields': ('primary_role', 'department', 'job_title', 'employee_number')
        }),
        ('Contact Information', {
            'fields': ('phone_number', 'mobile_number', 'office_location')
        }),
        ('Organizational Structure', {
            'fields': ('unit_subdirectorate', 'line_manager')
        }),
        ('Permissions & Access', {
            'fields': ('can_view_all_kpas', 'can_approve_updates', 'can_generate_reports')
        }),
        ('User Preferences', {
            'fields': ('is_active_user', 'email_notifications', 'dashboard_preferences'),
            'classes': ('collapse',)
        }),
        ('Profile Picture', {
            'fields': ('profile_picture',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)
    list_display = ['username', 'email', 'first_name', 'last_name', 'get_role', 'get_staff_link', 'is_active', 'last_login', 'password_actions']
    list_filter = ['is_active', 'is_staff', 'is_superuser', 'profile__primary_role', 'profile__department', 'profile__is_active_user']
    search_fields = ['username', 'first_name', 'last_name', 'email', 'profile__employee_number']
    actions = ['reset_passwords', 'activate_users', 'deactivate_users']

    # Enhanced fieldsets for comprehensive user management
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email')}),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'first_name', 'last_name', 'email', 'password1', 'password2'),
        }),
    )

    def get_role(self, obj):
        if hasattr(obj, 'profile'):
            return obj.profile.get_primary_role_display()
        return 'No Profile'
    get_role.short_description = 'Role'

    def get_staff_link(self, obj):
        """Show link to staff member if linked"""
        if hasattr(obj, 'profile') and obj.profile.staff_member:
            staff = obj.profile.staff_member
            return format_html(
                '<a href="/admin/core/staff/{}/change/" title="View Staff Record">{}</a>',
                staff.id, staff.persal_number
            )
        return '—'
    get_staff_link.short_description = 'Staff Record'

    def password_actions(self, obj):
        """Quick password reset action"""
        if obj.pk:
            return format_html(
                '<a class="button" href="{}">Change Password</a>',
                reverse('admin:auth_user_password_change', args=[obj.pk])
            )
        return '—'
    password_actions.short_description = 'Password'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<int:user_id>/reset-password/', self.admin_site.admin_view(self.reset_password_view), name='auth_user_reset_password'),
        ]
        return custom_urls + urls

    def reset_password_view(self, request, user_id):
        """Custom password reset view for admins"""
        user = get_object_or_404(User, pk=user_id)

        if request.method == 'POST':
            form = AdminPasswordChangeForm(user, request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, f'Password for {user.username} has been changed successfully.')
                return HttpResponseRedirect(reverse('admin:auth_user_changelist'))
        else:
            form = AdminPasswordChangeForm(user)

        context = {
            'title': f'Change password: {user.username}',
            'form': form,
            'is_popup': False,
            'add': False,
            'change': True,
            'has_delete_permission': False,
            'has_file_field': False,
            'has_absolute_url': False,
            'opts': User._meta,
            'original': user,
            'save_as': False,
            'show_save': True,
        }
        return admin.site.admin_view(lambda r: render(r, 'admin/auth/user/change_password.html', context))(request)

    # Bulk actions
    def reset_passwords(self, request, queryset):
        """Bulk password reset action"""
        import secrets
        import string

        count = 0
        temp_passwords = []

        for user in queryset:
            # Generate a temporary password
            temp_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))
            user.set_password(temp_password)
            user.save()
            count += 1

            # Store for display
            temp_passwords.append(f'{user.username}: {temp_password}')

        # Display all temporary passwords
        password_list = '<br>'.join(temp_passwords)
        messages.success(request, format_html(
            f'Reset passwords for {count} users:<br><strong>{password_list}</strong><br>'
            f'<small>Please save these passwords and share them securely with the users.</small>'
        ))
    reset_passwords.short_description = 'Reset selected users\' passwords (generates temp passwords)'

    def activate_users(self, request, queryset):
        """Bulk activate users"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} user(s) activated.')
    activate_users.short_description = 'Activate selected users'

    def deactivate_users(self, request, queryset):
        """Bulk deactivate users"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} user(s) deactivated.')
    deactivate_users.short_description = 'Deactivate selected users'


# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'primary_role', 'department', 'job_title',
        'is_active_user', 'can_approve_updates', 'get_staff_link', 'user_actions'
    ]
    list_filter = [
        'primary_role', 'department', 'is_active_user',
        'can_approve_updates', 'can_view_all_kpas'
    ]
    search_fields = [
        'user__username', 'user__first_name', 'user__last_name',
        'employee_number', 'job_title', 'department'
    ]
    readonly_fields = ['id', 'created_at', 'updated_at', 'created_by', 'updated_by']
    list_editable = ['is_active_user', 'can_approve_updates']
    actions = ['activate_profiles', 'deactivate_profiles', 'grant_approval_rights', 'revoke_approval_rights']

    fieldsets = (
        ('User Information', {
            'fields': ('user', 'employee_number', 'primary_role')
        }),
        ('Job Details', {
            'fields': ('job_title', 'department', 'unit_subdirectorate', 'office_location')
        }),
        ('Contact Information', {
            'fields': ('phone_number', 'mobile_number')
        }),
        ('Profile Picture', {
            'fields': ('profile_picture',)
        }),
        ('Hierarchy', {
            'fields': ('line_manager',)
        }),
        ('Permissions', {
            'fields': ('can_view_all_kpas', 'can_approve_updates', 'can_generate_reports')
        }),
        ('Preferences', {
            'fields': ('is_active_user', 'email_notifications', 'dashboard_preferences')
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        }),
    )

    def get_staff_link(self, obj):
        """Show link to staff member if linked"""
        if obj.staff_member:
            return format_html(
                '<a href="/admin/core/staff/{}/change/" title="View Staff Record">{}</a>',
                obj.staff_member.id, obj.staff_member.persal_number
            )
        return '—'
    get_staff_link.short_description = 'Staff Record'

    def user_actions(self, obj):
        """Quick user management actions"""
        if obj.user:
            return format_html(
                '<a class="button" href="{}">Edit User</a> '
                '<a class="button" href="{}">Change Password</a>',
                reverse('admin:auth_user_change', args=[obj.user.pk]),
                reverse('admin:auth_user_password_change', args=[obj.user.pk])
            )
        return '—'
    user_actions.short_description = 'User Actions'

    # Bulk actions
    def activate_profiles(self, request, queryset):
        """Bulk activate user profiles"""
        updated = queryset.update(is_active_user=True)
        self.message_user(request, f'{updated} profile(s) activated.')
    activate_profiles.short_description = 'Activate selected profiles'

    def deactivate_profiles(self, request, queryset):
        """Bulk deactivate user profiles"""
        updated = queryset.update(is_active_user=False)
        self.message_user(request, f'{updated} profile(s) deactivated.')
    deactivate_profiles.short_description = 'Deactivate selected profiles'

    def grant_approval_rights(self, request, queryset):
        """Grant approval rights to selected profiles"""
        updated = queryset.update(can_approve_updates=True)
        self.message_user(request, f'Granted approval rights to {updated} profile(s).')
    grant_approval_rights.short_description = 'Grant approval rights'

    def revoke_approval_rights(self, request, queryset):
        """Revoke approval rights from selected profiles"""
        updated = queryset.update(can_approve_updates=False)
        self.message_user(request, f'Revoked approval rights from {updated} profile(s).')
    revoke_approval_rights.short_description = 'Revoke approval rights'

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = [
        'timestamp', 'user_email', 'action', 'model_name',
        'object_repr', 'user_ip_address'
    ]
    list_filter = [
        'action', 'model_name', 'timestamp', 'user'
    ]
    search_fields = [
        'user_email', 'object_repr', 'model_name', 'user_ip_address'
    ]
    readonly_fields = [
        'id', 'user', 'user_email', 'user_ip_address', 'action',
        'model_name', 'object_id', 'object_repr', 'changes',
        'additional_data', 'timestamp', 'session_key'
    ]

    fieldsets = (
        ('Action Details', {
            'fields': ('timestamp', 'action', 'user', 'user_email', 'user_ip_address')
        }),
        ('Object Information', {
            'fields': ('model_name', 'object_id', 'object_repr')
        }),
        ('Changes', {
            'fields': ('changes', 'additional_data')
        }),
        ('Session', {
            'fields': ('session_key',)
        }),
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
