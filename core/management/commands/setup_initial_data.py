"""
Management command to set up initial data for KPA Monitoring system
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from core.models import FinancialYear, KPA
from accounts.models import UserProfile
import uuid


class Command(BaseCommand):
    help = 'Set up initial data for KPA Monitoring system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--create-superuser',
            action='store_true',
            help='Create a superuser account',
        )
        parser.add_argument(
            '--superuser-username',
            type=str,
            default='admin',
            help='Username for superuser (default: admin)',
        )
        parser.add_argument(
            '--superuser-email',
            type=str,
            default='admin@gcra.org.za',
            help='Email for superuser',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Setting up initial data...'))
        
        with transaction.atomic():
            # Create groups and permissions
            self.create_groups_and_permissions()
            
            # Create financial years if they don't exist
            self.create_financial_years()
            
            # Create superuser if requested
            if options['create_superuser']:
                self.create_superuser(
                    options['superuser_username'],
                    options['superuser_email']
                )
        
        self.stdout.write(self.style.SUCCESS('Initial data setup completed!'))

    def create_groups_and_permissions(self):
        """Create user groups and assign permissions"""
        self.stdout.write('Creating user groups and permissions...')
        
        # Define groups and their permissions
        groups_permissions = {
            'Senior Managers': [
                'view_kpa', 'change_kpa', 'view_operationalplanitem',
                'view_target', 'view_progressupdate', 'change_progressupdate',
                'view_reportrequest', 'add_reportrequest', 'view_attachment'
            ],
            'Programme Managers': [
                'view_operationalplanitem', 'change_operationalplanitem',
                'view_target', 'change_target', 'add_target',
                'view_progressupdate', 'add_progressupdate', 'change_progressupdate',
                'view_costline', 'add_costline', 'change_costline',
                'view_attachment', 'add_attachment'
            ],
            'M&E Strategy': [
                'view_kpa', 'add_kpa', 'change_kpa',
                'view_operationalplanitem', 'add_operationalplanitem', 'change_operationalplanitem',
                'view_target', 'add_target', 'change_target',
                'view_progressupdate', 'view_reportrequest', 'add_reportrequest'
            ],
            'Finance': [
                'view_operationalplanitem', 'view_costline', 'add_costline', 'change_costline',
                'view_progressupdate', 'view_reportrequest', 'add_reportrequest'
            ],
            'System Admins': [
                # System admins get all permissions via is_staff/is_superuser
            ]
        }
        
        for group_name, permission_codenames in groups_permissions.items():
            group, created = Group.objects.get_or_create(name=group_name)
            if created:
                self.stdout.write(f'  Created group: {group_name}')
            
            # Add permissions to group
            for codename in permission_codenames:
                try:
                    permission = Permission.objects.get(codename=codename)
                    group.permissions.add(permission)
                except Permission.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(f'  Permission {codename} not found')
                    )

    def create_financial_years(self):
        """Create initial financial years"""
        self.stdout.write('Creating financial years...')
        
        financial_years = [
            {
                'year_code': 'FY 2024/25',
                'start_date': '2024-04-01',
                'end_date': '2025-03-31',
                'is_active': True,
                'description': 'Financial Year 2024/25 - Active operational plan period'
            },
            {
                'year_code': 'FY 2025/26',
                'start_date': '2025-04-01',
                'end_date': '2026-03-31',
                'is_active': False,
                'description': 'Financial Year 2025/26 - Planning phase'
            }
        ]
        
        for fy_data in financial_years:
            fy, created = FinancialYear.objects.get_or_create(
                year_code=fy_data['year_code'],
                defaults=fy_data
            )
            if created:
                self.stdout.write(f'  Created financial year: {fy.year_code}')

    def create_superuser(self, username, email):
        """Create superuser account with profile"""
        self.stdout.write(f'Creating superuser: {username}...')
        
        if User.objects.filter(username=username).exists():
            self.stdout.write(
                self.style.WARNING(f'  Superuser {username} already exists')
            )
            return
        
        # Create superuser
        user = User.objects.create_superuser(
            username=username,
            email=email,
            password='admin123',  # Default password - should be changed
            first_name='System',
            last_name='Administrator'
        )
        
        # Create user profile
        profile = UserProfile.objects.create(
            user=user,
            employee_number='ADMIN001',
            job_title='System Administrator',
            department='ICT',
            primary_role='SYSTEM_ADMIN',
            can_view_all_kpas=True,
            can_approve_updates=True,
            can_generate_reports=True
        )
        
        # Add to System Admins group
        admin_group = Group.objects.get(name='System Admins')
        user.groups.add(admin_group)
        
        self.stdout.write(
            self.style.SUCCESS(
                f'  Created superuser: {username} (password: admin123)'
            )
        )
        self.stdout.write(
            self.style.WARNING(
                '  IMPORTANT: Change the default password after first login!'
            )
        )
