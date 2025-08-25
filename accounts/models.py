"""
User account extensions and role management models

This module extends Django's User model with additional fields for
organizational hierarchy and role-based permissions.
"""

from django.db import models
from django.contrib.auth.models import User, Group
from django.core.validators import RegexValidator
from core.models import BaseModel


class UserProfile(BaseModel):
    """
    Extended user profile with organizational information
    """
    ROLE_CHOICES = [
        ('SENIOR_MANAGER', 'Senior Manager / EXCO'),
        ('PROGRAMME_MANAGER', 'Programme Manager'),
        ('ME_STRATEGY', 'M&E / Strategy'),
        ('FINANCE', 'Finance'),
        ('SYSTEM_ADMIN', 'System Admin'),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile'
    )

    # Link to staff member record
    staff_member = models.OneToOneField(
        'core.Staff',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='user_profile',
        help_text="Link to staff member record in organizational structure"
    )

    # Organizational information
    employee_number = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        validators=[RegexValidator(r'^[A-Z0-9]+$', 'Employee number must be alphanumeric')]
    )
    job_title = models.CharField(max_length=200)
    department = models.CharField(max_length=200)
    unit_subdirectorate = models.CharField(
        max_length=200,
        blank=True,
        help_text="Unit or Sub-Directorate"
    )
    office_location = models.CharField(max_length=200, blank=True)

    # Contact information
    phone_number = models.CharField(
        max_length=20,
        blank=True,
        validators=[RegexValidator(r'^\+?1?\d{9,15}$', 'Enter a valid phone number')]
    )
    mobile_number = models.CharField(
        max_length=20,
        blank=True,
        validators=[RegexValidator(r'^\+?1?\d{9,15}$', 'Enter a valid mobile number')]
    )

    # Profile picture
    profile_picture = models.ImageField(
        upload_to='profile_pictures/',
        blank=True,
        null=True,
        help_text="Upload a profile picture (JPG, PNG, max 2MB)"
    )

    # Role and permissions
    primary_role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='PROGRAMME_MANAGER'
    )

    # Manager hierarchy
    line_manager = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='direct_reports',
        help_text="Direct line manager"
    )

    # Status and preferences
    is_active_user = models.BooleanField(
        default=True,
        help_text="Whether user can access the system"
    )
    email_notifications = models.BooleanField(
        default=True,
        help_text="Receive email notifications"
    )
    dashboard_preferences = models.JSONField(
        default=dict,
        blank=True,
        help_text="User dashboard preferences and settings"
    )

    # Data access permissions
    can_view_all_kpas = models.BooleanField(
        default=False,
        help_text="Can view all KPAs regardless of assignment"
    )
    can_approve_updates = models.BooleanField(
        default=False,
        help_text="Can approve progress updates"
    )
    can_generate_reports = models.BooleanField(
        default=True,
        help_text="Can generate and download reports"
    )

    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.get_primary_role_display()})"

    @property
    def full_name(self):
        return self.user.get_full_name() or self.user.username

    def get_accessible_kpas(self):
        """Get KPAs this user can access based on role and assignments"""
        from core.models import KPA

        if self.can_view_all_kpas or self.primary_role in ['SENIOR_MANAGER', 'ME_STRATEGY', 'SYSTEM_ADMIN']:
            return KPA.objects.filter(is_active=True)

        # Programme managers can see KPAs they own or are assigned to
        return KPA.objects.filter(
            models.Q(owner=self.user) |
            models.Q(plan_items__responsible_officer__icontains=self.user.get_full_name()),
            is_active=True
        ).distinct()

    def can_edit_plan_item(self, plan_item):
        """Check if user can edit a specific operational plan item"""
        if self.primary_role == 'SYSTEM_ADMIN':
            return True

        if self.primary_role == 'SENIOR_MANAGER' and plan_item.kpa.owner == self.user:
            return True

        if self.primary_role == 'PROGRAMME_MANAGER':
            # Check if user is the responsible officer
            return self.user.get_full_name().lower() in plan_item.responsible_officer.lower()

        return False


class AuditLog(BaseModel):
    """
    Comprehensive audit trail for all system changes
    """
    ACTION_CHOICES = [
        ('CREATE', 'Create'),
        ('UPDATE', 'Update'),
        ('DELETE', 'Delete'),
        ('LOGIN', 'Login'),
        ('LOGOUT', 'Logout'),
        ('APPROVE', 'Approve'),
        ('REJECT', 'Reject'),
        ('SUBMIT', 'Submit'),
        ('EXPORT', 'Export'),
        ('IMPORT', 'Import'),
    ]

    # Who performed the action
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="User who performed the action"
    )
    user_email = models.EmailField(
        help_text="Email of user (preserved even if user is deleted)"
    )
    user_ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="IP address of the user"
    )

    # What was done
    action = models.CharField(
        max_length=20,
        choices=ACTION_CHOICES
    )
    model_name = models.CharField(
        max_length=100,
        help_text="Name of the model that was changed"
    )
    object_id = models.CharField(
        max_length=100,
        help_text="ID of the object that was changed"
    )
    object_repr = models.CharField(
        max_length=200,
        help_text="String representation of the object"
    )

    # Change details
    changes = models.JSONField(
        default=dict,
        help_text="Before and after values for changed fields"
    )
    additional_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional context or metadata"
    )

    # When and where
    timestamp = models.DateTimeField(auto_now_add=True)
    session_key = models.CharField(
        max_length=40,
        blank=True,
        null=True,
        help_text="Session key for tracking user sessions"
    )

    class Meta:
        ordering = ['-timestamp']
        verbose_name = "Audit Log"
        verbose_name_plural = "Audit Logs"
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['model_name', 'object_id']),
            models.Index(fields=['action', 'timestamp']),
        ]

    def __str__(self):
        return f"{self.user_email} {self.action} {self.model_name} at {self.timestamp}"
