"""
Tests for runtime permission resolution
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import viewsets

from django_permission_engine.permissions import (
    PermissionResolver,
    PermissionRequired,
)
from django_permission_engine.models import Permission, UserPermission

User = get_user_model()


@pytest.mark.django_db
class TestPermissionResolver:
    """Test PermissionResolver"""

    def test_resolve_view_permission(self):
        """Test resolving view permission"""
        # Create permission
        permission = Permission.objects.create(
            key='users.view',
            module='users',
            capability='view',
            label='View Users',
        )

        # Create user with permission
        user = User.objects.create_user('testuser', 'test@example.com', 'password')
        UserPermission.objects.create(user=user, permission=permission)

        # Create mock viewset
        class MockViewSet:
            module = 'users'

        viewset = MockViewSet()
        resolver = PermissionResolver()

        # Test
        result = resolver.resolve(user, viewset, 'list', 'GET')
        assert result is True

    def test_resolve_create_permission(self):
        """Test resolving create permission"""
        permission = Permission.objects.create(
            key='users.create',
            module='users',
            capability='create',
            label='Create Users',
        )

        user = User.objects.create_user('testuser', 'test@example.com', 'password')
        UserPermission.objects.create(user=user, permission=permission)

        class MockViewSet:
            module = 'users'

        resolver = PermissionResolver()
        result = resolver.resolve(user, MockViewSet(), 'create', 'POST')
        assert result is True

    def test_resolve_custom_action(self):
        """Test resolving custom action permission"""
        permission = Permission.objects.create(
            key='users.reset_password',
            module='users',
            capability='reset_password',
            label='Reset Password',
        )

        user = User.objects.create_user('testuser', 'test@example.com', 'password')
        UserPermission.objects.create(user=user, permission=permission)

        class MockViewSet:
            module = 'users'

        resolver = PermissionResolver()
        result = resolver.resolve(user, MockViewSet(), 'reset_password', 'POST')
        assert result is True

    def test_resolve_no_permission(self):
        """Test resolving when user doesn't have permission"""
        user = User.objects.create_user('testuser', 'test@example.com', 'password')
        # No permissions assigned

        class MockViewSet:
            module = 'users'

        resolver = PermissionResolver()
        result = resolver.resolve(user, MockViewSet(), 'list', 'GET')
        assert result is False

    def test_resolve_no_module(self):
        """Test resolving when viewset has no module"""
        user = User.objects.create_user('testuser', 'test@example.com', 'password')

        class MockViewSet:
            pass  # No module

        resolver = PermissionResolver()
        result = resolver.resolve(user, MockViewSet(), 'list', 'GET')
        assert result is False

    def test_normalize_action(self):
        """Test action normalization"""
        resolver = PermissionResolver()

        assert resolver.normalize_action('list', 'GET') == 'view'
        assert resolver.normalize_action('retrieve', 'GET') == 'view'
        assert resolver.normalize_action('create', 'POST') == 'create'
        assert resolver.normalize_action('update', 'PUT') == 'update'
        assert resolver.normalize_action('partial_update', 'PATCH') == 'update'
        assert resolver.normalize_action('destroy', 'DELETE') == 'delete'
        assert resolver.normalize_action('reset_password', 'POST') == 'reset_password'

    def test_construct_permission_key(self):
        """Test permission key construction"""
        resolver = PermissionResolver()

        key = resolver.construct_permission_key('users', 'view')
        assert key == 'users.view'

        key = resolver.construct_permission_key('users', 'reset_password')
        assert key == 'users.reset_password'

    def test_is_valid_permission_key(self):
        """Test permission key validation"""
        resolver = PermissionResolver()

        # Valid keys
        assert resolver.is_valid_permission_key('users.view') is True
        assert resolver.is_valid_permission_key('users.reset_password') is True
        assert resolver.is_valid_permission_key('breakdown.visit.assign_engineer') is True

        # Invalid keys
        assert resolver.is_valid_permission_key('users') is False  # No dot
        assert resolver.is_valid_permission_key('Users.View') is False  # Uppercase
        assert resolver.is_valid_permission_key('users.view!') is False  # Special char
        assert resolver.is_valid_permission_key('') is False  # Empty


@pytest.mark.django_db
class TestPermissionRequired:
    """Test PermissionRequired DRF permission class"""

    def test_has_permission_authenticated(self):
        """Test permission check for authenticated user"""
        permission = Permission.objects.create(
            key='users.view',
            module='users',
            capability='view',
            label='View Users',
        )

        user = User.objects.create_user('testuser', 'test@example.com', 'password')
        UserPermission.objects.create(user=user, permission=permission)

        class MockViewSet:
            module = 'users'
            action = 'list'

        class MockRequest:
            user = user
            method = 'GET'

        perm_class = PermissionRequired()
        result = perm_class.has_permission(MockRequest(), MockViewSet())
        assert result is True

    def test_has_permission_unauthenticated(self):
        """Test permission check for unauthenticated user"""
        class MockViewSet:
            module = 'users'

        class MockRequest:
            user = None
            method = 'GET'

        perm_class = PermissionRequired()
        result = perm_class.has_permission(MockRequest(), MockViewSet())
        assert result is False

    def test_get_action_from_view(self):
        """Test getting action from view"""
        class MockViewSet:
            action = 'reset_password'

        class MockRequest:
            method = 'POST'

        perm_class = PermissionRequired()
        action = perm_class.get_action(MockViewSet(), MockRequest())
        assert action == 'reset_password'

    def test_get_action_inferred(self):
        """Test inferring action from HTTP method"""
        class MockViewSet:
            pass

        class MockRequest:
            method = 'GET'

        perm_class = PermissionRequired()
        action = perm_class.get_action(MockViewSet(), MockRequest())
        assert action == 'list'

    def test_has_object_permission(self):
        """Test object-level permission (delegates to has_permission)"""
        permission = Permission.objects.create(
            key='users.view',
            module='users',
            capability='view',
            label='View Users',
        )

        user = User.objects.create_user('testuser', 'test@example.com', 'password')
        UserPermission.objects.create(user=user, permission=permission)

        class MockViewSet:
            module = 'users'
            action = 'list'

        class MockRequest:
            user = user
            method = 'GET'

        perm_class = PermissionRequired()
        result = perm_class.has_object_permission(MockRequest(), MockViewSet(), None)
        assert result is True
