"""
Manager-specific views for KPA progress tracking and management
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q, Count, Sum, Avg, Max
from django.utils import timezone
from django.core.paginator import Paginator
from django.views.decorators.http import require_http_methods
from datetime import datetime, timedelta, date
from decimal import Decimal

from .models import KPA, OperationalPlanItem, Staff
from progress.models import Target, ProgressUpdate
from progress.forms import ProgressUpdateForm
from .permissions import require_manager_role, filter_kpas_for_user


@login_required
def manager_dashboard_view(request):
    """Dashboard for all staff members to track KPA progress and manage their responsibilities"""

    # Get user's accessible KPAs
    user_profile = getattr(request.user, 'profile', None)
    if not user_profile:
        messages.error(request, "User profile not found. Please contact system administrator.")
        return redirect('dashboard')

    # Get staff member record if available
    staff_member = getattr(user_profile, 'staff_member', None)

    # Determine user's management level and accessible KPAs
    if user_profile.primary_role == 'SENIOR_MANAGER':
        # Senior managers see KPAs they own
        kpas = KPA.objects.filter(owner=request.user, is_active=True)
        dashboard_title = "Senior Manager Dashboard"
        user_level = "senior_manager"
    elif user_profile.primary_role == 'PROGRAMME_MANAGER':
        # Programme managers see KPAs they're assigned to or own
        kpas = KPA.objects.filter(
            Q(plan_items__responsible_officer__icontains=request.user.get_full_name()) |
            Q(owner=request.user)
        ).filter(is_active=True).distinct()
        dashboard_title = "Programme Manager Dashboard"
        user_level = "programme_manager"
    elif staff_member and staff_member.is_manager:
        # Staff marked as managers see KPAs in their organizational unit
        kpas = KPA.objects.filter(
            Q(org_units=staff_member.org_unit) |
            Q(owner=request.user)
        ).filter(is_active=True).distinct()
        dashboard_title = f"{staff_member.job_title} Dashboard"
        user_level = "unit_manager"
    else:
        # Regular staff see KPAs they can contribute to
        kpas = user_profile.get_accessible_kpas()
        dashboard_title = "Staff Member Dashboard"
        user_level = "staff_member"
    
    # Get current financial year
    current_fy = None
    try:
        from core.models import FinancialYear
        current_fy = FinancialYear.objects.filter(is_active=True).first()
        if current_fy:
            kpas = kpas.filter(financial_year=current_fy)
    except:
        pass
    
    # Get statistics for each KPA
    kpa_stats = []
    for kpa in kpas.order_by('order', 'title'):
        plan_items = kpa.plan_items.filter(is_active=True)
        targets = Target.objects.filter(plan_item__in=plan_items, is_active=True)
        
        # Get recent progress updates
        recent_updates = ProgressUpdate.objects.filter(
            target__in=targets,
            is_active=True
        ).order_by('-period_end')[:5]
        
        # Calculate progress statistics
        total_targets = targets.count()
        targets_with_updates = targets.filter(progress_updates__isnull=False).distinct().count()
        
        # Get overdue targets (targets that should have updates but don't)
        overdue_targets = []
        for target in targets:
            if target.is_overdue_for_update():
                overdue_targets.append(target)
        
        kpa_stats.append({
            'kpa': kpa,
            'plan_items_count': plan_items.count(),
            'total_targets': total_targets,
            'targets_with_updates': targets_with_updates,
            'overdue_count': len(overdue_targets),
            'recent_updates': recent_updates,
            'completion_rate': (targets_with_updates / total_targets * 100) if total_targets > 0 else 0,
        })
    
    # Get overall statistics
    total_kpas = len(kpa_stats)
    total_plan_items = sum(stat['plan_items_count'] for stat in kpa_stats)
    total_targets = sum(stat['total_targets'] for stat in kpa_stats)
    total_overdue = sum(stat['overdue_count'] for stat in kpa_stats)
    
    # Get recent activity across all KPAs
    all_targets = Target.objects.filter(
        plan_item__kpa__in=kpas,
        is_active=True
    )
    recent_activity = ProgressUpdate.objects.filter(
        target__in=all_targets,
        is_active=True
    ).order_by('-updated_at')[:10]
    
    context = {
        'kpa_stats': kpa_stats,
        'total_kpas': total_kpas,
        'total_plan_items': total_plan_items,
        'total_targets': total_targets,
        'total_overdue': total_overdue,
        'recent_activity': recent_activity,
        'current_fy': current_fy,
        'user_role': user_profile.get_primary_role_display(),
        'dashboard_title': dashboard_title,
        'user_level': user_level,
        'staff_member': staff_member,
    }
    
    return render(request, 'manager/dashboard.html', context)


@login_required
def manager_kpa_detail_view(request, kpa_id):
    """Detailed view of a specific KPA for managers"""
    
    # Get the KPA and verify access
    kpa = get_object_or_404(KPA, id=kpa_id, is_active=True)
    user_profile = getattr(request.user, 'profile', None)
    
    # Check if user can access this KPA
    accessible_kpas = user_profile.get_accessible_kpas() if user_profile else KPA.objects.none()
    if not accessible_kpas.filter(id=kpa.id).exists():
        messages.error(request, "You don't have access to this KPA.")
        return redirect('manager_dashboard')
    
    # Get operational plan items
    plan_items = kpa.plan_items.filter(is_active=True).order_by('id')
    
    # Get targets and progress for each plan item
    plan_item_data = []
    for item in plan_items:
        targets = item.targets.filter(is_active=True).order_by('due_date')
        
        target_data = []
        for target in targets:
            latest_update = target.progress_updates.filter(is_active=True).order_by('-period_end').first()
            
            target_data.append({
                'target': target,
                'latest_update': latest_update,
                'is_overdue': target.is_overdue_for_update(),
                'rag_status': target.get_rag_status() if latest_update else 'GREY',
                'progress_percentage': target.get_progress_percentage() if latest_update else 0,
            })
        
        plan_item_data.append({
            'item': item,
            'targets': target_data,
            'can_edit': user_profile.can_edit_plan_item(item) if user_profile else False,
        })
    
    # Get recent updates for this KPA
    all_targets = Target.objects.filter(plan_item__kpa=kpa, is_active=True)
    recent_updates = ProgressUpdate.objects.filter(
        target__in=all_targets,
        is_active=True
    ).order_by('-period_end')[:10]
    
    context = {
        'kpa': kpa,
        'plan_item_data': plan_item_data,
        'recent_updates': recent_updates,
        'can_edit_kpa': (user_profile.primary_role == 'SENIOR_MANAGER' and kpa.owner == request.user) if user_profile else False,
    }
    
    return render(request, 'manager/kpa_detail.html', context)


@login_required
def manager_progress_update_view(request, target_id):
    """Create or update progress for a specific target"""
    from progress.forms import EvidenceFileForm, EvidenceUrlForm

    target = get_object_or_404(Target, id=target_id, is_active=True)
    user_profile = getattr(request.user, 'profile', None)

    # Check if user can edit this target's plan item
    if not user_profile or not user_profile.can_edit_plan_item(target.plan_item):
        messages.error(request, "You don't have permission to update this target.")
        return redirect('manager_kpa_detail', kpa_id=target.plan_item.kpa.id)

    # Get or create progress update for current period
    current_period = target.get_current_period()
    progress_update, created = ProgressUpdate.objects.get_or_create(
        target=target,
        period_start=current_period['start'],
        period_end=current_period['end'],
        defaults={
            'period_type': target.periodicity.upper(),
            'period_name': current_period['name'],
            'actual_value': 0,
            'narrative': '',
            'created_by': request.user,
        }
    )

    # Get previous update for context
    previous_update = ProgressUpdate.objects.filter(
        target=target,
        period_end__lt=current_period['start']
    ).order_by('-period_end').first()

    # Initialize forms
    evidence_file_form = EvidenceFileForm(user=request.user)
    evidence_url_form = EvidenceUrlForm()

    if request.method == 'POST':
        form_type = request.POST.get('form_type', 'progress')

        if form_type == 'progress':
            form = ProgressUpdateForm(request.POST, instance=progress_update, previous_update=previous_update)
            if form.is_valid():
                progress_update = form.save(commit=False)
                progress_update.updated_by = request.user
                progress_update.save()

                # Create detailed success message and send notifications
                if progress_update.is_submitted:
                    # Store success details in session for success page
                    request.session['progress_success'] = {
                        'target_name': target.name,
                        'actual_value': progress_update.actual_value,
                        'unit': target.get_unit_display,
                        'percentage': round(progress_update.percentage_complete, 1),
                        'rag_status': progress_update.rag_status,
                        'period_name': progress_update.period_name,
                        'submitted_at': progress_update.updated_at.strftime('%B %d, %Y at %I:%M %p'),
                        'kpa_name': target.plan_item.kpa.title,
                        'action': 'submitted'
                    }

                    messages.success(
                        request,
                        f"🎉 SUCCESS! Progress update for '{target.name}' has been successfully submitted for approval! "
                        f"Your update shows {progress_update.actual_value} {target.get_unit_display} "
                        f"({progress_update.percentage_complete:.1f}% complete) with {progress_update.rag_status} status. "
                        f"Approvers have been notified and you'll receive confirmation once reviewed."
                    )

                    # Send notification to approvers
                    try:
                        from notifications.services import NotificationService
                        from accounts.models import UserProfile

                        # Get potential approvers (Senior Managers and Programme Managers)
                        approvers = User.objects.filter(
                            profile__primary_role__in=['SENIOR_MANAGER', 'PROGRAMME_MANAGER'],
                            profile__can_approve_updates=True,
                            profile__is_active_user=True,
                            is_active=True
                        )

                        # Filter approvers who can access this KPA
                        accessible_approvers = []
                        for approver in approvers:
                            if approver.profile.can_edit_plan_item(target.plan_item):
                                accessible_approvers.append(approver)

                        if accessible_approvers:
                            approval_url = request.build_absolute_uri(
                                f"/manager/approve/{progress_update.id}/"
                            )

                            NotificationService.send_approval_notification(
                                title=f"Progress Update Approval Required: {target.name}",
                                message=f"A progress update has been submitted for approval.\n\n"
                                       f"Target: {target.name}\n"
                                       f"Submitted by: {request.user.get_full_name()}\n"
                                       f"Actual Value: {progress_update.actual_value} {target.get_unit_display}\n"
                                       f"RAG Status: {progress_update.rag_status}\n"
                                       f"Completion: {progress_update.percentage_complete:.1f}%\n\n"
                                       f"Please review and approve this progress update.",
                                approvers=accessible_approvers,
                                sender=request.user,
                                related_url=approval_url,
                                related_object_type='ProgressUpdate',
                                related_object_id=str(progress_update.id)
                            )
                    except Exception as e:
                        # Don't fail the main operation if notification fails
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.error(f"Failed to send approval notification: {e}")

                else:
                    # Store draft success details in session
                    request.session['progress_success'] = {
                        'target_name': target.name,
                        'actual_value': progress_update.actual_value,
                        'unit': target.get_unit_display,
                        'percentage': round(progress_update.percentage_complete, 1),
                        'rag_status': progress_update.rag_status,
                        'period_name': progress_update.period_name,
                        'saved_at': progress_update.updated_at.strftime('%B %d, %Y at %I:%M %p'),
                        'kpa_name': target.plan_item.kpa.title,
                        'action': 'saved_draft'
                    }

                    messages.success(
                        request,
                        f"💾 DRAFT SAVED! Progress update for '{target.name}' has been saved successfully! "
                        f"Your update shows {progress_update.actual_value} {target.get_unit_display} "
                        f"({progress_update.percentage_complete:.1f}% complete). "
                        f"Remember to submit for approval when you're ready."
                    )

                # Redirect to success page instead of KPA detail
                return redirect('progress_success', target_id=target_id)

        elif form_type == 'evidence_file':
            evidence_file_form = EvidenceFileForm(request.POST, request.FILES, user=request.user)
            if evidence_file_form.is_valid():
                evidence_file = evidence_file_form.save(commit=False)
                evidence_file.progress_update = progress_update
                evidence_file.save()

                messages.success(
                    request,
                    f"📎 Evidence file '{evidence_file.original_filename}' ({evidence_file.file_size_mb}MB) "
                    f"has been successfully uploaded and attached to your progress update!"
                )
                return redirect('manager_progress_update', target_id=target_id)

        elif form_type == 'evidence_url':
            evidence_url_form = EvidenceUrlForm(request.POST)
            if evidence_url_form.is_valid():
                url = evidence_url_form.cleaned_data['url']
                description = evidence_url_form.cleaned_data['description']

                # Add URL to evidence_urls list
                evidence_urls = progress_update.evidence_urls or []
                evidence_urls.append({
                    'url': url,
                    'description': description,
                    'added_by': request.user.get_full_name() or request.user.username,
                    'added_at': timezone.now().isoformat()
                })
                progress_update.evidence_urls = evidence_urls
                progress_update.save()

                messages.success(
                    request,
                    f"🔗 Evidence URL has been successfully added to your progress update! "
                    f"Link: {description or url[:50]}..."
                )
                return redirect('manager_progress_update', target_id=target_id)
    else:
        form = ProgressUpdateForm(instance=progress_update, previous_update=previous_update)

    # Get existing evidence
    evidence_files = progress_update.uploaded_evidence.filter(is_active=True).order_by('-uploaded_at')
    evidence_urls = progress_update.evidence_urls or []

    context = {
        'target': target,
        'form': form,
        'evidence_file_form': evidence_file_form,
        'evidence_url_form': evidence_url_form,
        'progress_update': progress_update,
        'previous_update': previous_update,
        'evidence_files': evidence_files,
        'evidence_urls': evidence_urls,
        'is_new': created,
        'evidence_required': progress_update.is_evidence_required(),
    }

    return render(request, 'manager/progress_update.html', context)


@login_required
@require_manager_role
def manager_targets_overview_view(request):
    """Overview of all targets requiring attention"""
    
    user_profile = getattr(request.user, 'profile', None)
    if not user_profile:
        return redirect('manager_dashboard')
    
    # Get accessible KPAs
    accessible_kpas = user_profile.get_accessible_kpas()
    
    # Get all targets from accessible KPAs
    all_targets = Target.objects.filter(
        plan_item__kpa__in=accessible_kpas,
        is_active=True
    ).select_related('plan_item', 'plan_item__kpa').order_by('due_date')
    
    # Categorize targets
    overdue_targets = []
    due_soon_targets = []
    on_track_targets = []
    
    today = date.today()
    week_from_now = today + timedelta(days=7)
    
    for target in all_targets:
        latest_update = target.progress_updates.filter(is_active=True).order_by('-period_end').first()
        
        target_info = {
            'target': target,
            'latest_update': latest_update,
            'rag_status': target.get_rag_status() if latest_update else 'GREY',
            'is_overdue': target.is_overdue_for_update(),
            'can_edit': user_profile.can_edit_plan_item(target.plan_item),
        }
        
        if target_info['is_overdue']:
            overdue_targets.append(target_info)
        elif target.due_date and target.due_date <= week_from_now:
            due_soon_targets.append(target_info)
        else:
            on_track_targets.append(target_info)
    
    context = {
        'overdue_targets': overdue_targets,
        'due_soon_targets': due_soon_targets,
        'on_track_targets': on_track_targets,
        'total_targets': len(overdue_targets) + len(due_soon_targets) + len(on_track_targets),
    }
    
    return render(request, 'manager/targets_overview.html', context)


@login_required
@require_manager_role
def manager_evidence_delete_view(request, evidence_id):
    """Delete an evidence file"""
    from progress.models import EvidenceFile

    evidence_file = get_object_or_404(EvidenceFile, id=evidence_id, is_active=True)

    # Check permissions
    user_profile = getattr(request.user, 'profile', None)
    if not user_profile or not user_profile.can_edit_plan_item(evidence_file.progress_update.target.plan_item):
        messages.error(request, "You don't have permission to delete this evidence file.")
        return redirect('manager_dashboard')

    # Only allow deletion by the uploader or managers
    if evidence_file.uploaded_by != request.user and not user_profile.primary_role in ['SENIOR_MANAGER', 'PROGRAMME_MANAGER']:
        messages.error(request, "You can only delete evidence files that you uploaded.")
        return redirect('manager_progress_update', target_id=evidence_file.progress_update.target.id)

    if request.method == 'POST':
        filename = evidence_file.original_filename
        target_id = evidence_file.progress_update.target.id

        # Mark as inactive instead of deleting
        evidence_file.is_active = False
        evidence_file.save()

        messages.success(request, f"Evidence file '{filename}' has been deleted.")
        return redirect('manager_progress_update', target_id=target_id)

    context = {
        'evidence_file': evidence_file,
        'target': evidence_file.progress_update.target,
    }

    return render(request, 'manager/evidence_delete_confirm.html', context)


@login_required
@require_manager_role
def manager_approval_dashboard_view(request):
    """Dashboard for senior managers to approve progress updates"""

    user_profile = getattr(request.user, 'profile', None)
    if not user_profile:
        return redirect('manager_dashboard')

    # Only senior managers and programme managers can approve
    if user_profile.primary_role not in ['SENIOR_MANAGER', 'PROGRAMME_MANAGER']:
        messages.error(request, "You don't have permission to approve progress updates.")
        return redirect('manager_dashboard')

    # Get accessible KPAs
    accessible_kpas = user_profile.get_accessible_kpas()

    # Get pending progress updates for approval
    pending_updates = ProgressUpdate.objects.filter(
        target__plan_item__kpa__in=accessible_kpas,
        is_submitted=True,
        is_approved=False,
        is_active=True
    ).select_related(
        'target', 'target__plan_item', 'target__plan_item__kpa', 'created_by'
    ).order_by('-updated_at')

    # Get recently approved updates
    recent_approvals = ProgressUpdate.objects.filter(
        target__plan_item__kpa__in=accessible_kpas,
        is_approved=True,
        approved_at__gte=timezone.now() - timedelta(days=30)
    ).select_related(
        'target', 'target__plan_item', 'target__plan_item__kpa', 'approved_by'
    ).order_by('-approved_at')[:10]

    context = {
        'pending_updates': pending_updates,
        'recent_approvals': recent_approvals,
        'pending_count': pending_updates.count(),
    }

    return render(request, 'manager/approval_dashboard.html', context)


@login_required
@require_manager_role
def manager_progress_approval_view(request, update_id):
    """Approve or reject a specific progress update"""

    progress_update = get_object_or_404(ProgressUpdate, id=update_id, is_active=True)
    user_profile = getattr(request.user, 'profile', None)

    # Check permissions
    if not user_profile or not user_profile.can_edit_plan_item(progress_update.target.plan_item):
        messages.error(request, "You don't have permission to approve this progress update.")
        return redirect('manager_dashboard')

    # Only senior managers and programme managers can approve
    if user_profile.primary_role not in ['SENIOR_MANAGER', 'PROGRAMME_MANAGER']:
        messages.error(request, "You don't have permission to approve progress updates.")
        return redirect('manager_dashboard')

    # Must be submitted for approval
    if not progress_update.is_submitted:
        messages.error(request, "This progress update has not been submitted for approval.")
        return redirect('manager_approval_dashboard')

    if request.method == 'POST':
        action = request.POST.get('action')
        approval_comments = request.POST.get('approval_comments', '')

        if action == 'approve':
            progress_update.is_approved = True
            progress_update.approved_by = request.user
            progress_update.approved_at = timezone.now()
            progress_update.approval_comments = approval_comments
            progress_update.save()

            messages.success(request, f"Progress update for {progress_update.target.name} has been approved.")

            # Send notification to submitter
            try:
                from notifications.services import NotificationService

                NotificationService.send_notification(
                    title=f"Progress Update Approved: {progress_update.target.name}",
                    message=f"Your progress update has been approved.\n\n"
                           f"Target: {progress_update.target.name}\n"
                           f"Approved by: {request.user.get_full_name()}\n"
                           f"Approval Date: {timezone.now().strftime('%B %d, %Y at %H:%M')}\n\n"
                           f"Comments: {approval_comments or 'No additional comments.'}\n\n"
                           f"Thank you for your submission!",
                    recipients=[progress_update.created_by],
                    sender=request.user,
                    message_type='APPROVAL_RESPONSE',
                    priority='NORMAL',
                    channel_name='APPROVAL',
                    related_object_type='ProgressUpdate',
                    related_object_id=str(progress_update.id)
                )
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to send approval notification: {e}")

        elif action == 'reject':
            progress_update.is_submitted = False
            progress_update.is_approved = False
            progress_update.approval_comments = approval_comments
            progress_update.save()

            messages.warning(request, f"Progress update for {progress_update.target.name} has been rejected and returned for revision.")

            # Send notification to submitter
            try:
                from notifications.services import NotificationService

                NotificationService.send_notification(
                    title=f"Progress Update Requires Revision: {progress_update.target.name}",
                    message=f"Your progress update has been returned for revision.\n\n"
                           f"Target: {progress_update.target.name}\n"
                           f"Reviewed by: {request.user.get_full_name()}\n"
                           f"Review Date: {timezone.now().strftime('%B %d, %Y at %H:%M')}\n\n"
                           f"Comments: {approval_comments or 'Please review and resubmit.'}\n\n"
                           f"Please make the necessary changes and resubmit for approval.",
                    recipients=[progress_update.created_by],
                    sender=request.user,
                    message_type='APPROVAL_RESPONSE',
                    priority='HIGH',
                    channel_name='APPROVAL',
                    requires_acknowledgment=True,
                    related_object_type='ProgressUpdate',
                    related_object_id=str(progress_update.id)
                )
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to send rejection notification: {e}")

        return redirect('manager_approval_dashboard')

    # Get evidence files and URLs
    evidence_files = progress_update.uploaded_evidence.filter(is_active=True).order_by('-uploaded_at')
    evidence_urls = progress_update.evidence_urls or []

    context = {
        'progress_update': progress_update,
        'target': progress_update.target,
        'evidence_files': evidence_files,
        'evidence_urls': evidence_urls,
        'evidence_required': progress_update.is_evidence_required(),
    }

    return render(request, 'manager/progress_approval.html', context)


@login_required
def progress_success_view(request, target_id):
    """Success page after progress update submission"""
    target = get_object_or_404(Target, id=target_id, is_active=True)

    # Get success details from session
    success_data = request.session.pop('progress_success', None)

    if not success_data:
        # If no success data, redirect to manager dashboard
        messages.info(request, "Progress update completed successfully.")
        return redirect('manager_dashboard')

    # Get the latest progress update for additional context
    latest_update = ProgressUpdate.objects.filter(
        target=target,
        is_active=True
    ).order_by('-updated_at').first()

    context = {
        'target': target,
        'success_data': success_data,
        'latest_update': latest_update,
        'kpa': target.plan_item.kpa,
    }

    return render(request, 'manager/progress_success.html', context)
