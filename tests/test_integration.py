"""
Integration tests for UPR
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

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


@pytest.mark.django_db
class TestOptInIntegration:
    """Integration tests for opt-in permission model"""

    def test_viewset_action_not_in_registry_allowed(self):
        """Test that ViewSet actions not in registry are allowed via API"""
        from django.urls import path, include
        from rest_framework.routers import DefaultRouter
        from rest_framework import viewsets
        from rest_framework.decorators import action
        from rest_framework.response import Response
        
        # Define module with only some permissions
        @module('users')
        class UsersModule:
            crud = ['view', 'create']
            actions = ['reset_password']
            # Note: 'export_data' is NOT in the config
        
        registry.sync()
        
        # Create ViewSet with protected and unprotected actions
        class UserViewSet(viewsets.ViewSet):
            permission_classes = [PermissionRequired]
            module = 'users'
            
            def list(self, request):
                return Response({'data': 'list'})
            
            @action(detail=False, methods=['get'])
            def export_data(self, request):
                # This action is NOT in UPR config
                return Response({'data': 'exported'})
            
            @action(detail=True, methods=['post'])
            def reset_password(self, request, pk=None):
                # This action IS in UPR config
                return Response({'status': 'reset'})
        
        # Setup router
        router = DefaultRouter()
        router.register(r'users', UserViewSet, basename='user')
        
        # Create user with no permissions
        user = User.objects.create_user('testuser', 'test@example.com', 'password')
        client = APIClient()
        client.force_authenticate(user=user)
        
        # Test unprotected action (export_data) - should be allowed
        # Note: This would require actual URL setup, so we test the resolver directly
        from django_permission_engine.permissions import PermissionResolver
        resolver = PermissionResolver()
        
        class MockViewSet:
            module = 'users'
        
        # export_data is not in registry, so it should be allowed
        result = resolver.resolve(user, MockViewSet(), 'export_data', 'GET')
        assert result is True
        
        # reset_password is in registry, but user has no permission, so denied
        result = resolver.resolve(user, MockViewSet(), 'reset_password', 'POST')
        assert result is False

    def test_crud_action_not_in_crud_list_allowed(self):
        """Test that CRUD actions not in crud list are allowed"""
        # Define module with only view and create (no update, delete)
        @module('users')
        class UsersModule:
            crud = ['view', 'create']  # update and delete NOT in list
        
        registry.sync()
        
        user = User.objects.create_user('testuser', 'test@example.com', 'password')
        
        from django_permission_engine.permissions import PermissionResolver
        resolver = PermissionResolver()
        
        class MockViewSet:
            module = 'users'
        
        # update is not in crud list, so should be allowed
        result = resolver.resolve(user, MockViewSet(), 'update', 'PUT')
        assert result is True
        
        # delete is not in crud list, so should be allowed
        result = resolver.resolve(user, MockViewSet(), 'destroy', 'DELETE')
        assert result is True
        
        # view is in crud list, but user has no permission, so denied
        result = resolver.resolve(user, MockViewSet(), 'list', 'GET')
        assert result is False

    def test_mixed_protected_unprotected_actions(self):
        """Test ViewSet with mix of protected and unprotected actions"""
        # Define module with some permissions
        @module('orders')
        class OrdersModule:
            crud = ['view', 'create']
            actions = ['cancel', 'refund']
            # Note: 'export', 'print', 'delete' are NOT in config
        
        registry.sync()
        
        # Create user with some permissions
        user = User.objects.create_user('testuser', 'test@example.com', 'password')
        view_permission = Permission.objects.get(key='orders.view')
        UserPermission.objects.create(user=user, permission=view_permission)
        # User has 'orders.view' but NOT 'orders.cancel'
        
        from django_permission_engine.permissions import PermissionResolver
        resolver = PermissionResolver()
        
        class MockViewSet:
            module = 'orders'
        
        # Protected actions
        result = resolver.resolve(user, MockViewSet(), 'list', 'GET')
        assert result is True  # Has 'orders.view' permission
        
        result = resolver.resolve(user, MockViewSet(), 'cancel', 'POST')
        assert result is False  # No 'orders.cancel' permission
        
        # Unprotected actions (not in registry)
        result = resolver.resolve(user, MockViewSet(), 'export', 'GET')
        assert result is True  # Not in registry = allowed
        
        result = resolver.resolve(user, MockViewSet(), 'print', 'GET')
        assert result is True  # Not in registry = allowed
        
        result = resolver.resolve(user, MockViewSet(), 'destroy', 'DELETE')
        assert result is True  # delete not in crud list = allowed

    def test_gradual_permission_adoption(self):
        """Test gradual adoption of permissions (start with few, add more later)"""
        # Phase 1: Start with only critical permissions
        @module('users')
        class UsersModule:
            crud = ['delete']  # Only protect deletion
            actions = ['reset_password']  # Only protect password reset
        
        registry.sync()
        
        user = User.objects.create_user('testuser', 'test@example.com', 'password')
        
        from django_permission_engine.permissions import PermissionResolver
        resolver = PermissionResolver()
        
        class MockViewSet:
            module = 'users'
        
        # Protected actions (in registry, no permission)
        result = resolver.resolve(user, MockViewSet(), 'destroy', 'DELETE')
        assert result is False  # Denied (no permission)
        
        result = resolver.resolve(user, MockViewSet(), 'reset_password', 'POST')
        assert result is False  # Denied (no permission)
        
        # Unprotected actions (not in registry)
        result = resolver.resolve(user, MockViewSet(), 'list', 'GET')
        assert result is True  # Allowed (not in registry)
        
        result = resolver.resolve(user, MockViewSet(), 'create', 'POST')
        assert result is True  # Allowed (not in registry)
        
        result = resolver.resolve(user, MockViewSet(), 'update', 'PUT')
        assert result is True  # Allowed (not in registry)
        
        # Phase 2: Expand permissions (simulate by re-registering)
        # In real scenario, you would update the module definition
        registry.register_module(
            'users',
            crud=['view', 'create', 'update', 'delete'],
            actions=['reset_password', 'export_data']
        )
        registry.sync()
        
        # Now more actions require permissions
        result = resolver.resolve(user, MockViewSet(), 'list', 'GET')
        assert result is False  # Now requires permission (in registry)
        
        result = resolver.resolve(user, MockViewSet(), 'create', 'POST')
        assert result is False  # Now requires permission (in registry)
        
        # But export_data is now in registry, so requires permission
        result = resolver.resolve(user, MockViewSet(), 'export_data', 'GET')
        assert result is False  # Now requires permission (in registry)
