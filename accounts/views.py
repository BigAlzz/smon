"""
Authentication and user management views for KPA Monitoring system
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView
from django.core.exceptions import PermissionDenied
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
import json

from .models import UserProfile, AuditLog
from core.permissions import require_role


class LoginView(TemplateView):
    """Custom login view with audit logging"""
    template_name = 'accounts/login.html'

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('dashboard')
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        username = request.POST.get('username')
        password = request.POST.get('password')

        if not username or not password:
            messages.error(request, 'Username and password are required.')
            return self.get(request, *args, **kwargs)

        user = authenticate(request, username=username, password=password)

        if user is not None:
            if user.is_active:
                login(request, user)

                # Log successful login
                AuditLog.objects.create(
                    user=user,
                    user_email=user.email,
                    user_ip_address=self._get_client_ip(request),
                    action='LOGIN',
                    model_name='AUTH',
                    object_id=str(user.id),
                    object_repr=f"User {user.username}",
                    session_key=request.session.session_key
                )

                messages.success(request, f'Welcome back, {user.get_full_name() or user.username}!')

                # Redirect to next page or profile (placeholder until dashboard is built)
                next_page = request.GET.get('next', 'profile')
                return redirect(next_page)
            else:
                messages.error(request, 'Your account has been disabled.')
        else:
            messages.error(request, 'Invalid username or password.')

            # Log failed login attempt
            AuditLog.objects.create(
                user=None,
                user_email=username,  # Store attempted username
                user_ip_address=self._get_client_ip(request),
                action='LOGIN',
                model_name='AUTH',
                object_id='FAILED',
                object_repr=f"Failed login attempt for {username}",
                additional_data={'status': 'FAILED'},
                session_key=request.session.session_key
            )

        return self.get(request, *args, **kwargs)

    def _get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


@login_required
def logout_view(request):
    """Custom logout view with audit logging"""
    user = request.user

    # Log logout
    AuditLog.objects.create(
        user=user,
        user_email=user.email,
        user_ip_address=request.META.get('REMOTE_ADDR'),
        action='LOGOUT',
        model_name='AUTH',
        object_id=str(user.id),
        object_repr=f"User {user.username}",
        session_key=request.session.session_key
    )

    logout(request)
    messages.success(request, 'You have been successfully logged out.')
    return redirect('login')


@login_required
def profile_view(request):
    """Comprehensive user profile view and edit"""
    from .forms import UserProfileForm, DashboardPreferencesForm, ProfilePictureForm

    user_profile, created = UserProfile.objects.get_or_create(user=request.user)

    # Handle form submissions
    if request.method == 'POST':
        form_type = request.POST.get('form_type')

        if form_type == 'profile':
            profile_form = UserProfileForm(
                request.POST,
                instance=user_profile,
                user=request.user
            )

            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, 'Profile information updated successfully.')
                return redirect('profile')
            else:
                # Add error highlighting to form fields
                profile_form.add_error_classes()
                messages.error(request, 'Please correct the errors below.')

        elif form_type == 'preferences':
            preferences_form = DashboardPreferencesForm(request.POST)

            if preferences_form.is_valid():
                # Update dashboard preferences
                dashboard_prefs = {
                    'default_view': preferences_form.cleaned_data['default_view'],
                    'items_per_page': int(preferences_form.cleaned_data['items_per_page']),
                    'show_completed': preferences_form.cleaned_data['show_completed'],
                    'show_inactive': preferences_form.cleaned_data['show_inactive'],
                    'email_digest_frequency': preferences_form.cleaned_data['email_digest_frequency'],
                    'theme_preference': preferences_form.cleaned_data['theme_preference'],
                }
                user_profile.dashboard_preferences = dashboard_prefs
                user_profile.save()

                messages.success(request, 'Dashboard preferences updated successfully.')
                return redirect('profile')
            else:
                messages.error(request, 'Please correct the errors in preferences.')

        elif form_type == 'picture':
            picture_form = ProfilePictureForm(request.POST, request.FILES)

            if picture_form.is_valid():
                if picture_form.cleaned_data['profile_picture']:
                    # Delete old picture if exists
                    if user_profile.profile_picture:
                        user_profile.profile_picture.delete()

                    user_profile.profile_picture = picture_form.cleaned_data['profile_picture']
                    user_profile.save()

                    messages.success(request, 'Profile picture updated successfully.')
                else:
                    messages.error(request, 'Please select a picture to upload.')
                return redirect('profile')
            else:
                messages.error(request, 'Please correct the errors in the picture upload.')

    # Initialize forms for GET request
    profile_form = UserProfileForm(instance=user_profile, user=request.user)
    picture_form = ProfilePictureForm()

    # Initialize preferences form with current values
    current_prefs = user_profile.dashboard_preferences or {}
    preferences_form = DashboardPreferencesForm(initial={
        'default_view': current_prefs.get('default_view', 'dashboard'),
        'items_per_page': current_prefs.get('items_per_page', 20),
        'show_completed': current_prefs.get('show_completed', True),
        'show_inactive': current_prefs.get('show_inactive', False),
        'email_digest_frequency': current_prefs.get('email_digest_frequency', 'weekly'),
        'theme_preference': current_prefs.get('theme_preference', 'light'),
    })

    # Get user statistics
    accessible_kpas = user_profile.get_accessible_kpas()

    # Get recent activity
    recent_logs = []
    try:
        recent_logs = AuditLog.objects.filter(
            user=request.user
        ).order_by('-timestamp')[:10]
    except:
        pass  # AuditLog might not be available

    context = {
        'user_profile': user_profile,
        'profile_form': profile_form,
        'picture_form': picture_form,
        'preferences_form': preferences_form,
        'accessible_kpas': accessible_kpas[:10],  # Show first 10
        'total_accessible_kpas': accessible_kpas.count(),
        'recent_logs': recent_logs,
        'user_stats': {
            'kpas_count': accessible_kpas.count(),
            'is_manager': user_profile.primary_role in ['SENIOR_MANAGER', 'PROGRAMME_MANAGER'],
            'can_approve': user_profile.can_approve_updates,
            'can_generate_reports': user_profile.can_generate_reports,
        }
    }
    return render(request, 'accounts/profile.html', context)


@login_required
def change_password_view(request):
    """Change password view with custom form"""
    from .forms import CustomPasswordChangeForm

    if request.method == 'POST':
        form = CustomPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Keep user logged in

            # Log password change
            AuditLog.objects.create(
                user=user,
                user_email=user.email,
                user_ip_address=request.META.get('REMOTE_ADDR'),
                action='UPDATE',
                model_name='AUTH',
                object_id=str(user.id),
                object_repr=f"Password changed for {user.username}",
                session_key=request.session.session_key
            )

            messages.success(request, 'Your password has been changed successfully.')
            return redirect('profile')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CustomPasswordChangeForm(request.user)

    return render(request, 'accounts/change_password.html', {'form': form})


@require_role('SYSTEM_ADMIN', 'SENIOR_MANAGER', 'PROGRAMME_MANAGER', 'ME_STRATEGY')
def user_management_view(request):
    """Enhanced user management interface for authorized staff"""
    from django.core.paginator import Paginator
    from django.db.models import Count, Q

    # Base queryset with related data
    users = User.objects.select_related('profile').prefetch_related('direct_reports')

    # Role-based access control - limit what users can see based on their role
    current_user_profile = getattr(request.user, 'profile', None)
    if current_user_profile:
        if current_user_profile.primary_role == 'PROGRAMME_MANAGER':
            # Programme managers can see users in their department/unit and their direct reports
            if current_user_profile.department:
                users = users.filter(
                    Q(profile__department=current_user_profile.department) |
                    Q(profile__line_manager=request.user) |
                    Q(id=request.user.id)  # Always include self
                )
            else:
                # If no department set, can only see self and direct reports
                users = users.filter(
                    Q(profile__line_manager=request.user) |
                    Q(id=request.user.id)
                )
        elif current_user_profile.primary_role == 'ME_STRATEGY':
            # M&E Strategy can see M&E related users and their direct reports
            users = users.filter(
                Q(profile__primary_role__in=['ME_STRATEGY', 'PROGRAMME_MANAGER']) |
                Q(profile__line_manager=request.user) |
                Q(id=request.user.id)  # Always include self
            )
        # SYSTEM_ADMIN and SENIOR_MANAGER can see all users (no additional filtering)

    # Filter parameters
    status_filter = request.GET.get('status', 'active')  # active, inactive, all
    role_filter = request.GET.get('role', '')
    department_filter = request.GET.get('department', '')
    search_query = request.GET.get('search', '')

    # Apply status filter
    if status_filter == 'active':
        users = users.filter(is_active=True, profile__is_active_user=True)
    elif status_filter == 'inactive':
        users = users.filter(Q(is_active=False) | Q(profile__is_active_user=False))
    # 'all' shows both active and inactive

    # Apply role filter
    if role_filter:
        users = users.filter(profile__primary_role=role_filter)

    # Apply department filter
    if department_filter:
        users = users.filter(profile__department=department_filter)

    # Search functionality
    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(profile__employee_number__icontains=search_query) |
            Q(profile__job_title__icontains=search_query)
        )

    # Annotate with additional data
    users = users.annotate(
        direct_reports_count=Count('direct_reports', distinct=True)
    )

    # Pagination
    paginator = Paginator(users.order_by('last_name', 'first_name'), 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Get filter options
    departments = UserProfile.objects.filter(
        user__is_active=True
    ).values_list('department', flat=True).distinct().order_by('department')

    # Statistics
    total_users = User.objects.filter(is_active=True).count()
    active_users = User.objects.filter(is_active=True, profile__is_active_user=True).count()
    inactive_users = total_users - active_users

    role_stats = UserProfile.objects.filter(
        user__is_active=True,
        is_active_user=True
    ).values('primary_role').annotate(count=Count('id')).order_by('primary_role')

    # Determine user capabilities based on role
    user_capabilities = {
        'can_create_users': current_user_profile and current_user_profile.primary_role in ['SYSTEM_ADMIN', 'SENIOR_MANAGER'],
        'can_edit_all_users': current_user_profile and current_user_profile.primary_role in ['SYSTEM_ADMIN', 'SENIOR_MANAGER'],
        'can_delete_users': current_user_profile and current_user_profile.primary_role == 'SYSTEM_ADMIN',
        'can_manage_permissions': current_user_profile and current_user_profile.primary_role == 'SYSTEM_ADMIN',
        'current_user_role': current_user_profile.get_primary_role_display() if current_user_profile else 'Unknown',
    }

    context = {
        'page_obj': page_obj,
        'role_choices': UserProfile.ROLE_CHOICES,
        'departments': [d for d in departments if d],
        'current_filters': {
            'status': status_filter,
            'role': role_filter,
            'department': department_filter,
            'search': search_query,
        },
        'statistics': {
            'total_users': total_users,
            'active_users': active_users,
            'inactive_users': inactive_users,
            'role_stats': role_stats,
        },
        'user_capabilities': user_capabilities,
    }

    return render(request, 'accounts/user_management.html', context)


@require_role('SYSTEM_ADMIN', 'SENIOR_MANAGER', 'PROGRAMME_MANAGER', 'ME_STRATEGY')
def user_detail_view(request, user_id):
    """User detail view for authorized staff"""
    user = get_object_or_404(User, id=user_id)
    user_profile = getattr(user, 'profile', None)

    # Get recent audit logs for this user
    recent_logs = AuditLog.objects.filter(user=user).order_by('-timestamp')[:20]

    context = {
        'viewed_user': user,
        'user_profile': user_profile,
        'recent_logs': recent_logs,
    }
    return render(request, 'accounts/user_detail.html', context)


@login_required
def admin_edit_user_view(request, user_id):
    """Comprehensive user editing view for authorized users"""
    from django.contrib.auth.forms import AdminPasswordChangeForm
    from .forms import UserProfileForm

    user = get_object_or_404(User, id=user_id)
    user_profile = getattr(user, 'profile', None)
    current_user_profile = getattr(request.user, 'profile', None)

    # Check permissions
    can_edit = False
    can_change_password = False
    can_edit_permissions = False

    if current_user_profile:
        # System admin can edit anyone
        if current_user_profile.primary_role == 'SYSTEM_ADMIN':
            can_edit = True
            can_change_password = True
            can_edit_permissions = True
        # Users can edit their own profile
        elif request.user.id == user.id:
            can_edit = True
            can_change_password = True
        # Senior managers can edit their direct reports
        elif current_user_profile.primary_role == 'SENIOR_MANAGER' and user_profile and user_profile.line_manager == request.user:
            can_edit = True
            can_change_password = True
        # Staff with admin permissions can edit profiles
        elif request.user.is_staff:
            can_edit = True
            if request.user.is_superuser:
                can_change_password = True
                can_edit_permissions = True

    if not can_edit:
        messages.error(request, 'You do not have permission to edit this user profile.')
        return redirect('user_management')

    # Create profile if it doesn't exist
    if not user_profile:
        user_profile = UserProfile.objects.create(user=user)

    if request.method == 'POST':
        action = request.POST.get('action')


        if action == 'update_user' and can_edit:
            # Update basic user information
            user.first_name = request.POST.get('first_name', '')
            user.last_name = request.POST.get('last_name', '')
            user.email = request.POST.get('email', '')

            # Only allow permission changes for system admins and superusers
            if can_edit_permissions:
                user.is_active = request.POST.get('is_active') == 'on'
                user.is_staff = request.POST.get('is_staff') == 'on'
                user.is_superuser = request.POST.get('is_superuser') == 'on'

            user.save()
            messages.success(request, f'User information for {user.username} updated successfully.')

        elif action == 'update_profile' and can_edit:
            # Update profile information
            profile_form = UserProfileForm(request.POST, request.FILES, instance=user_profile, user=user)

            if profile_form.is_valid():
                # Save the profile using the form's save method
                profile = profile_form.save(commit=True)

                # Only allow role changes for system admins
                if not can_edit_permissions and 'primary_role' in profile_form.cleaned_data:
                    profile.primary_role = user_profile.primary_role  # Keep original role
                    profile.save()

                messages.success(request, f'Profile information for {user.username} updated successfully.')
            else:
                # Add error highlighting to form fields
                profile_form.add_error_classes()
                # Debug form errors
                for field, errors in profile_form.errors.items():
                    for error in errors:
                        messages.error(request, f'{field}: {error}')
                messages.error(request, 'Please correct the errors in the profile form.')

        elif action == 'change_password' and can_change_password:
            # Change password
            if request.user.id == user.id:
                # User changing their own password - use regular form
                from django.contrib.auth.forms import PasswordChangeForm
                password_form = PasswordChangeForm(user, request.POST)
            else:
                # Admin changing someone else's password
                password_form = AdminPasswordChangeForm(user, request.POST)

            if password_form.is_valid():
                password_form.save()
                messages.success(request, f'Password for {user.username} changed successfully.')
            else:
                messages.error(request, 'Please correct the errors in the password form.')
        else:
            messages.error(request, 'You do not have permission to perform this action.')

        return redirect('admin_edit_user', user_id=user.id)

    # Initialize forms
    profile_form = UserProfileForm(instance=user_profile, user=user)

    # Initialize password form based on permissions
    if can_change_password:
        if request.user.id == user.id:
            from django.contrib.auth.forms import PasswordChangeForm
            password_form = PasswordChangeForm(user)
        else:
            password_form = AdminPasswordChangeForm(user)
    else:
        password_form = None

    # Get staff member if linked
    staff_member = None
    if user_profile and user_profile.staff_member:
        staff_member = user_profile.staff_member

    context = {
        'edited_user': user,
        'user_profile': user_profile,
        'profile_form': profile_form,
        'password_form': password_form,
        'staff_member': staff_member,
        'can_edit': can_edit,
        'can_change_password': can_change_password,
        'can_edit_permissions': can_edit_permissions,
        'is_editing_self': request.user.id == user.id,
    }

    return render(request, 'accounts/admin_edit_user.html', context)


# API Views for JWT authentication
@api_view(['POST'])
def api_login(request):
    """API login endpoint that returns JWT tokens"""
    username = request.data.get('username')
    password = request.data.get('password')

    if not username or not password:
        return Response(
            {'error': 'Username and password are required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    user = authenticate(username=username, password=password)

    if user and user.is_active:
        refresh = RefreshToken.for_user(user)

        # Get user profile information
        user_profile = getattr(user, 'profile', None)
        profile_data = {}
        if user_profile:
            profile_data = {
                'role': user_profile.primary_role,
                'department': user_profile.department,
                'can_approve_updates': user_profile.can_approve_updates,
                'can_generate_reports': user_profile.can_generate_reports,
            }

        # Log API login
        AuditLog.objects.create(
            user=user,
            user_email=user.email,
            user_ip_address=request.META.get('REMOTE_ADDR'),
            action='LOGIN',
            model_name='API_AUTH',
            object_id=str(user.id),
            object_repr=f"API login for {user.username}",
            additional_data={'method': 'JWT'}
        )

        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'profile': profile_data
            }
        })

    return Response(
        {'error': 'Invalid credentials'},
        status=status.HTTP_401_UNAUTHORIZED
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_logout(request):
    """API logout endpoint"""
    try:
        refresh_token = request.data.get('refresh')
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()

        # Log API logout
        AuditLog.objects.create(
            user=request.user,
            user_email=request.user.email,
            user_ip_address=request.META.get('REMOTE_ADDR'),
            action='LOGOUT',
            model_name='API_AUTH',
            object_id=str(request.user.id),
            object_repr=f"API logout for {request.user.username}",
            additional_data={'method': 'JWT'}
        )

        return Response({'message': 'Successfully logged out'})
    except Exception as e:
        return Response(
            {'error': 'Invalid token'},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_profile(request):
    """API endpoint to get user profile information"""
    user = request.user
    user_profile = getattr(user, 'profile', None)

    profile_data = {
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'is_active': user.is_active,
        'date_joined': user.date_joined,
        'last_login': user.last_login,
    }

    if user_profile:
        profile_data.update({
            'employee_number': user_profile.employee_number,
            'job_title': user_profile.job_title,
            'department': user_profile.department,
            'primary_role': user_profile.primary_role,
            'phone_number': user_profile.phone_number,
            'mobile_number': user_profile.mobile_number,
            'can_view_all_kpas': user_profile.can_view_all_kpas,
            'can_approve_updates': user_profile.can_approve_updates,
            'can_generate_reports': user_profile.can_generate_reports,
            'dashboard_preferences': user_profile.dashboard_preferences,
        })

    return Response(profile_data)


def register_view(request):
    """Staff member registration view"""
    from .forms import StaffRegistrationForm
    from django.db import transaction

    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = StaffRegistrationForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Create user account
                    user = form.save()

                    # Link to staff member if PERSAL number provided
                    persal_number = form.cleaned_data.get('persal_number')
                    if persal_number:
                        try:
                            from core.models import Staff
                            staff_member = Staff.objects.get(
                                persal_number=persal_number,
                                is_active=True
                            )

                            # Create or update profile
                            profile, created = UserProfile.objects.get_or_create(
                                user=user,
                                defaults={
                                    'staff_member': staff_member,
                                    'employee_number': staff_member.persal_number,
                                    'job_title': staff_member.job_title,
                                    'department': staff_member.org_unit.name,
                                    'unit_subdirectorate': staff_member.org_unit.name,
                                    'primary_role': get_role_from_title(staff_member.job_title),
                                }
                            )

                            if not created:
                                profile.staff_member = staff_member
                                profile.employee_number = staff_member.persal_number
                                profile.job_title = staff_member.job_title
                                profile.department = staff_member.org_unit.name
                                profile.unit_subdirectorate = staff_member.org_unit.name
                                profile.primary_role = get_role_from_title(staff_member.job_title)
                                profile.save()

                            messages.success(
                                request,
                                f"Account created successfully! You are registered as {staff_member.job_title} "
                                f"in {staff_member.org_unit.name}."
                            )
                        except Staff.DoesNotExist:
                            # Create basic profile without staff link
                            UserProfile.objects.get_or_create(user=user)
                            messages.warning(
                                request,
                                "Account created, but PERSAL number not found in staff records. "
                                "Please contact HR to link your account to your staff profile."
                            )
                    else:
                        # Create basic profile
                        UserProfile.objects.get_or_create(user=user)
                        messages.success(request, "Account created successfully!")

                    # Auto-login the user
                    login(request, user)
                    return redirect('dashboard')

            except Exception as e:
                messages.error(request, f"Registration failed: {str(e)}")
    else:
        form = StaffRegistrationForm()

    return render(request, 'accounts/register.html', {'form': form})


def password_reset_view(request):
    """Password reset request view"""
    from .forms import CustomPasswordResetForm
    from django.core.mail import send_mail
    from django.conf import settings
    from django.urls import reverse
    from django.utils.http import urlsafe_base64_encode
    from django.utils.encoding import force_bytes
    from django.contrib.auth.tokens import default_token_generator
    from django.template.loader import render_to_string

    if request.method == 'POST':
        form = CustomPasswordResetForm(request.POST)
        if form.is_valid():
            # Get user by email or username
            identifier = form.cleaned_data['email_or_username']

            user = None
            if '@' in identifier:
                # Email provided
                try:
                    user = User.objects.get(email=identifier, is_active=True)
                except User.DoesNotExist:
                    pass
            else:
                # Username provided
                try:
                    user = User.objects.get(username=identifier, is_active=True)
                except User.DoesNotExist:
                    pass

            if user:
                # Generate reset token
                token = default_token_generator.make_token(user)
                uid = urlsafe_base64_encode(force_bytes(user.pk))

                # Create reset URL
                reset_url = request.build_absolute_uri(
                    reverse('password_reset_confirm', kwargs={'uidb64': uid, 'token': token})
                )

                # Send email
                subject = 'Password Reset - KPA Performance Monitoring System'
                message = render_to_string('accounts/password_reset_email.html', {
                    'user': user,
                    'reset_url': reset_url,
                    'site_name': 'KPA Performance Monitoring System',
                })

                try:
                    send_mail(
                        subject,
                        message,
                        settings.DEFAULT_FROM_EMAIL,
                        [user.email],
                        html_message=message,
                        fail_silently=False,
                    )
                    messages.success(
                        request,
                        "Password reset instructions have been sent to your email address."
                    )
                except Exception as e:
                    messages.error(
                        request,
                        "Failed to send password reset email. Please contact your administrator."
                    )
            else:
                # Don't reveal whether user exists or not
                messages.success(
                    request,
                    "If an account with that email/username exists, "
                    "password reset instructions have been sent."
                )

            return redirect('login')
    else:
        form = CustomPasswordResetForm()

    return render(request, 'accounts/password_reset.html', {'form': form})


def password_reset_confirm_view(request, uidb64, token):
    """Password reset confirmation view"""
    from .forms import CustomSetPasswordForm
    from django.utils.http import urlsafe_base64_decode
    from django.utils.encoding import force_str
    from django.contrib.auth.tokens import default_token_generator

    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        if request.method == 'POST':
            form = CustomSetPasswordForm(user, request.POST)
            if form.is_valid():
                form.save()
                messages.success(
                    request,
                    "Your password has been reset successfully! You can now log in with your new password."
                )
                return redirect('login')
        else:
            form = CustomSetPasswordForm(user)

        return render(request, 'accounts/password_reset_confirm.html', {
            'form': form,
            'validlink': True,
            'user': user,
        })
    else:
        return render(request, 'accounts/password_reset_confirm.html', {
            'validlink': False,
        })


@require_http_methods(["GET"])
def check_username_availability(request):
    """AJAX endpoint to check username availability"""
    username = request.GET.get('username', '').strip()

    if not username:
        return JsonResponse({'available': False, 'message': 'Username is required'})

    if len(username) < 3:
        return JsonResponse({'available': False, 'message': 'Username must be at least 3 characters'})

    if User.objects.filter(username=username).exists():
        return JsonResponse({'available': False, 'message': 'Username is already taken'})

    return JsonResponse({'available': True, 'message': 'Username is available'})


@require_http_methods(["GET"])
def check_persal_validity(request):
    """AJAX endpoint to check PERSAL number validity"""
    from core.models import Staff

    persal = request.GET.get('persal', '').strip()

    if not persal:
        return JsonResponse({'valid': False, 'message': 'PERSAL number is required'})

    try:
        staff_member = Staff.objects.get(persal_number=persal, is_active=True)

        # Check if already linked to a user
        if hasattr(staff_member, 'user_profile') and staff_member.user_profile:
            return JsonResponse({
                'valid': False,
                'message': 'This PERSAL number is already linked to another account'
            })

        return JsonResponse({
            'valid': True,
            'message': 'Valid PERSAL number',
            'staff_info': {
                'name': staff_member.full_name,
                'job_title': staff_member.job_title,
                'unit': staff_member.org_unit.name,
            }
        })
    except Staff.DoesNotExist:
        return JsonResponse({
            'valid': False,
            'message': 'PERSAL number not found in staff records'
        })


def get_role_from_title(job_title):
    """Determine user role based on job title"""
    title_upper = job_title.upper()

    if 'CEO' in title_upper or 'DIRECTOR-GENERAL' in title_upper:
        return 'SENIOR_MANAGER'
    elif 'CHIEF DIRECTOR' in title_upper or 'DIRECTOR:' in title_upper:
        return 'SENIOR_MANAGER'
    elif 'DD:' in title_upper or 'DEPUTY DIRECTOR' in title_upper:
        return 'PROGRAMME_MANAGER'
    elif 'ASD:' in title_upper or 'ASSISTANT DIRECTOR' in title_upper:
        return 'PROGRAMME_MANAGER'
    elif 'SAO:' in title_upper or 'SENIOR ADMINISTRATIVE' in title_upper:
        return 'ME_STRATEGY'
    else:
        return 'ME_STRATEGY'  # Default role for other staff
