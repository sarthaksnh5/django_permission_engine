"""
Performance tests
"""
import pytest
import time
from django.contrib.auth import get_user_model
from django.core.cache import cache

from django_permission_engine.models import Permission, UserPermission
from django_permission_engine.permissions import PermissionResolver

User = get_user_model()


@pytest.mark.django_db
class TestPerformance:
    """Performance tests"""

    def test_permission_check_performance(self):
        """Test permission check is fast"""
        # Create user with many permissions
        user = User.objects.create_user('testuser', 'test@example.com', 'password')
        permissions = [
            Permission.objects.create(
                key=f'test.permission{i}',
                module='test',
                capability=f'action{i}',
                label=f'Permission {i}',
            )
            for i in range(100)
        ]
        for perm in permissions:
            UserPermission.objects.create(user=user, permission=perm)

        resolver = PermissionResolver()

        # Clear cache
        cache.clear()

        # First check (loads from DB)
        start = time.time()
        result = resolver.check_permission(user, 'test.permission50')
        elapsed = time.time() - start

        assert result is True
        assert elapsed < 0.1  # Should be fast even on first load

        # Second check (from cache)
        start = time.time()
        result = resolver.check_permission(user, 'test.permission50')
        elapsed = time.time() - start

        assert result is True
        assert elapsed < 0.001  # Should be very fast from cache

    def test_bulk_permission_checks(self):
        """Test bulk permission checks performance"""
        user = User.objects.create_user('testuser', 'test@example.com', 'password')
        
        # Create permissions
        permissions = [
            Permission.objects.create(
                key=f'test.permission{i}',
                module='test',
                capability=f'action{i}',
                label=f'Permission {i}',
            )
            for i in range(50)
        ]
        
        # Assign all to user
        for perm in permissions:
            UserPermission.objects.create(user=user, permission=perm)

        resolver = PermissionResolver()
        cache.clear()

        # Check multiple permissions
        start = time.time()
        for i in range(50):
            resolver.check_permission(user, f'test.permission{i}')
        elapsed = time.time() - start

        # Should be fast even with many checks
        assert elapsed < 1.0  # Less than 1 second for 50 checks
