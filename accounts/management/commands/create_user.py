"""
Management command to create users with temporary passwords
"""

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from accounts.models import UserProfile
import secrets
import string


class Command(BaseCommand):
    help = 'Create a new user with a temporary password'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Username for the new user')
        parser.add_argument('--email', type=str, help='Email address for the user')
        parser.add_argument('--first-name', type=str, help='First name')
        parser.add_argument('--last-name', type=str, help='Last name')
        parser.add_argument('--role', type=str, choices=[
            'SENIOR_MANAGER', 'PROGRAMME_MANAGER', 'UNIT_MANAGER', 
            'STAFF_MEMBER', 'ME_STRATEGY', 'SYSTEM_ADMIN'
        ], default='STAFF_MEMBER', help='User role')
        parser.add_argument('--department', type=str, help='Department')
        parser.add_argument('--job-title', type=str, help='Job title')
        parser.add_argument('--staff', action='store_true', help='Give staff permissions')
        parser.add_argument('--superuser', action='store_true', help='Create as superuser')

    def handle(self, *args, **options):
        username = options['username']
        
        # Check if user already exists
        if User.objects.filter(username=username).exists():
            raise CommandError(f'User "{username}" already exists.')
        
        # Generate temporary password
        temp_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))
        
        # Create user
        user = User.objects.create_user(
            username=username,
            email=options.get('email', ''),
            first_name=options.get('first_name', ''),
            last_name=options.get('last_name', ''),
            password=temp_password
        )
        
        # Set permissions
        if options['staff'] or options['superuser']:
            user.is_staff = True
        
        if options['superuser']:
            user.is_superuser = True
        
        user.save()
        
        # Create or update profile
        profile, created = UserProfile.objects.get_or_create(user=user)
        profile.primary_role = options['role']
        if options.get('department'):
            profile.department = options['department']
        if options.get('job_title'):
            profile.job_title = options['job_title']
        profile.save()
        
        # Output results
        self.stdout.write(
            self.style.SUCCESS(f'Successfully created user "{username}"')
        )
        self.stdout.write(f'Temporary password: {temp_password}')
        self.stdout.write(f'Role: {profile.get_primary_role_display()}')
        if options.get('email'):
            self.stdout.write(f'Email: {options["email"]}')
        
        self.stdout.write(
            self.style.WARNING(
                'Please save this password and share it securely with the user. '
                'They should change it on first login.'
            )
        )
