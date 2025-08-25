"""
Notification views for user interface
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods, require_POST
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from django.urls import reverse

from .models import Notification, NotificationRecipient, NotificationChannel
from .services import NotificationService
from accounts.models import UserProfile


@login_required
def notification_inbox(request):
    """
    User's notification inbox
    """
    # Get filter parameters
    filter_type = request.GET.get('filter', 'all')  # all, unread, acknowledged
    search_query = request.GET.get('search', '')

    # Base queryset
    notifications = NotificationRecipient.objects.filter(
        recipient=request.user,
        notification__is_active=True,
        is_archived=False
    ).select_related('notification', 'notification__sender')

    # Apply filters
    if filter_type == 'unread':
        notifications = notifications.filter(is_read=False)
    elif filter_type == 'acknowledged':
        notifications = notifications.filter(is_acknowledged=True)

    # Search functionality
    if search_query:
        notifications = notifications.filter(
            Q(notification__title__icontains=search_query) |
            Q(notification__message__icontains=search_query) |
            Q(notification__sender__first_name__icontains=search_query) |
            Q(notification__sender__last_name__icontains=search_query)
        )

    # Exclude expired notifications
    notifications = notifications.filter(
        Q(notification__expires_at__isnull=True) |
        Q(notification__expires_at__gt=timezone.now())
    )

    # Pagination
    paginator = Paginator(notifications.order_by('-notification__sent_at'), 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Get counts for filter badges
    total_count = NotificationRecipient.objects.filter(
        recipient=request.user,
        notification__is_active=True,
        is_archived=False
    ).count()

    unread_count = NotificationService.get_unread_count(request.user)

    acknowledged_count = NotificationRecipient.objects.filter(
        recipient=request.user,
        is_acknowledged=True,
        notification__is_active=True,
        is_archived=False
    ).count()

    context = {
        'page_obj': page_obj,
        'filter_type': filter_type,
        'search_query': search_query,
        'total_count': total_count,
        'unread_count': unread_count,
        'acknowledged_count': acknowledged_count,
    }

    return render(request, 'notifications/inbox.html', context)


@login_required
def notification_detail(request, notification_id):
    """
    View a specific notification
    """
    notification_recipient = get_object_or_404(
        NotificationRecipient,
        notification_id=notification_id,
        recipient=request.user,
        notification__is_active=True
    )

    # Mark as read if not already read
    if not notification_recipient.is_read:
        notification_recipient.mark_as_read()

    context = {
        'notification_recipient': notification_recipient,
        'notification': notification_recipient.notification,
    }

    return render(request, 'notifications/detail.html', context)


@login_required
@require_POST
def mark_as_read(request, notification_id):
    """
    Mark a notification as read (AJAX)
    """
    try:
        notification_recipient = NotificationRecipient.objects.get(
            notification_id=notification_id,
            recipient=request.user
        )

        notification_recipient.mark_as_read()

        return JsonResponse({
            'success': True,
            'message': 'Notification marked as read'
        })

    except NotificationRecipient.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Notification not found'
        }, status=404)


@login_required
@require_POST
def acknowledge_notification(request, notification_id):
    """
    Acknowledge a notification
    """
    try:
        notification_recipient = NotificationRecipient.objects.get(
            notification_id=notification_id,
            recipient=request.user
        )

        response_message = request.POST.get('response_message', '')
        notification_recipient.mark_as_acknowledged(response_message)

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': 'Notification acknowledged'
            })
        else:
            messages.success(request, 'Notification acknowledged successfully.')
            return redirect('notification_detail', notification_id=notification_id)

    except NotificationRecipient.DoesNotExist:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': 'Notification not found'
            }, status=404)
        else:
            messages.error(request, 'Notification not found.')
            return redirect('notification_inbox')


@login_required
@require_POST
def archive_notification(request, notification_id):
    """
    Archive a notification
    """
    try:
        notification_recipient = NotificationRecipient.objects.get(
            notification_id=notification_id,
            recipient=request.user
        )

        notification_recipient.archive()

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': 'Notification archived'
            })
        else:
            messages.success(request, 'Notification archived successfully.')
            return redirect('notification_inbox')

    except NotificationRecipient.DoesNotExist:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': 'Notification not found'
            }, status=404)
        else:
            messages.error(request, 'Notification not found.')
            return redirect('notification_inbox')


@login_required
def compose_message(request):
    """
    Compose a new message to other users
    """
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        message = request.POST.get('message', '').strip()
        recipient_ids = request.POST.getlist('recipients')
        org_unit_ids = request.POST.getlist('org_units')
        priority = request.POST.get('priority', 'NORMAL')
        requires_acknowledgment = request.POST.get('requires_acknowledgment') == 'on'

        if not title or not message or (not recipient_ids and not org_unit_ids):
            messages.error(request, 'Please fill in all required fields and select at least one recipient or organizational unit.')
        else:
            try:
                # Get individual recipients
                recipients = set()
                if recipient_ids:
                    individual_recipients = User.objects.filter(id__in=recipient_ids, is_active=True)
                    recipients.update(individual_recipients)

                # Get organizational unit recipients
                if org_unit_ids:
                    from core.models import OrgUnit
                    org_units = OrgUnit.objects.filter(id__in=org_unit_ids, is_active=True)
                    for org_unit in org_units:
                        # Get all active users in this organizational unit
                        org_unit_users = User.objects.filter(
                            profile__staff_member__org_unit=org_unit,
                            is_active=True,
                            profile__is_active_user=True
                        )
                        recipients.update(org_unit_users)

                # Convert to list and exclude sender
                recipients = list(recipients)
                if request.user in recipients:
                    recipients.remove(request.user)

                if recipients:
                    NotificationService.send_notification(
                        title=title,
                        message=message,
                        recipients=recipients,
                        sender=request.user,
                        message_type='USER_MESSAGE',
                        priority=priority,
                        channel_name='GENERAL',
                        requires_acknowledgment=requires_acknowledgment
                    )

                    # Create summary message
                    org_unit_names = []
                    if org_unit_ids:
                        from core.models import OrgUnit
                        org_unit_names = list(OrgUnit.objects.filter(id__in=org_unit_ids).values_list('name', flat=True))

                    summary_parts = []
                    if len(recipients) > 0:
                        summary_parts.append(f'{len(recipients)} recipient(s)')
                    if org_unit_names:
                        summary_parts.append(f'organizational units: {", ".join(org_unit_names)}')

                    summary = ' including ' + ' and '.join(summary_parts) if summary_parts else f'{len(recipients)} recipient(s)'

                    messages.success(
                        request,
                        f'Message sent successfully to {summary}.'
                    )
                    return redirect('notification_inbox')
                else:
                    messages.error(request, 'No valid recipients found.')

            except Exception as e:
                messages.error(request, f'Error sending message: {str(e)}')

    # Get all available recipients (all active users except current user)
    available_users = User.objects.filter(
        is_active=True,
        profile__is_active_user=True
    ).exclude(id=request.user.id).select_related('profile', 'profile__staff_member', 'profile__staff_member__org_unit')

    # Get all organizational units for group messaging
    from core.models import OrgUnit
    org_units = OrgUnit.objects.filter(is_active=True).order_by('unit_type', 'name')

    context = {
        'available_users': available_users.order_by('first_name', 'last_name'),
        'org_units': org_units,
        'priority_choices': Notification.PRIORITY_CHOICES,
    }

    return render(request, 'notifications/compose.html', context)


@login_required
@require_http_methods(["GET"])
def get_unread_count(request):
    """
    Get unread notification count (AJAX)
    """
    count = NotificationService.get_unread_count(request.user)
    return JsonResponse({'unread_count': count})


@login_required
@require_http_methods(["GET"])
def get_recent_notifications(request):
    """
    Get recent notifications for dropdown/widget (AJAX)
    """
    notifications = NotificationService.get_user_notifications(
        request.user,
        unread_only=False,
        limit=10
    )

    notification_data = []
    for notif_recipient in notifications:
        notification = notif_recipient.notification
        notification_data.append({
            'id': notification.id,
            'title': notification.title,
            'message': notification.message[:100] + '...' if len(notification.message) > 100 else notification.message,
            'sender': notification.sender.get_full_name() if notification.sender else 'System',
            'sent_at': notification.sent_at.isoformat(),
            'is_read': notif_recipient.is_read,
            'priority': notification.priority,
            'message_type': notification.message_type,
            'url': reverse('notification_detail', args=[notification.id])
        })

    return JsonResponse({
        'notifications': notification_data,
        'unread_count': NotificationService.get_unread_count(request.user)
    })
