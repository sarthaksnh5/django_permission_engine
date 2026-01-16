# Phase 5: Runtime Permission Resolution

## Overview

This phase covers implementing runtime permission checking and DRF integration.

## Step 1: Create Permission Resolver

### django_permission_engine/permissions.py

```python
"""
Runtime permission resolution and DRF integration
"""
from typing import Optional, Set
from django.core.cache import cache
from django.contrib.auth import get_user_model
from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

from .models import Permission

User = get_user_model()


class PermissionResolver:
    """
    Resolves permissions at runtime.
    
    Determines if a user has permission to perform an action.
    """
    
    CRUD_ACTION_MAP = {
        'list': 'view',
        'retrieve': 'view',
        'create': 'create',
        'update': 'update',
        'partial_update': 'update',
        'destroy': 'delete',
    }
    
    def __init__(self, cache_timeout: int = 3600):
        self.cache_timeout = cache_timeout
    
    def resolve(
        self,
        user: User,
        viewset,
        action: str,
        http_method: str,
    ) -> bool:
        """
        Resolve if user has permission for action.
        
        Args:
            user: Authenticated user
            viewset: DRF ViewSet instance
            action: DRF action name
            http_method: HTTP method (GET, POST, etc.)
        
        Returns:
            True if user has permission, False otherwise
        """
        # Deny if not authenticated
        if not user or not user.is_authenticated:
            return False
        
        # Get module from viewset
        module = self.get_module(viewset)
        if not module:
            return False  # Deny if no module
        
        # Normalize action to capability
        capability = self.normalize_action(action, http_method)
        
        # Construct permission key
        permission_key = self.construct_permission_key(module, capability)
        
        # Check permission
        return self.check_permission(user, permission_key)
    
    def get_module(self, viewset) -> Optional[str]:
        """Extract module from viewset"""
        # Check for module attribute
        if hasattr(viewset, 'module'):
            return viewset.module
        
        # Check for get_module method
        if hasattr(viewset, 'get_module'):
            return viewset.get_module()
        
        return None
    
    def normalize_action(self, action: str, http_method: str) -> str:
        """
        Normalize DRF action to capability.
        
        Maps standard CRUD actions to capabilities,
        custom actions are used as-is.
        """
        # Check if standard CRUD action
        if action in self.CRUD_ACTION_MAP:
            return self.CRUD_ACTION_MAP[action]
        
        # Custom action - use as-is
        return action
    
    def construct_permission_key(self, module: str, capability: str) -> str:
        """Construct permission key from module and capability"""
        return f"{module}.{capability}"
    
    def check_permission(self, user: User, permission_key: str) -> bool:
        """
        Check if user has permission.
        
        Args:
            user: User to check
            permission_key: Permission key to check
        
        Returns:
            True if user has permission, False otherwise
        """
        # Validate permission key format
        if not self.is_valid_permission_key(permission_key):
            return False
        
        # Get user permissions (cached)
        user_permissions = self.get_user_permissions(user)
        
        # Check if permission exists
        return permission_key in user_permissions
    
    def is_valid_permission_key(self, key: str) -> bool:
        """Validate permission key format"""
        if not key or '.' not in key:
            return False
        
        # Check format: module.capability
        parts = key.split('.')
        if len(parts) < 2:
            return False
        
        # Check each part is valid identifier
        import re
        pattern = r'^[a-z0-9_]+$'
        for part in parts:
            if not re.match(pattern, part):
                return False
        
        return True
    
    def get_user_permissions(self, user: User) -> Set[str]:
        """
        Get all permission keys for user (cached).
        
        This method should be overridden by applications
        to provide their own permission assignment logic.
        """
        cache_key = f'user_permissions:{user.id}'
        permissions = cache.get(cache_key)
        
        if permissions is None:
            permissions = self._load_user_permissions(user)
            cache.set(cache_key, permissions, timeout=self.cache_timeout)
        
        return permissions
    
    def _load_user_permissions(self, user: User) -> Set[str]:
        """
        Load user permissions from database.
        
        This is a default implementation. Applications should
        override get_user_permissions() to provide their own logic.
        """
        # Default: Load from UserPermission model if it exists
        try:
            from django.apps import apps
            UserPermission = apps.get_model('django_permission_engine', 'UserPermission')
            return set(
                UserPermission.objects
                .filter(user=user)
                .values_list('permission__key', flat=True)
            )
        except (LookupError, AttributeError):
            # UserPermission model doesn't exist
            # Applications should provide their own implementation
            return set()


class PermissionRequired(BasePermission):
    """
    DRF permission class that uses UPR for permission checking.
    
    Usage:
        class UserViewSet(viewsets.ModelViewSet):
            permission_classes = [PermissionRequired]
            module = 'users'
    """
    
    resolver = PermissionResolver()
    
    def has_permission(self, request: Request, view: APIView) -> bool:
        """
        Check if user has permission for this view/action.
        """
        # Deny if not authenticated
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Get action
        action = self.get_action(view, request)
        
        # Resolve permission
        return self.resolver.resolve(
            user=request.user,
            viewset=view,
            action=action,
            http_method=request.method,
        )
    
    def get_action(self, view: APIView, request: Request) -> str:
        """
        Get DRF action name from view.
        """
        # Check if view has action attribute
        if hasattr(view, 'action'):
            return view.action
        
        # Infer from HTTP method and URL
        method = request.method
        has_pk = 'pk' in view.kwargs
        
        if method == 'GET':
            return 'retrieve' if has_pk else 'list'
        elif method == 'POST':
            return 'create'
        elif method in ['PUT', 'PATCH']:
            return 'update'
        elif method == 'DELETE':
            return 'destroy'
        
        return 'list'
    
    def has_object_permission(
        self,
        request: Request,
        view: APIView,
        obj,
    ) -> bool:
        """
        Optional: Override for object-level permissions.
        
        By default, delegates to has_permission.
        """
        return self.has_permission(request, view)
```

## Step 2: Create User Permission Model (Optional)

### django_permission_engine/models.py (add)

```python
# Add to existing models.py

class UserPermission(models.Model):
    """
    Model for assigning permissions to users.
    
    This is optional - applications can use their own assignment models.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='user_permissions',
    )
    permission = models.ForeignKey(
        Permission,
        on_delete=models.CASCADE,
        related_name='user_assignments',
    )
    granted_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='granted_permissions',
    )
    granted_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'upr_user_permissions'
        unique_together = ['user', 'permission']
        verbose_name = 'User Permission'
        verbose_name_plural = 'User Permissions'
    
    def __str__(self):
        return f"{self.user.username} - {self.permission.key}"
```

### Create Migration

```bash
python manage.py makemigrations django_permission_engine
```

## Step 3: Update Permission Resolver to Use UserPermission

### django_permission_engine/permissions.py (update)

```python
class PermissionResolver:
    # ... existing code ...
    
    def _load_user_permissions(self, user: User) -> Set[str]:
        """Load user permissions from UserPermission model"""
        try:
            from .models import UserPermission
            return set(
                UserPermission.objects
                .filter(user=user, permission__is_active=True)
                .values_list('permission__key', flat=True)
            )
        except ImportError:
            return set()
```

## Step 4: Write Runtime Resolution Tests

### tests/test_permissions.py

```python
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
```

## Step 5: Create Example ViewSet

### examples/viewset_example.py

```python
"""
Example: Using PermissionRequired in ViewSet
"""
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from django_permission_engine.permissions import PermissionRequired


class UserViewSet(viewsets.ModelViewSet):
    """
    Example ViewSet using UPR permissions.
    
    Permissions required:
    - users.view (for list, retrieve)
    - users.create (for create)
    - users.update (for update, partial_update)
    - users.delete (for destroy)
    - users.reset_password (for reset_password action)
    """
    permission_classes = [PermissionRequired]
    module = 'users'  # Required: Declare module
    queryset = User.objects.all()
    serializer_class = UserSerializer
    
    @action(detail=True, methods=['post'])
    def reset_password(self, request, pk=None):
        """
        Reset user password.
        
        Requires 'users.reset_password' permission.
        """
        user = self.get_object()
        # ... reset password logic ...
        return Response({'status': 'password reset'})


class OrderViewSet(viewsets.ModelViewSet):
    """Order ViewSet with custom actions"""
    permission_classes = [PermissionRequired]
    module = 'orders'
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel order - requires 'orders.cancel' permission"""
        order = self.get_object()
        # ... cancel logic ...
        return Response({'status': 'cancelled'})
    
    @action(detail=True, methods=['post'])
    def refund(self, request, pk=None):
        """Refund order - requires 'orders.refund' permission"""
        order = self.get_object()
        # ... refund logic ...
        return Response({'status': 'refunded'})
```

## Step 6: Add Cache Invalidation

### django_permission_engine/models.py (add signal)

```python
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache


@receiver([post_save, post_delete], sender=UserPermission)
def invalidate_user_permission_cache(sender, instance, **kwargs):
    """Invalidate user permission cache when permissions change"""
    cache_key = f'user_permissions:{instance.user.id}'
    cache.delete(cache_key)
```

## Checklist

- [ ] PermissionResolver class created
- [ ] PermissionRequired DRF class created
- [ ] UserPermission model created (optional)
- [ ] Runtime resolution tests written
- [ ] Example ViewSet created
- [ ] Cache invalidation implemented
- [ ] Integration tests passing

## Next Steps

Once runtime resolution is complete, proceed to **[06-catalog-api.md](06-catalog-api.md)** to implement the permission catalog API.
