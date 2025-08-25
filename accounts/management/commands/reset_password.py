"""
Management command to reset user passwords
"""

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
import secrets
import string


class Command(BaseCommand):
    help = 'Reset a user password and generate a temporary password'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Username of the user to reset')
        parser.add_argument('--password', type=str, help='Set specific password (optional)')

    def handle(self, *args, **options):
        username = options['username']
        
        # Get user
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f'User "{username}" does not exist.')
        
        # Set password
        if options.get('password'):
            new_password = options['password']
            user.set_password(new_password)
            user.save()
            
            self.stdout.write(
                self.style.SUCCESS(f'Password for "{username}" has been set to the specified value.')
            )
        else:
            # Generate temporary password
            temp_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))
            user.set_password(temp_password)
            user.save()
            
            self.stdout.write(
                self.style.SUCCESS(f'Password for "{username}" has been reset.')
            )
            self.stdout.write(f'Temporary password: {temp_password}')
            self.stdout.write(
                self.style.WARNING(
                    'Please save this password and share it securely with the user. '
                    'They should change it on first login.'
                )
            )
