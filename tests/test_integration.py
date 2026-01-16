"""
Integration tests for UPR
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from django_permission_engine import registry, module, action
from django_permission_engine.models import Permission, UserPermission
from django_permission_engine.permissions import PermissionRequired

User = get_user_model()


@pytest.mark.django_db
class TestIntegration:
    """Integration tests"""

    def test_full_workflow(self):
        """Test complete workflow: define -> sync -> assign -> check"""
        # 1. Define permissions
        @module('users')
        class UsersModule:
            crud = ['view', 'create']
            actions = ['reset_password']

        # 2. Sync to database
        result = registry.sync()
        assert len(result['created']) == 3

        # 3. Create user and assign permission
        user = User.objects.create_user('testuser', 'test@example.com', 'password')
        permission = Permission.objects.get(key='users.view')
        UserPermission.objects.create(user=user, permission=permission)

        # 4. Check permission
        from django_permission_engine.permissions import PermissionResolver
        resolver = PermissionResolver()

        class MockViewSet:
            module = 'users'

        has_permission = resolver.resolve(user, MockViewSet(), 'list', 'GET')
        assert has_permission is True

    def test_drf_integration(self):
        """Test DRF integration"""
        # Setup
        @module('users')
        class UsersModule:
            crud = ['view']

        registry.sync()

        user = User.objects.create_user('testuser', 'test@example.com', 'password')
        permission = Permission.objects.get(key='users.view')
        UserPermission.objects.create(user=user, permission=permission)

        # Test DRF permission class
        from django_permission_engine.permissions import PermissionRequired

        class MockViewSet:
            module = 'users'
            action = 'list'

        class MockRequest:
            user = user
            method = 'GET'

        perm_class = PermissionRequired()
        result = perm_class.has_permission(MockRequest(), MockViewSet())
        assert result is True

    def test_catalog_api_integration(self):
        """Test catalog API integration"""
        # Setup permissions
        @module('users')
        class UsersModule:
            crud = ['view', 'create']

        registry.sync()

        # Test API
        user = User.objects.create_user('testuser', 'test@example.com', 'password')
        client = APIClient()
        client.force_authenticate(user=user)

        response = client.get('/api/permissions/catalog/')
        assert response.status_code == 200
        data = response.json()
        assert 'modules' in data
        assert len(data['modules']) > 0

    def test_management_commands_integration(self):
        """Test management commands integration"""
        from io import StringIO
        from django.core.management import call_command

        # Define permissions
        @module('users')
        class UsersModule:
            crud = ['view', 'create']

        # Test sync command
        out = StringIO()
        call_command('upr_sync', stdout=out)
        assert Permission.objects.count() == 2

        # Test validate command
        out = StringIO()
        call_command('upr_validate', stdout=out)
        output = out.getvalue()
        assert 'All validations passed' in output

        # Test list command
        out = StringIO()
        call_command('upr_list', stdout=out)
        output = out.getvalue()
        assert 'users.view' in output
