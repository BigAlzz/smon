"""
Admin configuration for core models
"""

from django.contrib import admin
from django.utils.html import format_html
from .models import OrgUnit

from .models import FinancialYear, KPA, OperationalPlanItem, Staff


@admin.register(FinancialYear)
class FinancialYearAdmin(admin.ModelAdmin):
    list_display = ['year_code', 'start_date', 'end_date', 'is_active', 'created_at']
    list_filter = ['is_active', 'start_date']
    search_fields = ['year_code', 'description']
    readonly_fields = ['id', 'created_at', 'updated_at', 'created_by', 'updated_by']

    fieldsets = (
        (None, {
            'fields': ('year_code', 'start_date', 'end_date', 'is_active', 'description')
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        }),
    )

    def save_model(self, request, obj, form, change):
        if not change:  # Creating new object
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)

@admin.register(OrgUnit)
class OrgUnitAdmin(admin.ModelAdmin):
    list_display = ['name', 'unit_type', 'parent', 'is_active']
    list_filter = ['unit_type', 'is_active']
    search_fields = ['name']
    autocomplete_fields = ['parent']
    fields = ['name', 'unit_type', 'parent', 'is_active']

    def get_urls(self):
        urls = super().get_urls()
        from django.urls import path
        from core.views_orgchart import admin_org_chart_view
        custom_urls = [
            path('org-chart/', admin_org_chart_view, name='core_orgunit_orgchart'),
        ]
        return custom_urls + urls


@admin.register(KPA)
class KPAAdmin(admin.ModelAdmin):
    list_display = ['title', 'financial_year', 'owner', 'get_org_units', 'order', 'is_active']
    list_filter = ['financial_year', 'is_active', 'owner', 'org_units']
    search_fields = ['title', 'description', 'strategic_objective']
    readonly_fields = ['id', 'created_at', 'updated_at', 'created_by', 'updated_by']
    ordering = ['financial_year', 'order', 'title']
    filter_horizontal = ['org_units']
    list_editable = ['order', 'is_active']
    actions = ['make_active', 'make_inactive']

    fieldsets = (
        (None, {
            'fields': ('title', 'description', 'financial_year', 'owner', 'strategic_objective')
        }),
        ('Organizational Units', {
            'fields': ('org_units',)
        }),
        ('Display Settings', {
            'fields': ('order', 'is_active')
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        }),
    )

    def get_org_units(self, obj):
        """Display org units in list view"""
        units = obj.org_units.all()[:3]  # Show first 3
        if not units:
            return "—"
        result = ", ".join([unit.name for unit in units])
        if obj.org_units.count() > 3:
            result += f" (+{obj.org_units.count() - 3} more)"
        return result
    get_org_units.short_description = 'Organizational Units'

    def make_active(self, request, queryset):
        """Bulk action to activate KPAs"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} KPA(s) marked as active.')
    make_active.short_description = 'Mark selected KPAs as active'

    def make_inactive(self, request, queryset):
        """Bulk action to deactivate KPAs"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} KPA(s) marked as inactive.')
    make_inactive.short_description = 'Mark selected KPAs as inactive'

    def save_model(self, request, obj, form, change):
        if not change:  # Creating new object
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    list_display = ['persal_number', 'full_name', 'job_title', 'org_unit', 'cell_number', 'extension', 'employment_type', 'is_active', 'start_date']
    list_filter = ['org_unit', 'employment_type', 'salary_level', 'is_active', 'gender', 'highest_qualification', 'is_manager']
    search_fields = ['persal_number', 'first_name', 'last_name', 'email', 'job_title', 'cell_number', 'phone']
    readonly_fields = ['id', 'created_at', 'updated_at', 'created_by', 'updated_by', 'years_of_service', 'is_contract_ending_soon']
    list_editable = ['is_active']
    actions = ['make_active', 'make_inactive', 'mark_as_managers']

    fieldsets = (
        ('Personal Information', {
            'fields': ('persal_number', 'first_name', 'last_name', 'email', 'phone', 'cell_number', 'extension', 'id_number')
        }),
        ('Demographics', {
            'fields': ('date_of_birth', 'gender', 'nationality'),
            'classes': ('collapse',)
        }),
        ('Employment Details', {
            'fields': ('org_unit', 'job_title', 'employment_type', 'salary_level', 'start_date', 'end_date')
        }),
        ('Qualifications & Skills', {
            'fields': ('highest_qualification', 'qualification_details', 'skills'),
            'classes': ('collapse',)
        }),
        ('Contact Information', {
            'fields': ('physical_address', 'postal_address', 'emergency_contact_name', 'emergency_contact_phone'),
            'classes': ('collapse',)
        }),
        ('Performance & Development', {
            'fields': ('performance_rating', 'development_needs'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_active', 'is_manager')
        }),
        ('Metadata', {
            'fields': ('id', 'years_of_service', 'is_contract_ending_soon', 'created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        }),
    )

    def full_name(self, obj):
        return obj.full_name
    full_name.short_description = 'Full Name'

    def make_active(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} staff member(s) marked as active.')
    make_active.short_description = 'Mark selected staff as active'

    def make_inactive(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} staff member(s) marked as inactive.')
    make_inactive.short_description = 'Mark selected staff as inactive'

    def mark_as_managers(self, request, queryset):
        updated = queryset.update(is_manager=True)
        self.message_user(request, f'{updated} staff member(s) marked as managers.')
    mark_as_managers.short_description = 'Mark selected staff as managers'

    def save_model(self, request, obj, form, change):
        if not change:  # Creating new object
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(OperationalPlanItem)
class OperationalPlanItemAdmin(admin.ModelAdmin):
    list_display = [
        'output_summary', 'kpa', 'responsible_officer',
        'budget_programme', 'total_budget_display', 'priority', 'is_active'
    ]
    list_filter = [
        'kpa__financial_year', 'kpa', 'priority', 'is_active',
        'budget_programme', 'budget_objective'
    ]
    search_fields = [
        'output', 'indicator', 'responsible_officer',
        'budget_programme', 'budget_objective', 'unit_subdirectorate'
    ]
    readonly_fields = [
        'id', 'created_at', 'updated_at', 'created_by', 'updated_by', 'total_budget'
    ]

    fieldsets = (
        ('Output & Activities', {
            'fields': ('kpa', 'output', 'activities', 'target_description', 'indicator')
        }),
        ('Resources & Inputs', {
            'fields': ('inputs', 'input_cost', 'output_cost')
        }),
        ('Timeline', {
            'fields': ('timeframe', 'start_date', 'end_date')
        }),
        ('Budget Classification', {
            'fields': ('budget_programme', 'budget_objective', 'budget_responsibility')
        }),
        ('Responsibility', {
            'fields': ('responsible_officer', 'unit_subdirectorate', 'office')
        }),
        ('Status & Priority', {
            'fields': ('priority', 'is_active', 'notes')
        }),
        ('Metadata', {
            'fields': ('id', 'total_budget', 'created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        }),
    )

    def output_summary(self, obj):
        """Display truncated output for list view"""
        return obj.output[:80] + "..." if len(obj.output) > 80 else obj.output
    output_summary.short_description = "Output"

    def total_budget_display(self, obj):
        """Display formatted total budget"""
        return format_html(
            '<span style="font-weight: bold;">R {:,.2f}</span>',
            obj.total_budget
        )
    total_budget_display.short_description = "Total Budget"

    def save_model(self, request, obj, form, change):
        if not change:  # Creating new object
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)
