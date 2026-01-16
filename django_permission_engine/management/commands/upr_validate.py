"""
Management command to validate permissions
"""
from django.core.management.base import BaseCommand, CommandError

from django_permission_engine import get_registry
from django_permission_engine.models import Permission


class Command(BaseCommand):
    help = 'Validate permission definitions and database consistency'

    def add_arguments(self, parser):
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed output',
        )

    def handle(self, *args, **options):
        """Execute validate command"""
        verbose = options['verbose']

        # Get registry
        registry = get_registry()

        self.stdout.write('Validating permissions...')

        errors = []
        warnings = []

        # Validate registry
        registry_errors = registry.validate()
        if registry_errors:
            errors.extend(registry_errors)

        # Validate database consistency
        db_errors, db_warnings = self._validate_database(registry)
        errors.extend(db_errors)
        warnings.extend(db_warnings)

        # Display results
        if errors:
            self.stdout.write(self.style.ERROR(f'\nErrors: {len(errors)}'))
            for error in errors:
                self.stdout.write(self.style.ERROR(f'  ✗ {error}'))

        if warnings:
            self.stdout.write(self.style.WARNING(f'\nWarnings: {len(warnings)}'))
            for warning in warnings:
                self.stdout.write(self.style.WARNING(f'  ⚠ {warning}'))

        if not errors and not warnings:
            self.stdout.write(self.style.SUCCESS('\n✓ All validations passed'))
            return

        if errors:
            raise CommandError(f'Validation failed with {len(errors)} error(s)')

    def _validate_database(self, registry):
        """Validate database consistency"""
        errors = []
        warnings = []

        # Get all permission keys
        defined_keys = registry.get_all_permission_keys()
        db_keys = set(Permission.objects.values_list('key', flat=True))

        # Check for orphaned permissions
        orphaned = db_keys - defined_keys
        if orphaned:
            warnings.append(f'Found {len(orphaned)} orphaned permissions in database')
            for key in orphaned:
                warnings.append(f'  - {key}')

        # Check for missing permissions
        missing = defined_keys - db_keys
        if missing:
            errors.append(f'Found {len(missing)} permissions in code but not in database')
            for key in missing:
                errors.append(f'  - {key}')

        # Check for invalid permission keys
        for perm in Permission.objects.all():
            if '.' not in perm.key:
                errors.append(f'Invalid permission key format: {perm.key}')

        return errors, warnings
