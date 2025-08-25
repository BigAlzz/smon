"""
Internal notification system for person-to-person and system-to-person communications
"""

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from core.models import BaseModel


class NotificationChannel(BaseModel):
    """
    Notification channels for different types of communications
    """
    CHANNEL_TYPES = [
        ('SYSTEM', 'System Notifications'),
        ('APPROVAL', 'Approval Workflow'),
        ('PROGRESS', 'Progress Updates'),
        ('GENERAL', 'General Communications'),
        ('URGENT', 'Urgent Messages'),
    ]

    name = models.CharField(max_length=100, unique=True)
    channel_type = models.CharField(max_length=20, choices=CHANNEL_TYPES, default='GENERAL')
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    # Channel settings
    allow_user_messages = models.BooleanField(default=True, help_text="Allow person-to-person messages")
    allow_system_messages = models.BooleanField(default=True, help_text="Allow system-generated messages")
    auto_delete_after_days = models.IntegerField(default=30, help_text="Auto-delete messages after X days (0 = never)")

    class Meta:
        ordering = ['channel_type', 'name']
        verbose_name = "Notification Channel"
        verbose_name_plural = "Notification Channels"

    def __str__(self):
        return f"{self.name} ({self.get_channel_type_display()})"


class Notification(BaseModel):
    """
    Internal notification/message system
    """
    PRIORITY_CHOICES = [
        ('LOW', 'Low Priority'),
        ('NORMAL', 'Normal Priority'),
        ('HIGH', 'High Priority'),
        ('URGENT', 'Urgent'),
    ]

    MESSAGE_TYPES = [
        ('USER_MESSAGE', 'User Message'),
        ('SYSTEM_ALERT', 'System Alert'),
        ('APPROVAL_REQUEST', 'Approval Request'),
        ('APPROVAL_RESPONSE', 'Approval Response'),
        ('PROGRESS_UPDATE', 'Progress Update'),
        ('DEADLINE_REMINDER', 'Deadline Reminder'),
        ('SYSTEM_MAINTENANCE', 'System Maintenance'),
    ]

    # Message details
    title = models.CharField(max_length=200)
    message = models.TextField()
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPES, default='USER_MESSAGE')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='NORMAL')

    # Sender and recipients
    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sent_notifications',
        null=True,
        blank=True,
        help_text="Null for system-generated messages"
    )
    recipients = models.ManyToManyField(
        User,
        through='NotificationRecipient',
        through_fields=('notification', 'recipient'),
        related_name='received_notifications'
    )

    # Channel and context
    channel = models.ForeignKey(
        NotificationChannel,
        on_delete=models.CASCADE,
        related_name='notifications'
    )

    # Related objects (for context)
    related_object_type = models.CharField(max_length=50, blank=True, help_text="Model name of related object")
    related_object_id = models.CharField(max_length=100, blank=True, help_text="ID of related object")
    related_url = models.URLField(blank=True, help_text="URL to related object/action")

    # Message settings
    requires_acknowledgment = models.BooleanField(default=False)
    expires_at = models.DateTimeField(null=True, blank=True, help_text="Message expiration time")
    is_broadcast = models.BooleanField(default=False, help_text="Broadcast to all users in role/department")

    # Status
    is_active = models.BooleanField(default=True)
    sent_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-sent_at', '-priority']
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"

    def __str__(self):
        sender_name = self.sender.get_full_name() if self.sender else "System"
        return f"{self.title} (from {sender_name})"

    @property
    def is_expired(self):
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False

    def get_recipient_count(self):
        return self.recipients.count()

    def get_read_count(self):
        return self.notificationrecipient_set.filter(is_read=True).count()

    def get_acknowledged_count(self):
        return self.notificationrecipient_set.filter(is_acknowledged=True).count()


class NotificationRecipient(BaseModel):
    """
    Through model for notification recipients with read/acknowledgment status
    """
    notification = models.ForeignKey(Notification, on_delete=models.CASCADE)
    recipient = models.ForeignKey(User, on_delete=models.CASCADE)

    # Status tracking
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    is_acknowledged = models.BooleanField(default=False)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    is_archived = models.BooleanField(default=False)
    archived_at = models.DateTimeField(null=True, blank=True)

    # Response (for acknowledgment messages)
    response_message = models.TextField(blank=True, help_text="Optional response from recipient")

    class Meta:
        unique_together = ['notification', 'recipient']
        ordering = ['-notification__sent_at']
        verbose_name = "Notification Recipient"
        verbose_name_plural = "Notification Recipients"

    def __str__(self):
        return f"{self.notification.title} → {self.recipient.get_full_name()}"

    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save()

    def mark_as_acknowledged(self, response_message=""):
        if not self.is_acknowledged:
            self.is_acknowledged = True
            self.acknowledged_at = timezone.now()
            if response_message:
                self.response_message = response_message
            self.save()

    def archive(self):
        if not self.is_archived:
            self.is_archived = True
            self.archived_at = timezone.now()
            self.save()


class NotificationTemplate(BaseModel):
    """
    Templates for system-generated notifications
    """
    name = models.CharField(max_length=100, unique=True)
    title_template = models.CharField(max_length=200, help_text="Title template with placeholders")
    message_template = models.TextField(help_text="Message template with placeholders")
    message_type = models.CharField(max_length=20, choices=Notification.MESSAGE_TYPES)
    priority = models.CharField(max_length=10, choices=Notification.PRIORITY_CHOICES, default='NORMAL')
    channel = models.ForeignKey(NotificationChannel, on_delete=models.CASCADE)

    # Template settings
    requires_acknowledgment = models.BooleanField(default=False)
    expires_after_hours = models.IntegerField(default=0, help_text="Auto-expire after X hours (0 = never)")

    # Usage tracking
    usage_count = models.IntegerField(default=0)
    last_used = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['name']
        verbose_name = "Notification Template"
        verbose_name_plural = "Notification Templates"

    def __str__(self):
        return f"{self.name} ({self.get_message_type_display()})"

    def render(self, context=None):
        """Render template with context variables"""
        if not context:
            context = {}

        try:
            from django.template import Template, Context
            title = Template(self.title_template).render(Context(context))
            message = Template(self.message_template).render(Context(context))
            return title, message
        except Exception as e:
            return self.title_template, self.message_template
