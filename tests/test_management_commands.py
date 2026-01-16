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

    def test_sync_verbose(self):
        """Test sync with verbose output"""
        registry = get_registry()
        registry.register_module('users', crud=['view'])

        out = StringIO()
        call_command('upr_sync', '--verbose', stdout=out)

        output = out.getvalue()
        assert 'Validating permissions' in output
        assert 'Syncing permissions' in output


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

    def test_validate_missing(self):
        """Test validate with missing permissions"""
        registry = get_registry()
        registry.register_module('users', crud=['view'])
        # Don't sync - permissions in code but not in DB

        out = StringIO()
        try:
            call_command('upr_validate', stdout=out)
        except CommandError:
            pass  # Expected to fail

        output = out.getvalue()
        assert 'permissions in code but not in database' in output.lower()


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

    def test_list_filter_by_type(self):
        """Test list with type filter"""
        Permission.objects.create(
            key='users.view',
            module='users',
            capability='view',
            label='View Users',
        )
        Permission.objects.create(
            key='users.reset_password',
            module='users',
            capability='reset_password',
            label='Reset Password',
        )

        out = StringIO()
        call_command('upr_list', '--type', 'crud', stdout=out)

        output = out.getvalue()
        assert 'users.view' in output
        assert 'users.reset_password' not in output

    def test_list_json_format(self):
        """Test list with JSON format"""
        Permission.objects.create(
            key='users.view',
            module='users',
            capability='view',
            label='View Users',
        )

        out = StringIO()
        call_command('upr_list', '--format', 'json', stdout=out)

        output = out.getvalue()
        import json
        data = json.loads(output)
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]['key'] == 'users.view'

    def test_list_simple_format(self):
        """Test list with simple format"""
        Permission.objects.create(
            key='users.view',
            module='users',
            capability='view',
            label='View Users',
        )

        out = StringIO()
        call_command('upr_list', '--format', 'simple', stdout=out)

        output = out.getvalue()
        assert output.strip() == 'users.view'
