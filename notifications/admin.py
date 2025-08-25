"""
Admin interface for notification system
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import NotificationChannel, Notification, NotificationRecipient, NotificationTemplate


@admin.register(NotificationChannel)
class NotificationChannelAdmin(admin.ModelAdmin):
    list_display = ['name', 'channel_type', 'is_active', 'allow_user_messages', 'allow_system_messages', 'created_at']
    list_filter = ['channel_type', 'is_active', 'allow_user_messages', 'allow_system_messages']
    search_fields = ['name', 'description']
    readonly_fields = ['id', 'created_at', 'updated_at']

    fieldsets = (
        ('Channel Information', {
            'fields': ('name', 'channel_type', 'description', 'is_active')
        }),
        ('Channel Settings', {
            'fields': ('allow_user_messages', 'allow_system_messages', 'auto_delete_after_days')
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


class NotificationRecipientInline(admin.TabularInline):
    model = NotificationRecipient
    extra = 0
    readonly_fields = ['is_read', 'read_at', 'is_acknowledged', 'acknowledged_at']
    fields = ['recipient', 'is_read', 'read_at', 'is_acknowledged', 'acknowledged_at', 'is_archived']


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['title', 'sender', 'message_type', 'priority', 'channel', 'get_recipient_count', 'get_read_count', 'sent_at']
    list_filter = ['message_type', 'priority', 'channel', 'is_broadcast', 'requires_acknowledgment', 'sent_at']
    search_fields = ['title', 'message', 'sender__username', 'sender__first_name', 'sender__last_name']
    readonly_fields = ['id', 'sent_at', 'created_at', 'updated_at', 'get_recipient_count', 'get_read_count', 'get_acknowledged_count']
    inlines = [NotificationRecipientInline]
    date_hierarchy = 'sent_at'

    fieldsets = (
        ('Message Details', {
            'fields': ('title', 'message', 'message_type', 'priority')
        }),
        ('Sender and Channel', {
            'fields': ('sender', 'channel')
        }),
        ('Related Object', {
            'fields': ('related_object_type', 'related_object_id', 'related_url'),
            'classes': ('collapse',)
        }),
        ('Message Settings', {
            'fields': ('requires_acknowledgment', 'expires_at', 'is_broadcast')
        }),
        ('Status', {
            'fields': ('is_active', 'sent_at')
        }),
        ('Statistics', {
            'fields': ('get_recipient_count', 'get_read_count', 'get_acknowledged_count'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_recipient_count(self, obj):
        return obj.get_recipient_count()
    get_recipient_count.short_description = 'Recipients'

    def get_read_count(self, obj):
        count = obj.get_read_count()
        total = obj.get_recipient_count()
        if total > 0:
            percentage = (count / total) * 100
            return format_html(f'{count}/{total} ({percentage:.0f}%)')
        return '0/0'
    get_read_count.short_description = 'Read'

    def get_acknowledged_count(self, obj):
        if obj.requires_acknowledgment:
            count = obj.get_acknowledged_count()
            total = obj.get_recipient_count()
            if total > 0:
                percentage = (count / total) * 100
                return format_html(f'{count}/{total} ({percentage:.0f}%)')
            return '0/0'
        return 'N/A'
    get_acknowledged_count.short_description = 'Acknowledged'


@admin.register(NotificationRecipient)
class NotificationRecipientAdmin(admin.ModelAdmin):
    list_display = ['notification', 'recipient', 'is_read', 'read_at', 'is_acknowledged', 'acknowledged_at', 'is_archived']
    list_filter = ['is_read', 'is_acknowledged', 'is_archived', 'notification__message_type', 'notification__priority']
    search_fields = ['notification__title', 'recipient__username', 'recipient__first_name', 'recipient__last_name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    date_hierarchy = 'notification__sent_at'

    fieldsets = (
        ('Notification Details', {
            'fields': ('notification', 'recipient')
        }),
        ('Status', {
            'fields': ('is_read', 'read_at', 'is_acknowledged', 'acknowledged_at', 'is_archived', 'archived_at')
        }),
        ('Response', {
            'fields': ('response_message',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('notification', 'recipient')


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'message_type', 'priority', 'channel', 'requires_acknowledgment', 'usage_count', 'last_used']
    list_filter = ['message_type', 'priority', 'channel', 'requires_acknowledgment']
    search_fields = ['name', 'title_template', 'message_template']
    readonly_fields = ['id', 'usage_count', 'last_used', 'created_at', 'updated_at']

    fieldsets = (
        ('Template Information', {
            'fields': ('name', 'message_type', 'priority', 'channel')
        }),
        ('Template Content', {
            'fields': ('title_template', 'message_template'),
            'description': 'Use Django template syntax with context variables like {{ user.first_name }}, {{ target.name }}, etc.'
        }),
        ('Template Settings', {
            'fields': ('requires_acknowledgment', 'expires_after_hours')
        }),
        ('Usage Statistics', {
            'fields': ('usage_count', 'last_used'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def save_model(self, request, obj, form, change):
        if not change:  # New template
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)
