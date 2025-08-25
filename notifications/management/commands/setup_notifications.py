"""
Management command to set up initial notification channels and templates
"""

from django.core.management.base import BaseCommand
from notifications.models import NotificationChannel, NotificationTemplate


class Command(BaseCommand):
    help = 'Set up initial notification channels and templates'

    def handle(self, *args, **options):
        self.stdout.write('Setting up notification channels and templates...')
        
        # Create notification channels
        channels = [
            {
                'name': 'SYSTEM',
                'channel_type': 'SYSTEM',
                'description': 'System-generated notifications and alerts',
                'allow_user_messages': False,
                'allow_system_messages': True,
                'auto_delete_after_days': 30
            },
            {
                'name': 'APPROVAL',
                'channel_type': 'APPROVAL',
                'description': 'Approval workflow notifications',
                'allow_user_messages': False,
                'allow_system_messages': True,
                'auto_delete_after_days': 60
            },
            {
                'name': 'PROGRESS',
                'channel_type': 'PROGRESS',
                'description': 'Progress update notifications',
                'allow_user_messages': False,
                'allow_system_messages': True,
                'auto_delete_after_days': 45
            },
            {
                'name': 'GENERAL',
                'channel_type': 'GENERAL',
                'description': 'General communications between users',
                'allow_user_messages': True,
                'allow_system_messages': True,
                'auto_delete_after_days': 30
            },
            {
                'name': 'URGENT',
                'channel_type': 'URGENT',
                'description': 'Urgent messages and alerts',
                'allow_user_messages': True,
                'allow_system_messages': True,
                'auto_delete_after_days': 90
            }
        ]
        
        for channel_data in channels:
            channel, created = NotificationChannel.objects.get_or_create(
                name=channel_data['name'],
                defaults=channel_data
            )
            if created:
                self.stdout.write(f'Created channel: {channel.name}')
            else:
                self.stdout.write(f'Channel already exists: {channel.name}')
        
        # Create notification templates
        templates = [
            {
                'name': 'progress_approval_request',
                'title_template': 'Progress Update Approval Required: {{ target.name }}',
                'message_template': '''A progress update has been submitted for approval.

Target: {{ target.name }}
Submitted by: {{ submitter.get_full_name }}
Actual Value: {{ progress_update.actual_value }} {{ target.get_unit_display }}
RAG Status: {{ progress_update.rag_status }}
Completion: {{ progress_update.percentage_complete }}%

Please review and approve this progress update.''',
                'message_type': 'APPROVAL_REQUEST',
                'priority': 'HIGH',
                'channel_name': 'APPROVAL',
                'requires_acknowledgment': True,
                'expires_after_hours': 72
            },
            {
                'name': 'progress_approved',
                'title_template': 'Progress Update Approved: {{ target.name }}',
                'message_template': '''Your progress update has been approved.

Target: {{ target.name }}
Approved by: {{ approver.get_full_name }}
Approval Date: {{ approval_date }}

{% if comments %}Comments: {{ comments }}{% endif %}

Thank you for your submission!''',
                'message_type': 'APPROVAL_RESPONSE',
                'priority': 'NORMAL',
                'channel_name': 'APPROVAL',
                'requires_acknowledgment': False,
                'expires_after_hours': 168
            },
            {
                'name': 'progress_rejected',
                'title_template': 'Progress Update Requires Revision: {{ target.name }}',
                'message_template': '''Your progress update has been returned for revision.

Target: {{ target.name }}
Reviewed by: {{ reviewer.get_full_name }}
Review Date: {{ review_date }}

Comments: {{ comments|default:"Please review and resubmit." }}

Please make the necessary changes and resubmit for approval.''',
                'message_type': 'APPROVAL_RESPONSE',
                'priority': 'HIGH',
                'channel_name': 'APPROVAL',
                'requires_acknowledgment': True,
                'expires_after_hours': 168
            },
            {
                'name': 'deadline_reminder',
                'title_template': 'Deadline Reminder: {{ target.name }}',
                'message_template': '''This is a reminder that a target deadline is approaching.

Target: {{ target.name }}
Due Date: {{ target.due_date }}
Days Remaining: {{ days_remaining }}

Please ensure your progress updates are current and submitted on time.''',
                'message_type': 'DEADLINE_REMINDER',
                'priority': 'NORMAL',
                'channel_name': 'SYSTEM',
                'requires_acknowledgment': False,
                'expires_after_hours': 24
            },
            {
                'name': 'system_maintenance',
                'title_template': 'System Maintenance: {{ maintenance_type }}',
                'message_template': '''System maintenance is scheduled.

Maintenance Type: {{ maintenance_type }}
Scheduled Date: {{ maintenance_date }}
Expected Duration: {{ duration }}

{% if impact %}Impact: {{ impact }}{% endif %}

Please plan accordingly and save your work before the maintenance window.''',
                'message_type': 'SYSTEM_MAINTENANCE',
                'priority': 'HIGH',
                'channel_name': 'SYSTEM',
                'requires_acknowledgment': True,
                'expires_after_hours': 48
            }
        ]
        
        for template_data in templates:
            channel_name = template_data.pop('channel_name')
            try:
                channel = NotificationChannel.objects.get(name=channel_name)
                template_data['channel'] = channel
                
                template, created = NotificationTemplate.objects.get_or_create(
                    name=template_data['name'],
                    defaults=template_data
                )
                if created:
                    self.stdout.write(f'Created template: {template.name}')
                else:
                    self.stdout.write(f'Template already exists: {template.name}')
            except NotificationChannel.DoesNotExist:
                self.stdout.write(f'Channel {channel_name} not found for template {template_data["name"]}')
        
        self.stdout.write(self.style.SUCCESS('Successfully set up notification system!'))
