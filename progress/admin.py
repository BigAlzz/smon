"""
Admin configuration for progress tracking models
"""

from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import Target, ProgressUpdate, CostLine, EvidenceFile


@admin.register(Target)
class TargetAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'plan_item', 'value', 'unit', 'due_date',
        'periodicity', 'rag_status_display', 'is_active'
    ]
    list_filter = [
        'unit', 'periodicity', 'is_active', 'plan_item__kpa',
        'plan_item__kpa__financial_year'
    ]
    search_fields = ['name', 'plan_item__output', 'plan_item__responsible_officer']
    readonly_fields = [
        'id', 'created_at', 'updated_at', 'created_by', 'updated_by',
        'ytd_target', 'rag_status_display'
    ]

    fieldsets = (
        ('Target Definition', {
            'fields': ('plan_item', 'name', 'value', 'unit', 'baseline')
        }),
        ('Timing', {
            'fields': ('due_date', 'periodicity', 'is_cumulative')
        }),
        ('RAG Thresholds', {
            'fields': ('green_threshold', 'amber_threshold', 'positive_tolerance', 'negative_tolerance')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Calculated Fields', {
            'fields': ('ytd_target', 'rag_status_display'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        }),
    )

    def rag_status_display(self, obj):
        """Display RAG status with color coding"""
        status = obj.calculate_rag_status()
        colors = {
            'GREEN': '#28a745',
            'AMBER': '#ffc107',
            'RED': '#dc3545',
            'GREY': '#6c757d'
        }
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            colors.get(status, '#000000'),
            status
        )
    rag_status_display.short_description = "RAG Status"

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(ProgressUpdate)
class ProgressUpdateAdmin(admin.ModelAdmin):
    list_display = [
        'target', 'period_name', 'actual_value', 'percentage_complete_display',
        'rag_status_display', 'risk_rating', 'is_submitted', 'is_approved'
    ]
    list_filter = [
        'period_type', 'risk_rating', 'is_submitted', 'is_approved',
        'target__plan_item__kpa', 'period_end'
    ]
    search_fields = [
        'target__name', 'period_name', 'narrative',
        'target__plan_item__output', 'target__plan_item__responsible_officer'
    ]
    readonly_fields = [
        'id', 'created_at', 'updated_at', 'created_by', 'updated_by',
        'variance_absolute', 'variance_percentage', 'percentage_complete',
        'rag_status', 'submitted_at', 'approved_at'
    ]

    fieldsets = (
        ('Period Information', {
            'fields': ('target', 'period_type', 'period_start', 'period_end', 'period_name')
        }),
        ('Progress Data', {
            'fields': ('actual_value', 'narrative', 'evidence_urls')
        }),
        ('Risk Assessment', {
            'fields': ('risk_rating', 'issues', 'corrective_actions')
        }),
        ('Forecasting', {
            'fields': ('forecast_value', 'forecast_confidence')
        }),
        ('Approval Workflow', {
            'fields': ('is_submitted', 'submitted_at', 'is_approved', 'approved_by', 'approved_at')
        }),
        ('Calculated Fields', {
            'fields': ('variance_absolute', 'variance_percentage', 'percentage_complete', 'rag_status'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('id', 'is_active', 'created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        }),
    )

    def percentage_complete_display(self, obj):
        """Display percentage complete with formatting"""
        return format_html(
            '<span style="font-weight: bold;">{:.1f}%</span>',
            obj.percentage_complete
        )
    percentage_complete_display.short_description = "% Complete"

    def rag_status_display(self, obj):
        """Display RAG status with color coding"""
        status = obj.rag_status
        colors = {
            'GREEN': '#28a745',
            'AMBER': '#ffc107',
            'RED': '#dc3545',
            'GREY': '#6c757d'
        }
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            colors.get(status, '#000000'),
            status
        )
    rag_status_display.short_description = "RAG Status"

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user

        # Handle approval workflow
        if obj.is_approved and not obj.approved_by:
            obj.approved_by = request.user
            obj.approved_at = timezone.now()

        super().save_model(request, obj, form, change)


@admin.register(CostLine)
class CostLineAdmin(admin.ModelAdmin):
    list_display = [
        'description', 'plan_item', 'cost_type', 'budgeted_amount_display',
        'actual_spend_display', 'spend_percentage_display', 'spend_status_display'
    ]
    list_filter = [
        'cost_type', 'funding_source', 'plan_item__kpa',
        'cost_period_start', 'is_active'
    ]
    search_fields = [
        'description', 'plan_item__output', 'supplier_vendor',
        'purchase_order_number'
    ]
    readonly_fields = [
        'id', 'created_at', 'updated_at', 'created_by', 'updated_by',
        'variance_amount', 'variance_percentage', 'commitment_percentage',
        'spend_percentage', 'remaining_budget'
    ]

    fieldsets = (
        ('Cost Information', {
            'fields': ('plan_item', 'cost_type', 'description')
        }),
        ('Financial Details', {
            'fields': ('budgeted_amount', 'committed_amount', 'actual_spend')
        }),
        ('Period & Source', {
            'fields': ('cost_period_start', 'cost_period_end', 'funding_source')
        }),
        ('Procurement Details', {
            'fields': ('purchase_order_number', 'supplier_vendor')
        }),
        ('Calculated Fields', {
            'fields': ('variance_amount', 'variance_percentage', 'commitment_percentage',
                      'spend_percentage', 'remaining_budget'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('id', 'is_active', 'created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        }),
    )

    def budgeted_amount_display(self, obj):
        return format_html('R {:,.2f}', obj.budgeted_amount)
    budgeted_amount_display.short_description = "Budget"

    def actual_spend_display(self, obj):
        color = '#dc3545' if obj.is_overspent() else '#000000'
        return format_html(
            '<span style="color: {};">R {:,.2f}</span>',
            color, obj.actual_spend
        )
    actual_spend_display.short_description = "Actual Spend"

    def spend_percentage_display(self, obj):
        percentage = obj.spend_percentage
        color = '#dc3545' if percentage > 100 else '#28a745' if percentage < 50 else '#ffc107'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{:.1f}%</span>',
            color, percentage
        )
    spend_percentage_display.short_description = "% Spent"

    def spend_status_display(self, obj):
        status = obj.get_spend_status()
        colors = {
            'OVERSPENT': '#dc3545',
            'FULLY_SPENT': '#28a745',
            'HIGH_SPEND': '#ffc107',
            'MODERATE_SPEND': '#17a2b8',
            'LOW_SPEND': '#6c757d'
        }
        return format_html(
            '<span style="color: {};">{}</span>',
            colors.get(status, '#000000'),
            status.replace('_', ' ').title()
        )
    spend_status_display.short_description = "Spend Status"

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(EvidenceFile)
class EvidenceFileAdmin(admin.ModelAdmin):
    list_display = [
        'original_filename', 'progress_update', 'file_type_display',
        'file_size_display', 'uploaded_by', 'uploaded_at', 'is_active'
    ]
    list_filter = [
        'file_type', 'is_active', 'uploaded_at',
        'progress_update__target__plan_item__kpa'
    ]
    search_fields = [
        'original_filename', 'description', 'uploaded_by__username',
        'progress_update__target__name'
    ]
    readonly_fields = [
        'id', 'original_filename', 'file_size', 'file_type', 'uploaded_at'
    ]

    fieldsets = (
        ('File Information', {
            'fields': ('progress_update', 'file', 'original_filename', 'description')
        }),
        ('File Details', {
            'fields': ('file_size', 'file_type'),
            'classes': ('collapse',)
        }),
        ('Upload Information', {
            'fields': ('uploaded_by', 'uploaded_at')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Metadata', {
            'fields': ('id',),
            'classes': ('collapse',)
        }),
    )

    def file_type_display(self, obj):
        """Display file type with icon"""
        icon = obj.file_icon.replace('bi-', '')
        return format_html(
            '<i class="bi bi-{}"></i> {}',
            icon, obj.file_type
        )
    file_type_display.short_description = "File Type"

    def file_size_display(self, obj):
        """Display file size in MB"""
        return format_html('{} MB', obj.file_size_mb)
    file_size_display.short_description = "Size"

    def save_model(self, request, obj, form, change):
        if not change:
            obj.uploaded_by = request.user
            if obj.file:
                obj.original_filename = obj.file.name
                obj.file_size = obj.file.size
                obj.file_type = getattr(obj.file, 'content_type', 'application/octet-stream')
        super().save_model(request, obj, form, change)
