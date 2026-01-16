"""
Management command to sync permissions with database
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from django_permission_engine import get_registry


class Command(BaseCommand):
    help = 'Synchronize permission definitions with database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would change without making changes',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force sync even with warnings',
        )
        parser.add_argument(
            '--clean-orphans',
            action='store_true',
            help='Delete orphaned permissions',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed output',
        )

    def handle(self, *args, **options):
        """Execute sync command"""
        dry_run = options['dry_run']
        force = options['force']
        clean_orphans = options['clean_orphans']
        verbose = options['verbose']

        # Get registry
        registry = get_registry()

        # Set orphan action
        if clean_orphans:
            registry.orphan_action = 'delete'
        elif not force:
            registry.orphan_action = 'warn'

        try:
            # Validate first
            if verbose:
                self.stdout.write('Validating permissions...')

            errors = registry.validate()
            if errors:
                self.stdout.write(
                    self.style.ERROR(f'Validation errors found: {len(errors)}')
                )
                for error in errors:
                    self.stdout.write(self.style.ERROR(f'  - {error}'))

                if not force:
                    raise CommandError('Validation failed. Use --force to continue.')

            # Sync
            if dry_run:
                self.stdout.write(self.style.WARNING('DRY RUN - No changes will be made'))
                plan = registry.sync(dry_run=True)
                self._display_plan(plan, verbose)
            else:
                self.stdout.write('Syncing permissions...')
                result = registry.sync()
                self._display_result(result, verbose)
                self.stdout.write(
                    self.style.SUCCESS('Sync complete.')
                )

        except Exception as e:
            raise CommandError(f'Sync failed: {e}')

    def _display_plan(self, plan, verbose):
        """Display sync plan"""
        self.stdout.write('\nSync Plan:')

        if plan['create']:
            self.stdout.write(
                self.style.SUCCESS(f'  Would create: {len(plan["create"])} permissions')
            )
            if verbose:
                for perm in plan['create']:
                    self.stdout.write(f'    - {perm.key}')

        if plan['update']:
            self.stdout.write(
                self.style.WARNING(f'  Would update: {len(plan["update"])} permissions')
            )
            if verbose:
                for perm in plan['update']:
                    self.stdout.write(f'    - {perm.key}')

        if plan['orphaned']:
            self.stdout.write(
                self.style.ERROR(f'  Orphaned: {len(plan["orphaned"])} permissions')
            )
            if verbose:
                for perm in plan['orphaned']:
                    self.stdout.write(f'    - {perm.key}')

        unchanged = len(get_registry().get_all_permissions()) - len(plan['create']) - len(plan['update'])
        if unchanged > 0:
            self.stdout.write(f'  Unchanged: {unchanged} permissions')

    def _display_result(self, result, verbose):
        """Display sync result"""
        if result['created']:
            self.stdout.write(
                self.style.SUCCESS(f'  Created: {len(result["created"])} permissions')
            )
            if verbose:
                for key in result['created']:
                    self.stdout.write(f'    - {key}')

        if result['updated']:
            self.stdout.write(
                self.style.WARNING(f'  Updated: {len(result["updated"])} permissions')
            )
            if verbose:
                for key in result['updated']:
                    self.stdout.write(f'    - {key}')

        if result['orphaned']:
            self.stdout.write(
                self.style.ERROR(f'  Orphaned: {len(result["orphaned"])} permissions')
            )
            if verbose:
                for key in result['orphaned']:
                    self.stdout.write(f'    - {key}')

        total = len(get_registry().get_all_permissions())
        unchanged = total - len(result['created']) - len(result['updated'])
        if unchanged > 0:
            self.stdout.write(f'  Unchanged: {unchanged} permissions')
