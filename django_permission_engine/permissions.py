"""
Runtime permission resolution and DRF integration
"""
from __future__ import annotations

from typing import Optional, Set, TYPE_CHECKING
from django.core.cache import cache

if TYPE_CHECKING:
    from rest_framework.permissions import BasePermission
    from rest_framework.request import Request
    from rest_framework.views import APIView


def _get_base_permission_class():
    """Lazy import of BasePermission to avoid AppRegistryNotReady"""
    try:
        from rest_framework.permissions import BasePermission
        return BasePermission
    except Exception:
        # Fallback base class if DRF not available or apps not ready
        return object


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
        user,
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
            return True  # Allow if no module (skip permission checking)

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

    def check_permission(self, user, permission_key: str) -> bool:
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

    def get_user_permissions(self, user) -> Set[str]:
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

    def _load_user_permissions(self, user) -> Set[str]:
        """
        Load user permissions from database.

        Uses UserPermission model if available.
        """
        try:
            from .models import UserPermission
            return set(
                UserPermission.objects
                .filter(user=user, permission__is_active=True)
                .values_list('permission__key', flat=True)
            )
        except Exception:
            # UserPermission model might not exist or error occurred
            # Applications should provide their own implementation
            return set()


class PermissionRequired(_get_base_permission_class()):
    """
    DRF permission class that uses UPR for permission checking.

    Usage:
        class UserViewSet(viewsets.ModelViewSet):
            permission_classes = [PermissionRequired]
            module = 'users'
    """

    resolver = PermissionResolver()

    def has_permission(self, request, view) -> bool:
        """
        Check if user has permission for this view/action.
        
        If no module is assigned to the viewset, permission checking is skipped (allows access).
        """
        # Deny if not authenticated
        if not request.user or not request.user.is_authenticated:
            return False

        # Check if module is assigned
        module = self.resolver.get_module(view)
        if not module:
            # No module assigned - skip permission checking (allow access)
            return True

        # Get action
        action = self.get_action(view, request)

        # Resolve permission
        return self.resolver.resolve(
            user=request.user,
            viewset=view,
            action=action,
            http_method=request.method,
        )

    def get_action(self, view, request) -> str:
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
        request,
        view,
        obj,
    ) -> bool:
        """
        Optional: Override for object-level permissions.

        By default, delegates to has_permission.
        """
        return self.has_permission(request, view)
