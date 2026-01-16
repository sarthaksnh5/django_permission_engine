# Phase 7: Management Commands

## Overview

This phase covers implementing Django management commands for syncing and validating permissions.

## Step 1: Create Sync Command

### django_permission_engine/management/commands/upr_sync.py

```python
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
```

## Step 2: Create Validate Command

### django_permission_engine/management/commands/upr_validate.py

```python
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
```

## Step 3: Create List Command

### django_permission_engine/management/commands/upr_list.py

```python
"""
Management command to list permissions
"""
from django.core.management.base import BaseCommand

from django_permission_engine import get_registry
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
        self.stdout.write(f'{'Key':<40} {'Module':<20} {'Capability':<20}')
        self.stdout.write('-' * 80)
        
        for perm in permissions:
            self.stdout.write(
                f'{perm.key:<40} {perm.module:<20} {perm.capability:<20}'
            )
        
        self.stdout.write('-' * 80)
        self.stdout.write(f'\nTotal: {permissions.count()} permissions')
    
    def _display_simple(self, permissions):
        """Display permissions in simple format"""
        for perm in permissions:
            self.stdout.write(perm.key)
    
    def _display_json(self, permissions):
        """Display permissions in JSON format"""
        import json
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
```

## Step 4: Write Command Tests

### tests/test_management_commands.py

```python
"""
Tests for management commands
"""
import pytest
from io import StringIO
from django.core.management import call_command
from django.core.management.base import CommandError

from django_permission_engine import get_registry
from django_permission_engine.models import Permission


@pytest.mark.django_db
class TestSyncCommand:
    """Test upr_sync command"""
    
    def test_sync_command(self):
        """Test sync command"""
        # Register module
        registry = get_registry()
        registry.register_module('users', crud=['view', 'create'])
        
        # Run sync
        out = StringIO()
        call_command('upr_sync', stdout=out)
        
        # Verify permissions created
        assert Permission.objects.count() == 2
        assert Permission.objects.filter(key='users.view').exists()
        assert Permission.objects.filter(key='users.create').exists()
    
    def test_sync_dry_run(self):
        """Test sync dry run"""
        registry = get_registry()
        registry.register_module('users', crud=['view'])
        
        out = StringIO()
        call_command('upr_sync', '--dry-run', stdout=out)
        
        # No permissions should be created
        assert Permission.objects.count() == 0
        
        # Output should contain plan
        output = out.getvalue()
        assert 'DRY RUN' in output
        assert 'Would create' in output
    
    def test_sync_with_orphans(self):
        """Test sync with orphaned permissions"""
        # Create orphaned permission
        Permission.objects.create(
            key='users.old_action',
            module='users',
            capability='old_action',
            label='Old Action',
        )
        
        registry = get_registry()
        registry.register_module('users', crud=['view'])
        
        out = StringIO()
        call_command('upr_sync', '--clean-orphans', stdout=out)
        
        # Orphaned permission should be deleted
        assert not Permission.objects.filter(key='users.old_action').exists()


@pytest.mark.django_db
class TestValidateCommand:
    """Test upr_validate command"""
    
    def test_validate_success(self):
        """Test validate with no errors"""
        registry = get_registry()
        registry.register_module('users', crud=['view'])
        registry.sync()
        
        out = StringIO()
        call_command('upr_validate', stdout=out)
        
        output = out.getvalue()
        assert 'All validations passed' in output
    
    def test_validate_orphaned(self):
        """Test validate with orphaned permissions"""
        # Create orphaned permission
        Permission.objects.create(
            key='users.old_action',
            module='users',
            capability='old_action',
            label='Old Action',
        )
        
        registry = get_registry()
        registry.register_module('users', crud=['view'])
        
        out = StringIO()
        call_command('upr_validate', stdout=out)
        
        output = out.getvalue()
        assert 'orphaned' in output.lower()


@pytest.mark.django_db
class TestListCommand:
    """Test upr_list command"""
    
    def test_list_command(self):
        """Test list command"""
        Permission.objects.create(
            key='users.view',
            module='users',
            capability='view',
            label='View Users',
        )
        
        out = StringIO()
        call_command('upr_list', stdout=out)
        
        output = out.getvalue()
        assert 'users.view' in output
        assert 'Total:' in output
    
    def test_list_filter_by_module(self):
        """Test list with module filter"""
        Permission.objects.create(
            key='users.view',
            module='users',
            capability='view',
            label='View Users',
        )
        Permission.objects.create(
            key='orders.view',
            module='orders',
            capability='view',
            label='View Orders',
        )
        
        out = StringIO()
        call_command('upr_list', '--module', 'users', stdout=out)
        
        output = out.getvalue()
        assert 'users.view' in output
        assert 'orders.view' not in output
```

## Step 5: Test Commands Manually

```bash
# Test sync command
python manage.py upr_sync

# Test sync with dry run
python manage.py upr_sync --dry-run

# Test validate command
python manage.py upr_validate

# Test list command
python manage.py upr_list

# Test list with filters
python manage.py upr_list --module users
python manage.py upr_list --type crud
```

## Checklist

- [ ] upr_sync command created
- [ ] upr_validate command created
- [ ] upr_list command created
- [ ] Command tests written
- [ ] Commands tested manually
- [ ] Error handling implemented
- [ ] Help text added

## Next Steps

Once management commands are complete, proceed to **[08-testing.md](08-testing.md)** to set up comprehensive testing.
