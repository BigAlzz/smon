"""
Report generation and file attachment models

This module contains models for managing report requests, file attachments,
and document management within the KPA monitoring system.
"""

from django.db import models
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator
from django.utils import timezone
from core.models import BaseModel, OperationalPlanItem, KPA
from progress.models import ProgressUpdate
import os


def attachment_upload_path(instance, filename):
    """Generate upload path for attachments"""
    # Organize by year/month/model_type
    now = timezone.now()
    model_name = instance.content_object._meta.model_name if instance.content_object else 'general'
    return f'attachments/{now.year}/{now.month:02d}/{model_name}/{filename}'


class Attachment(BaseModel):
    """
    File attachments that can be linked to various models
    """
    FILE_TYPE_CHOICES = [
        ('EVIDENCE', 'Evidence Document'),
        ('TOR', 'Terms of Reference'),
        ('SCM', 'SCM Document'),
        ('REPORT', 'Report'),
        ('PHOTO', 'Photograph'),
        ('SPREADSHEET', 'Spreadsheet'),
        ('PRESENTATION', 'Presentation'),
        ('OTHER', 'Other Document'),
    ]

    # File information
    file = models.FileField(
        upload_to=attachment_upload_path,
        validators=[
            FileExtensionValidator(
                allowed_extensions=['pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx',
                                  'jpg', 'jpeg', 'png', 'gif', 'txt', 'csv']
            )
        ]
    )
    original_filename = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField(help_text="File size in bytes")
    file_type = models.CharField(
        max_length=20,
        choices=FILE_TYPE_CHOICES,
        default='OTHER'
    )

    # Metadata
    title = models.CharField(
        max_length=200,
        help_text="Descriptive title for the attachment"
    )
    description = models.TextField(
        blank=True,
        help_text="Additional description or notes"
    )

    # Linking to other models (generic approach)
    # Can be linked to OperationalPlanItem, ProgressUpdate, etc.
    linked_plan_item = models.ForeignKey(
        OperationalPlanItem,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='attachments'
    )
    linked_progress_update = models.ForeignKey(
        ProgressUpdate,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='attachments'
    )

    # Access control
    is_public = models.BooleanField(
        default=False,
        help_text="Whether this attachment can be viewed by all users"
    )
    access_level = models.CharField(
        max_length=20,
        choices=[
            ('PUBLIC', 'Public'),
            ('INTERNAL', 'Internal Only'),
            ('RESTRICTED', 'Restricted Access'),
            ('CONFIDENTIAL', 'Confidential'),
        ],
        default='INTERNAL'
    )

    # Status
    is_active = models.BooleanField(default=True)
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploaded_attachments'
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Attachment"
        verbose_name_plural = "Attachments"

    def __str__(self):
        return f"{self.title} ({self.get_file_type_display()})"

    def save(self, *args, **kwargs):
        if self.file:
            self.original_filename = self.file.name
            self.file_size = self.file.size
        super().save(*args, **kwargs)

    @property
    def file_extension(self):
        """Get file extension"""
        return os.path.splitext(self.original_filename)[1].lower()

    @property
    def file_size_mb(self):
        """Get file size in MB"""
        return round(self.file_size / (1024 * 1024), 2)

    def can_user_access(self, user):
        """Check if user can access this attachment"""
        if not user.is_authenticated:
            return False

        if self.access_level == 'PUBLIC':
            return True

        # Check if user has appropriate role
        user_profile = getattr(user, 'profile', None)
        if not user_profile:
            return False

        if user_profile.primary_role in ['SYSTEM_ADMIN', 'SENIOR_MANAGER']:
            return True

        # Check if user is linked to the related objects
        if self.linked_plan_item:
            return user_profile.can_edit_plan_item(self.linked_plan_item)

        if self.linked_progress_update:
            return user_profile.can_edit_plan_item(self.linked_progress_update.target.plan_item)

        return self.uploaded_by == user


class ReportRequest(BaseModel):
    """
    Represents a request to generate a report
    """
    TEMPLATE_CHOICES = [
        ('EXCO_ONEPAGER', 'EXCO One-Pager'),
        ('KPA_DRILLDOWN', 'KPA Drill-down'),
        ('PROGRAMME_PACK', 'Programme Pack'),
        ('FINANCE_VIEW', 'Finance View'),
        ('SCM_TRACKER', 'SCM & Deliverables Tracker'),
        ('CUSTOM', 'Custom Report'),
    ]

    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('CANCELLED', 'Cancelled'),
    ]

    FORMAT_CHOICES = [
        ('PDF', 'PDF'),
        ('XLSX', 'Excel'),
        ('PPTX', 'PowerPoint'),
        ('JSON', 'JSON Data'),
    ]

    # Request details
    requested_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='report_requests'
    )
    template = models.CharField(
        max_length=20,
        choices=TEMPLATE_CHOICES
    )
    output_format = models.CharField(
        max_length=10,
        choices=FORMAT_CHOICES,
        default='PDF'
    )

    # Filters and parameters
    filters = models.JSONField(
        default=dict,
        help_text="Report filters (KPAs, date ranges, units, etc.)"
    )
    parameters = models.JSONField(
        default=dict,
        help_text="Additional report parameters and settings"
    )

    # Status tracking
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING'
    )
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Results
    generated_file = models.FileField(
        upload_to='reports/generated/',
        null=True,
        blank=True
    )
    file_size = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Generated file size in bytes"
    )

    # Error handling
    error_message = models.TextField(
        blank=True,
        help_text="Error message if generation failed"
    )
    retry_count = models.PositiveIntegerField(default=0)

    # Scheduling
    is_scheduled = models.BooleanField(
        default=False,
        help_text="Whether this is a scheduled recurring report"
    )
    schedule_frequency = models.CharField(
        max_length=20,
        choices=[
            ('DAILY', 'Daily'),
            ('WEEKLY', 'Weekly'),
            ('MONTHLY', 'Monthly'),
            ('QUARTERLY', 'Quarterly'),
        ],
        blank=True
    )
    next_run_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Report Request"
        verbose_name_plural = "Report Requests"

    def __str__(self):
        return f"{self.get_template_display()} - {self.requested_by.username} ({self.status})"

    def save(self, *args, **kwargs):
        if self.status == 'PROCESSING' and not self.started_at:
            self.started_at = timezone.now()
        elif self.status == 'COMPLETED' and not self.completed_at:
            self.completed_at = timezone.now()

        if self.generated_file:
            self.file_size = self.generated_file.size

        super().save(*args, **kwargs)

    @property
    def processing_time(self):
        """Calculate processing time if completed"""
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        return None

    @property
    def file_size_mb(self):
        """Get file size in MB"""
        if self.file_size:
            return round(self.file_size / (1024 * 1024), 2)
        return 0

    def can_user_download(self, user):
        """Check if user can download this report"""
        if user == self.requested_by:
            return True

        user_profile = getattr(user, 'profile', None)
        if user_profile and user_profile.primary_role in ['SYSTEM_ADMIN', 'SENIOR_MANAGER']:
            return True

        return False

    def mark_as_failed(self, error_message):
        """Mark report as failed with error message"""
        self.status = 'FAILED'
        self.error_message = error_message
        self.completed_at = timezone.now()
        self.save()

    def mark_as_completed(self, file_path):
        """Mark report as completed with generated file"""
        self.status = 'COMPLETED'
        self.generated_file = file_path
        self.completed_at = timezone.now()
        self.save()
