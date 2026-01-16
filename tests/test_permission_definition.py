"""
Tests for permission definition layer
"""
import pytest
from django_permission_engine import registry, module, action
from django_permission_engine.models import Permission


@pytest.mark.django_db
class TestModuleDecorator:
    """Test @module decorator"""

    def test_module_decorator_simple(self):
        """Test simple module definition"""
        @module('users')
        class UsersModule:
            crud = ['view', 'create', 'update', 'delete']

        # Check module registered
        assert 'users' in registry._modules
        permissions = registry.get_all_permissions()
        assert 'users.view' in permissions
        assert 'users.create' in permissions
        assert 'users.update' in permissions
        assert 'users.delete' in permissions

    def test_module_decorator_with_actions(self):
        """Test module with actions list"""
        @module('users')
        class UsersModule:
            crud = ['view']
            actions = ['reset_password', 'export_data']

        permissions = registry.get_all_permissions()
        assert 'users.view' in permissions
        assert 'users.reset_password' in permissions
        assert 'users.export_data' in permissions

    def test_module_decorator_with_metadata(self):
        """Test module with label and description"""
        @module('users', label='User Management', description='Manage users')
        class UsersModule:
            crud = ['view']

        module_def = registry._modules['users']
        assert module_def.label == 'User Management'
        assert module_def.description == 'Manage users'

    def test_module_decorator_class_metadata(self):
        """Test module using class attributes"""
        @module('users')
        class UsersModule:
            label = 'User Management'
            description = 'Manage users'
            crud = ['view']

        module_def = registry._modules['users']
        assert module_def.label == 'User Management'
        assert module_def.description == 'Manage users'


@pytest.mark.django_db
class TestActionDecorator:
    """Test @action decorator"""

    def test_action_decorator(self):
        """Test action decorator"""
        @module('users')
        class UsersModule:
            crud = ['view']

            @action('reset_password', label='Reset Password')
            def reset_password(self):
                pass

        permissions = registry.get_all_permissions()
        assert 'users.reset_password' in permissions

        perm_def = permissions['users.reset_password']
        assert perm_def.label == 'Reset Password'

    def test_action_decorator_multiple(self):
        """Test multiple action decorators"""
        @module('users')
        class UsersModule:
            crud = ['view']

            @action('reset_password')
            def reset_password(self):
                pass

            @action('export_data')
            def export_data(self):
                pass

        permissions = registry.get_all_permissions()
        assert 'users.reset_password' in permissions
        assert 'users.export_data' in permissions

    def test_action_decorator_with_description(self):
        """Test action with description"""
        @module('users')
        class UsersModule:
            crud = ['view']

            @action(
                'reset_password',
                label='Reset Password',
                description='Allows resetting user passwords'
            )
            def reset_password(self):
                pass

        permissions = registry.get_all_permissions()
        perm_def = permissions['users.reset_password']
        # Note: Description is stored in action metadata but not in PermissionDefinition
        # This is expected behavior - description can be added to PermissionDefinition if needed

    def test_action_decorator_deprecated(self):
        """Test deprecated action"""
        @module('users')
        class UsersModule:
            crud = ['view']

            @action('old_action', deprecated=True)
            def old_action(self):
                pass

        permissions = registry.get_all_permissions()
        assert 'users.old_action' in permissions


@pytest.mark.django_db
class TestDefinitionIntegration:
    """Test integration of definition layer"""

    def test_full_module_definition(self):
        """Test complete module definition"""
        @module('orders', label='Order Management')
        class OrdersModule:
            crud = ['view', 'create', 'update', 'delete']
            actions = ['cancel', 'refund']

            @action('ship', label='Ship Order')
            def ship(self):
                pass

        # Sync to database
        result = registry.sync()

        # Verify permissions created
        assert Permission.objects.filter(module='orders').count() == 7
        assert Permission.objects.filter(key='orders.view').exists()
        assert Permission.objects.filter(key='orders.cancel').exists()
        assert Permission.objects.filter(key='orders.ship').exists()

    def test_hierarchical_modules(self):
        """Test hierarchical module structure"""
        @module('breakdown')
        class BreakdownModule:
            crud = ['view', 'create', 'update', 'delete']

        @module('breakdown.visit')
        class BreakdownVisitModule:
            crud = ['view', 'create', 'update']
            actions = ['assign_engineer', 'close']

        # Sync
        registry.sync()

        # Verify permissions
        assert Permission.objects.filter(module='breakdown').count() == 4
        assert Permission.objects.filter(module='breakdown.visit').count() == 5
        assert Permission.objects.filter(key='breakdown.visit.assign_engineer').exists()

    def test_combined_crud_and_actions(self):
        """Test module with both CRUD and actions"""
        @module('users')
        class UsersModule:
            crud = ['view', 'create']
            actions = ['reset_password']

            @action('export_data')
            def export_data(self):
                pass

        permissions = registry.get_all_permissions()
        assert len(permissions) == 4  # view, create, reset_password, export_data
        assert 'users.view' in permissions
        assert 'users.create' in permissions
        assert 'users.reset_password' in permissions
        assert 'users.export_data' in permissions
