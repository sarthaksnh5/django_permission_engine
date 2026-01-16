"""
Management command to list permissions
"""
from django.core.management.base import BaseCommand
import json

from django_permission_engine.models import Permission


class Command(BaseCommand):
    help = 'List all registered permissions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--module',
            type=str,
            help='Filter by module',
        )
        parser.add_argument(
            '--type',
            type=str,
            choices=['crud', 'action'],
            help='Filter by type',
        )
        parser.add_argument(
            '--format',
            type=str,
            choices=['table', 'json', 'simple'],
            default='table',
            help='Output format',
        )

    def handle(self, *args, **options):
        """Execute list command"""
        module_filter = options.get('module')
        type_filter = options.get('type')
        format_type = options['format']

        # Get permissions
        if module_filter:
            permissions = Permission.objects.filter(module=module_filter)
        else:
            permissions = Permission.objects.all()

        if type_filter:
            if type_filter == 'crud':
                permissions = permissions.filter(capability__in=['view', 'create', 'update', 'delete'])
            else:
                permissions = permissions.exclude(capability__in=['view', 'create', 'update', 'delete'])

        permissions = permissions.order_by('module', 'capability')

        # Display
        if format_type == 'json':
            self._display_json(permissions)
        elif format_type == 'simple':
            self._display_simple(permissions)
        else:
            self._display_table(permissions)

    def _display_table(self, permissions):
        """Display permissions in table format"""
        self.stdout.write('\nRegistered Permissions:\n')
        self.stdout.write('-' * 80)
        self.stdout.write('{:<40} {:<20} {:<20}'.format('Key', 'Module', 'Capability'))
        self.stdout.write('-' * 80)

        for perm in permissions:
            self.stdout.write(
                '{:<40} {:<20} {:<20}'.format(perm.key, perm.module, perm.capability)
            )

        self.stdout.write('-' * 80)
        self.stdout.write(f'\nTotal: {permissions.count()} permissions')

    def _display_simple(self, permissions):
        """Display permissions in simple format"""
        for perm in permissions:
            self.stdout.write(perm.key)

    def _display_json(self, permissions):
        """Display permissions in JSON format"""
        data = [
            {
                'key': perm.key,
                'module': perm.module,
                'capability': perm.capability,
                'label': perm.label,
            }
            for perm in permissions
        ]
        self.stdout.write(json.dumps(data, indent=2))
