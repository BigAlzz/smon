"""
Notification service utilities for sending and managing notifications
"""

from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Q
from typing import List, Optional, Dict, Any
from .models import Notification, NotificationChannel, NotificationRecipient, NotificationTemplate


class NotificationService:
    """
    Service class for managing notifications
    """
    
    @staticmethod
    def send_notification(
        title: str,
        message: str,
        recipients: List[User],
        sender: Optional[User] = None,
        message_type: str = 'USER_MESSAGE',
        priority: str = 'NORMAL',
        channel_name: str = 'GENERAL',
        requires_acknowledgment: bool = False,
        expires_after_hours: int = 0,
        related_object_type: str = '',
        related_object_id: str = '',
        related_url: str = ''
    ) -> Notification:
        """
        Send a notification to multiple recipients
        """
        # Get or create channel
        channel, _ = NotificationChannel.objects.get_or_create(
            name=channel_name,
            defaults={
                'channel_type': 'GENERAL',
                'description': f'Auto-created channel: {channel_name}'
            }
        )
        
        # Calculate expiration time
        expires_at = None
        if expires_after_hours > 0:
            expires_at = timezone.now() + timezone.timedelta(hours=expires_after_hours)
        
        # Create notification
        notification = Notification.objects.create(
            title=title,
            message=message,
            message_type=message_type,
            priority=priority,
            sender=sender,
            channel=channel,
            requires_acknowledgment=requires_acknowledgment,
            expires_at=expires_at,
            related_object_type=related_object_type,
            related_object_id=related_object_id,
            related_url=related_url
        )
        
        # Add recipients
        for recipient in recipients:
            NotificationRecipient.objects.create(
                notification=notification,
                recipient=recipient
            )
        
        return notification
    
    @staticmethod
    def send_system_notification(
        title: str,
        message: str,
        recipients: List[User],
        message_type: str = 'SYSTEM_ALERT',
        priority: str = 'NORMAL',
        **kwargs
    ) -> Notification:
        """
        Send a system-generated notification
        """
        return NotificationService.send_notification(
            title=title,
            message=message,
            recipients=recipients,
            sender=None,  # System message
            message_type=message_type,
            priority=priority,
            channel_name='SYSTEM',
            **kwargs
        )
    
    @staticmethod
    def send_approval_notification(
        title: str,
        message: str,
        approvers: List[User],
        sender: User,
        related_url: str = '',
        **kwargs
    ) -> Notification:
        """
        Send an approval request notification
        """
        return NotificationService.send_notification(
            title=title,
            message=message,
            recipients=approvers,
            sender=sender,
            message_type='APPROVAL_REQUEST',
            priority='HIGH',
            channel_name='APPROVAL',
            requires_acknowledgment=True,
            related_url=related_url,
            **kwargs
        )
    
    @staticmethod
    def send_from_template(
        template_name: str,
        recipients: List[User],
        context: Dict[str, Any],
        sender: Optional[User] = None,
        **kwargs
    ) -> Optional[Notification]:
        """
        Send notification using a template
        """
        try:
            template = NotificationTemplate.objects.get(name=template_name, is_active=True)
            
            # Render template
            title, message = template.render(context)
            
            # Calculate expiration
            expires_after_hours = template.expires_after_hours
            if 'expires_after_hours' in kwargs:
                expires_after_hours = kwargs.pop('expires_after_hours')
            
            # Send notification
            notification = NotificationService.send_notification(
                title=title,
                message=message,
                recipients=recipients,
                sender=sender,
                message_type=template.message_type,
                priority=template.priority,
                channel_name=template.channel.name,
                requires_acknowledgment=template.requires_acknowledgment,
                expires_after_hours=expires_after_hours,
                **kwargs
            )
            
            # Update template usage
            template.usage_count += 1
            template.last_used = timezone.now()
            template.save()
            
            return notification
            
        except NotificationTemplate.DoesNotExist:
            return None
    
    @staticmethod
    def broadcast_to_role(
        title: str,
        message: str,
        role: str,
        sender: Optional[User] = None,
        **kwargs
    ) -> Optional[Notification]:
        """
        Broadcast notification to all users with a specific role
        """
        from accounts.models import UserProfile
        
        # Get users with the specified role
        recipients = User.objects.filter(
            profile__primary_role=role,
            profile__is_active_user=True,
            is_active=True
        )
        
        if not recipients.exists():
            return None
        
        return NotificationService.send_notification(
            title=title,
            message=message,
            recipients=list(recipients),
            sender=sender,
            is_broadcast=True,
            **kwargs
        )
    
    @staticmethod
    def get_user_notifications(
        user: User,
        unread_only: bool = False,
        limit: int = 50
    ) -> List[NotificationRecipient]:
        """
        Get notifications for a specific user
        """
        queryset = NotificationRecipient.objects.filter(
            recipient=user,
            notification__is_active=True,
            is_archived=False
        ).select_related('notification', 'notification__sender')
        
        if unread_only:
            queryset = queryset.filter(is_read=False)
        
        # Exclude expired notifications
        queryset = queryset.filter(
            Q(notification__expires_at__isnull=True) |
            Q(notification__expires_at__gt=timezone.now())
        )
        
        return list(queryset.order_by('-notification__sent_at')[:limit])
    
    @staticmethod
    def mark_as_read(notification_recipient: NotificationRecipient):
        """
        Mark a notification as read
        """
        notification_recipient.mark_as_read()
    
    @staticmethod
    def mark_as_acknowledged(
        notification_recipient: NotificationRecipient,
        response_message: str = ""
    ):
        """
        Mark a notification as acknowledged
        """
        notification_recipient.mark_as_acknowledged(response_message)
    
    @staticmethod
    def get_unread_count(user: User) -> int:
        """
        Get count of unread notifications for a user
        """
        return NotificationRecipient.objects.filter(
            recipient=user,
            is_read=False,
            notification__is_active=True,
            is_archived=False
        ).filter(
            Q(notification__expires_at__isnull=True) |
            Q(notification__expires_at__gt=timezone.now())
        ).count()
    
    @staticmethod
    def cleanup_expired_notifications():
        """
        Clean up expired notifications
        """
        expired_notifications = Notification.objects.filter(
            expires_at__lt=timezone.now(),
            is_active=True
        )
        
        count = expired_notifications.count()
        expired_notifications.update(is_active=False)
        
        return count
    
    @staticmethod
    def auto_delete_old_notifications():
        """
        Auto-delete old notifications based on channel settings
        """
        from datetime import timedelta
        
        channels = NotificationChannel.objects.filter(
            auto_delete_after_days__gt=0,
            is_active=True
        )
        
        total_deleted = 0
        
        for channel in channels:
            cutoff_date = timezone.now() - timedelta(days=channel.auto_delete_after_days)
            
            old_notifications = Notification.objects.filter(
                channel=channel,
                sent_at__lt=cutoff_date
            )
            
            count = old_notifications.count()
            old_notifications.delete()
            total_deleted += count
        
        return total_deleted
