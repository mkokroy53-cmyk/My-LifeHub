import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = 'Automatically creates or updates a superuser from environment variables or arguments.'

    def add_arguments(self, parser):
        parser.add_argument('--username', type=str, help='Admin username')
        parser.add_argument('--email', type=str, help='Admin email')
        parser.add_argument('--password', type=str, help='Admin password')

    def handle(self, *args, **options):
        User = get_user_model()

        username = (
            options.get('username')
            or os.getenv('DJANGO_SUPERUSER_USERNAME')
            or 'mkokroy'
        )
        email = (
            options.get('email')
            or os.getenv('DJANGO_SUPERUSER_EMAIL')
            or 'mkokroy53@gmail.com'
        )
        password = (
            options.get('password')
            or os.getenv('DJANGO_SUPERUSER_PASSWORD')
            or 'mkokfrank'
        )

        if not username or not password:
            self.stdout.write(
                self.style.WARNING('Superuser auto-creation skipped: username or password missing.')
            )
            return

        user = User.objects.filter(username=username).first()
        if user:
            user.email = email
            user.is_staff = True
            user.is_superuser = True
            if not user.first_name:
                user.first_name = 'Frank'
            if not user.last_name:
                user.last_name = 'Mkok'
            user.set_password(password)
            user.save()
            self.stdout.write(
                self.style.SUCCESS(f'Superuser "{username}" updated successfully.')
            )
        else:
            User.objects.create_superuser(
                username=username,
                email=email,
                password=password,
                first_name='Frank',
                last_name='Mkok'
            )
            self.stdout.write(
                self.style.SUCCESS(f'Superuser "{username}" created successfully.')
            )
