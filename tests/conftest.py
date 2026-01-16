"""
Pytest configuration and fixtures
"""
import pytest
from django.contrib.auth import get_user_model
from django_permission_engine.models import Permission, UserPermission

User = get_user_model()


@pytest.fixture
def user():
    """Create a test user"""
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123'
    )


@pytest.fixture
def admin_user():
    """Create an admin user"""
    return User.objects.create_superuser(
        username='admin',
        email='admin@example.com',
        password='adminpass123'
    )


@pytest.fixture
def permission():
    """Create a test permission"""
    return Permission.objects.create(
        key='users.view',
        module='users',
        capability='view',
        label='View Users',
    )


@pytest.fixture
def user_with_permission(user, permission):
    """Create user with permission"""
    UserPermission.objects.create(user=user, permission=permission)
    return user


@pytest.fixture
def registry():
    """Get registry instance"""
    from django_permission_engine import get_registry
    # Clear registry for clean tests
    from django_permission_engine.registry import _default_registry
    import django_permission_engine.registry
    django_permission_engine.registry._default_registry = None
    return get_registry()
