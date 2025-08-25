"""
Admin configuration for reports models
"""

from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import Attachment, ReportRequest


@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'file_type', 'original_filename', 'file_size_display',
        'access_level', 'uploaded_by', 'created_at'
    ]
    list_filter = [
        'file_type', 'access_level', 'is_public', 'is_active',
        'created_at', 'uploaded_by'
    ]
    search_fields = [
        'title', 'description', 'original_filename',
        'linked_plan_item__output', 'uploaded_by__username'
    ]
    readonly_fields = [
        'id', 'created_at', 'updated_at', 'created_by', 'updated_by',
        'original_filename', 'file_size', 'file_extension', 'file_size_mb'
    ]

    fieldsets = (
        ('File Information', {
            'fields': ('file', 'title', 'description', 'file_type')
        }),
        ('Linking', {
            'fields': ('linked_plan_item', 'linked_progress_update')
        }),
        ('Access Control', {
            'fields': ('access_level', 'is_public', 'is_active')
        }),
        ('File Details', {
            'fields': ('original_filename', 'file_size', 'file_extension', 'file_size_mb'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('id', 'uploaded_by', 'created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        }),
    )

    def file_size_display(self, obj):
        """Display file size in human readable format"""
        if obj.file_size:
            if obj.file_size < 1024:
                return f"{obj.file_size} B"
            elif obj.file_size < 1024 * 1024:
                return f"{obj.file_size / 1024:.1f} KB"
            else:
                return f"{obj.file_size / (1024 * 1024):.1f} MB"
        return "Unknown"
    file_size_display.short_description = "File Size"

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
            obj.uploaded_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(ReportRequest)
class ReportRequestAdmin(admin.ModelAdmin):
    list_display = [
        'template', 'requested_by', 'output_format', 'status_display',
        'created_at', 'processing_time_display', 'file_size_display'
    ]
    list_filter = [
        'template', 'output_format', 'status', 'is_scheduled',
        'created_at', 'requested_by'
    ]
    search_fields = [
        'requested_by__username', 'template', 'error_message'
    ]
    readonly_fields = [
        'id', 'created_at', 'updated_at', 'created_by', 'updated_by',
        'started_at', 'completed_at', 'processing_time', 'file_size',
        'file_size_mb', 'retry_count'
    ]

    fieldsets = (
        ('Request Details', {
            'fields': ('requested_by', 'template', 'output_format')
        }),
        ('Filters & Parameters', {
            'fields': ('filters', 'parameters')
        }),
        ('Status', {
            'fields': ('status', 'started_at', 'completed_at', 'processing_time')
        }),
        ('Results', {
            'fields': ('generated_file', 'file_size', 'file_size_mb')
        }),
        ('Error Handling', {
            'fields': ('error_message', 'retry_count')
        }),
        ('Scheduling', {
            'fields': ('is_scheduled', 'schedule_frequency', 'next_run_date')
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        }),
    )

    def status_display(self, obj):
        """Display status with color coding"""
        colors = {
            'PENDING': '#ffc107',
            'PROCESSING': '#17a2b8',
            'COMPLETED': '#28a745',
            'FAILED': '#dc3545',
            'CANCELLED': '#6c757d'
        }
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            colors.get(obj.status, '#000000'),
            obj.get_status_display()
        )
    status_display.short_description = "Status"

    def processing_time_display(self, obj):
        """Display processing time"""
        time = obj.processing_time
        if time:
            total_seconds = int(time.total_seconds())
            minutes = total_seconds // 60
            seconds = total_seconds % 60
            return f"{minutes}m {seconds}s"
        return "-"
    processing_time_display.short_description = "Processing Time"

    def file_size_display(self, obj):
        """Display file size"""
        if obj.file_size_mb:
            return f"{obj.file_size_mb} MB"
        return "-"
    file_size_display.short_description = "File Size"

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)

    actions = ['retry_failed_reports', 'cancel_pending_reports']

    def retry_failed_reports(self, request, queryset):
        """Retry failed report generation"""
        failed_reports = queryset.filter(status='FAILED')
        count = 0
        for report in failed_reports:
            report.status = 'PENDING'
            report.error_message = ''
            report.retry_count += 1
            report.save()
            count += 1

        self.message_user(request, f"Retrying {count} failed reports.")
    retry_failed_reports.short_description = "Retry failed reports"

    def cancel_pending_reports(self, request, queryset):
        """Cancel pending reports"""
        pending_reports = queryset.filter(status='PENDING')
        count = pending_reports.update(status='CANCELLED')
        self.message_user(request, f"Cancelled {count} pending reports.")
    cancel_pending_reports.short_description = "Cancel pending reports"
