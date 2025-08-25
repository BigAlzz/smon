"""
Forms for user account management and profile editing
"""

from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import PasswordChangeForm, UserCreationForm, SetPasswordForm
from django.core.exceptions import ValidationError
from .models import UserProfile
from core.models import Staff


class UserProfileForm(forms.ModelForm):
    """
    Comprehensive user profile form for editing personal and professional information
    """
    
    # User model fields - simplified
    first_name = forms.CharField(
        max_length=150,
        required=False,  # Make optional to avoid validation issues
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your first name'
        })
    )

    last_name = forms.CharField(
        max_length=150,
        required=False,  # Make optional to avoid validation issues
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your last name'
        })
    )

    email = forms.EmailField(
        required=False,  # Make optional to avoid validation issues
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email address'
        })
    )
    
    class Meta:
        model = UserProfile
        fields = [
            'primary_role',
            'employee_number',
            'phone_number',
            'mobile_number',
            'profile_picture',
            'line_manager',
            'is_active_user',
            'email_notifications',
            'can_view_all_kpas',
            'can_approve_updates',
            'can_generate_reports',
        ]
        
        widgets = {
            'primary_role': forms.Select(attrs={
                'class': 'form-select'
            }),
            'employee_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., EMP001'
            }),


            'phone_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., +27 11 123 4567'
            }),
            'mobile_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., +27 82 123 4567'
            }),
            'profile_picture': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'line_manager': forms.Select(attrs={
                'class': 'form-select'
            }),
            'is_active_user': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'email_notifications': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'can_view_all_kpas': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'can_approve_updates': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'can_generate_reports': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Populate user fields if instance exists
        if self.instance and hasattr(self.instance, 'user') and self.instance.user:
            self.fields['first_name'].initial = self.instance.user.first_name or ''
            self.fields['last_name'].initial = self.instance.user.last_name or ''
            self.fields['email'].initial = self.instance.user.email or ''

        # Create dropdown fields for organizational data
        try:
            from core.models import OrgUnit, Staff

            # Get organizational units and staff data
            org_units = OrgUnit.objects.filter(is_active=True).order_by('unit_type', 'name')

            # Department choices
            department_choices = [('', '— Select Department —')]
            for unit in org_units:
                department_choices.append((unit.name, f"{unit.name} ({unit.get_unit_type_display()})"))

            # Unit/subdirectorate choices
            unit_choices = [('', '— Select Unit —')]
            for unit in org_units:
                unit_choices.append((unit.name, unit.name))

            # Job title choices from existing staff
            job_titles = Staff.objects.filter(is_active=True).values_list('job_title', flat=True).distinct().order_by('job_title')
            job_title_choices = [('', '— Select Job Title —')]
            for title in job_titles:
                if title:  # Skip empty titles
                    job_title_choices.append((title, title))

            # Office location choices
            office_choices = [
                ('', '— Select Office Location —'),
                ('Head Office, Floor 1', 'Head Office, Floor 1'),
                ('Head Office, Floor 2', 'Head Office, Floor 2'),
                ('Head Office, Floor 3', 'Head Office, Floor 3'),
                ('Head Office, Floor 4', 'Head Office, Floor 4'),
                ('Head Office, Floor 5', 'Head Office, Floor 5'),
                ('Regional Office - Gauteng', 'Regional Office - Gauteng'),
                ('Regional Office - Western Cape', 'Regional Office - Western Cape'),
                ('Regional Office - KwaZulu-Natal', 'Regional Office - KwaZulu-Natal'),
                ('Remote/Home Office', 'Remote/Home Office'),
                ('Other', 'Other'),
            ]

            # Create the dropdown fields
            self.fields['department'] = forms.ChoiceField(
                choices=department_choices,
                required=False,
                widget=forms.Select(attrs={'class': 'form-select'}),
                initial=self.instance.department if self.instance else ''
            )

            self.fields['unit_subdirectorate'] = forms.ChoiceField(
                choices=unit_choices,
                required=False,
                widget=forms.Select(attrs={'class': 'form-select'}),
                initial=self.instance.unit_subdirectorate if self.instance else ''
            )

            self.fields['job_title'] = forms.ChoiceField(
                choices=job_title_choices,
                required=False,
                widget=forms.Select(attrs={'class': 'form-select'}),
                initial=self.instance.job_title if self.instance else ''
            )

            self.fields['office_location'] = forms.ChoiceField(
                choices=office_choices,
                required=False,
                widget=forms.Select(attrs={'class': 'form-select'}),
                initial=self.instance.office_location if self.instance else ''
            )

        except Exception:
            # Fallback to simple text fields if there's an error
            for field_name in ['department', 'unit_subdirectorate', 'job_title', 'office_location']:
                self.fields[field_name] = forms.CharField(
                    max_length=200,
                    required=False,
                    widget=forms.TextInput(attrs={'class': 'form-control'})
                )



        # Filter line manager choices to exclude self and inactive users
        if self.user:
            self.fields['line_manager'].queryset = User.objects.filter(
                is_active=True,
                profile__is_active_user=True
            ).exclude(id=self.user.id).order_by('first_name', 'last_name')

        # Add help text
        self.fields['employee_number'].help_text = "Your unique employee identifier"
        self.fields['line_manager'].help_text = "Select your direct line manager"
        self.fields['email_notifications'].help_text = "Receive email notifications for updates and reminders"

        # Handle primary_role field based on user permissions
        # If user is editing their own profile, make primary_role optional and hidden
        if (self.user and self.instance and hasattr(self.instance, 'user') and
            self.instance.user == self.user):
            # User is editing their own profile - hide primary_role and make it optional
            self.fields['primary_role'].widget = forms.HiddenInput()
            self.fields['primary_role'].required = False
            if self.instance.primary_role:
                self.fields['primary_role'].initial = self.instance.primary_role
        elif not self.user or not hasattr(self.user, 'profile') or not self.user.profile.primary_role == 'SYSTEM_ADMIN':
            # Non-admin users editing other profiles - also hide and make optional
            self.fields['primary_role'].widget = forms.HiddenInput()
            self.fields['primary_role'].required = False
            if self.instance and self.instance.primary_role:
                self.fields['primary_role'].initial = self.instance.primary_role

        # Apply error highlighting if form is bound and has errors
        if self.is_bound and self.errors:
            self.add_error_classes()

    def add_error_classes(self):
        """Add Bootstrap validation classes to fields with errors"""
        for field_name, field in self.fields.items():
            if field_name in self.errors:
                # Get current CSS classes
                current_classes = field.widget.attrs.get('class', '')

                # Add is-invalid class if not already present
                if 'is-invalid' not in current_classes:
                    field.widget.attrs['class'] = f"{current_classes} is-invalid".strip()
            else:
                # Remove is-invalid class if field is valid
                current_classes = field.widget.attrs.get('class', '')
                if 'is-invalid' in current_classes:
                    field.widget.attrs['class'] = current_classes.replace('is-invalid', '').strip()

    def clean_email(self):
        """Validate email uniqueness"""
        email = self.cleaned_data.get('email')
        if email and self.user:
            # Check if email is already taken by another user
            existing_user = User.objects.filter(email=email).exclude(id=self.user.id).first()
            if existing_user:
                raise ValidationError("This email address is already in use by another user.")
        return email
    
    def clean_employee_number(self):
        """Validate employee number uniqueness"""
        employee_number = self.cleaned_data.get('employee_number')
        if employee_number:
            # Check if employee number is already taken
            existing_profile = UserProfile.objects.filter(
                employee_number=employee_number
            ).exclude(id=self.instance.id if self.instance else None).first()
            if existing_profile:
                raise ValidationError("This employee number is already in use.")
        return employee_number

    def clean_phone_number(self):
        """Validate phone number format"""
        phone_number = self.cleaned_data.get('phone_number')
        if phone_number:
            # Remove spaces and dashes for validation
            cleaned_phone = phone_number.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
            if not cleaned_phone.isdigit():
                raise ValidationError("Phone number must contain only numbers, spaces, and dashes.")
            if len(cleaned_phone) < 10:
                raise ValidationError("Phone number must be at least 10 digits long.")
        return phone_number

    def clean_mobile_number(self):
        """Validate mobile number format"""
        mobile_number = self.cleaned_data.get('mobile_number')
        if mobile_number:
            # Remove spaces and dashes for validation
            cleaned_mobile = mobile_number.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
            if not cleaned_mobile.isdigit():
                raise ValidationError("Mobile number must contain only numbers, spaces, and dashes.")
            if len(cleaned_mobile) < 10:
                raise ValidationError("Mobile number must be at least 10 digits long.")
        return mobile_number

    def save(self, commit=True):
        """Save both user and profile data"""
        profile = super().save(commit=False)

        # Handle custom dropdown fields that aren't in the model form
        if hasattr(self, 'cleaned_data'):
            if 'job_title' in self.cleaned_data:
                profile.job_title = self.cleaned_data['job_title']
            if 'department' in self.cleaned_data:
                profile.department = self.cleaned_data['department']
            if 'unit_subdirectorate' in self.cleaned_data:
                profile.unit_subdirectorate = self.cleaned_data['unit_subdirectorate']
            if 'office_location' in self.cleaned_data:
                profile.office_location = self.cleaned_data['office_location']

        if commit:
            profile.save()

            # Update related User fields if they exist in cleaned_data
            if self.user and hasattr(self, 'cleaned_data'):
                user_updated = False
                if 'first_name' in self.cleaned_data and self.cleaned_data['first_name']:
                    self.user.first_name = self.cleaned_data['first_name']
                    user_updated = True
                if 'last_name' in self.cleaned_data and self.cleaned_data['last_name']:
                    self.user.last_name = self.cleaned_data['last_name']
                    user_updated = True
                if 'email' in self.cleaned_data and self.cleaned_data['email']:
                    self.user.email = self.cleaned_data['email']
                    user_updated = True

                if user_updated:
                    self.user.save()

        return profile


class DashboardPreferencesForm(forms.Form):
    """
    Form for managing user dashboard preferences
    """
    
    DEFAULT_VIEW_CHOICES = [
        ('dashboard', 'Main Dashboard'),
        ('kpa_list', 'KPA List'),
        ('plan_grid', 'Operational Plan Grid'),
        ('manager_dashboard', 'Manager Dashboard'),
    ]
    
    ITEMS_PER_PAGE_CHOICES = [
        (10, '10 items'),
        (20, '20 items'),
        (50, '50 items'),
        (100, '100 items'),
    ]
    
    default_view = forms.ChoiceField(
        choices=DEFAULT_VIEW_CHOICES,
        initial='dashboard',
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text="Page to show when you log in"
    )
    
    items_per_page = forms.ChoiceField(
        choices=ITEMS_PER_PAGE_CHOICES,
        initial=20,
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text="Number of items to show per page in lists"
    )
    
    show_completed = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text="Show completed items in lists and dashboards"
    )
    
    show_inactive = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text="Show inactive KPAs and plan items"
    )
    
    email_digest_frequency = forms.ChoiceField(
        choices=[
            ('never', 'Never'),
            ('daily', 'Daily'),
            ('weekly', 'Weekly'),
            ('monthly', 'Monthly'),
        ],
        initial='weekly',
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text="How often to receive email digest of your KPAs"
    )
    
    theme_preference = forms.ChoiceField(
        choices=[
            ('light', 'Light Theme'),
            ('dark', 'Dark Theme'),
            ('auto', 'Auto (System)'),
        ],
        initial='light',
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text="Visual theme preference"
    )


class CustomPasswordChangeForm(PasswordChangeForm):
    """
    Custom password change form with Bootstrap styling
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add Bootstrap classes to all fields
        for field_name, field in self.fields.items():
            field.widget.attrs.update({
                'class': 'form-control'
            })
        
        # Update help text
        self.fields['old_password'].help_text = "Enter your current password"
        self.fields['new_password1'].help_text = "Enter your new password (at least 8 characters)"
        self.fields['new_password2'].help_text = "Confirm your new password"


class ProfilePictureForm(forms.Form):
    """
    Form for uploading profile picture
    """
    
    profile_picture = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*'
        }),
        help_text="Upload a profile picture (JPG, PNG, max 2MB)"
    )
    
    def clean_profile_picture(self):
        """Validate profile picture"""
        picture = self.cleaned_data.get('profile_picture')
        
        if picture:
            # Check file size (2MB limit)
            if picture.size > 2 * 1024 * 1024:
                raise ValidationError("Image file too large. Maximum size is 2MB.")
            
            # Check file type
            if not picture.content_type.startswith('image/'):
                raise ValidationError("Please upload a valid image file.")
        
        return picture


class StaffRegistrationForm(UserCreationForm):
    """Registration form for staff members with PERSAL integration"""

    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'your.email@example.com'
        })
    )

    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'First Name'
        })
    )

    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Last Name'
        })
    )

    persal_number = forms.CharField(
        max_length=20,
        required=False,
        help_text="Enter your PERSAL number to link your account to your staff profile",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'PERSAL Number (Optional)',
            'id': 'id_persal_number'
        })
    )

    terms_accepted = forms.BooleanField(
        required=True,
        label="I accept the terms and conditions",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2')
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Username',
                'id': 'id_username'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Add Bootstrap classes to password fields
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Password'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Confirm Password'
        })

        # Update help texts
        self.fields['username'].help_text = "Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only."
        self.fields['password1'].help_text = "Your password must contain at least 8 characters and cannot be entirely numeric."

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError("A user with this email address already exists.")
        return email

    def clean_persal_number(self):
        persal_number = self.cleaned_data.get('persal_number')
        if persal_number:
            # Check if PERSAL number exists in staff records
            try:
                staff_member = Staff.objects.get(persal_number=persal_number, is_active=True)

                # Check if already linked to another user
                if hasattr(staff_member, 'user_profile') and staff_member.user_profile:
                    raise ValidationError("This PERSAL number is already linked to another user account.")

            except Staff.DoesNotExist:
                raise ValidationError("PERSAL number not found in staff records. You can still register without it.")

        return persal_number

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']

        if commit:
            user.save()
        return user


class CustomPasswordResetForm(forms.Form):
    """Custom password reset form that accepts email or username"""

    email_or_username = forms.CharField(
        max_length=254,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email address or username',
            'autocomplete': 'email'
        }),
        label="Email or Username"
    )

    def clean_email_or_username(self):
        identifier = self.cleaned_data['email_or_username']

        # Check if it's an email or username
        user_exists = False
        if '@' in identifier:
            # Email provided
            user_exists = User.objects.filter(email=identifier, is_active=True).exists()
        else:
            # Username provided
            user_exists = User.objects.filter(username=identifier, is_active=True).exists()

        if not user_exists:
            # Don't reveal whether user exists or not for security
            pass

        return identifier


class CustomSetPasswordForm(SetPasswordForm):
    """Custom set password form with Bootstrap styling"""

    def __init__(self, user, *args, **kwargs):
        super().__init__(user, *args, **kwargs)

        self.fields['new_password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'New Password'
        })
        self.fields['new_password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Confirm New Password'
        })
