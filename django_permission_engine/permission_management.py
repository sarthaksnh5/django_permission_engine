"""
Permission Management API for assigning/revoking user permissions
"""
from typing import TYPE_CHECKING
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

if TYPE_CHECKING:
    from rest_framework.permissions import BasePermission
    from rest_framework.request import Request


def _get_base_permission_class():
    """Lazy import to avoid AppRegistryNotReady"""
    try:
        from rest_framework.permissions import BasePermission
        return BasePermission
    except Exception:
        return object


class ConfigurablePermissionManagementPermission(_get_base_permission_class()):
    """
    Configurable permission class for permission management API.
    
    Checks UPR_CONFIG['can_manage_permissions'] function if provided,
    otherwise defaults to superuser check.
    """
    
    def has_permission(self, request, view) -> bool:
        """
        Check if user can manage permissions.
        
        Priority:
        1. If UPR_CONFIG['can_manage_permissions'] function is provided, use it
        2. Otherwise, check if user is superuser
        """
        from django.conf import settings
        
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Get config
        upr_config = getattr(settings, "UPR_CONFIG", {})
        can_manage_permissions_func = upr_config.get("can_manage_permissions", None)
        
        # If custom function is provided, use it
        if can_manage_permissions_func:
            try:
                # Call the function with request
                if callable(can_manage_permissions_func):
                    return bool(can_manage_permissions_func(request))
                else:
                    # If it's a string path, import and call it
                    from django.utils.module_loading import import_string
                    func = import_string(can_manage_permissions_func)
                    return bool(func(request))
            except Exception:
                # If function fails, fall back to superuser check
                return request.user.is_superuser
        
        # Default: superuser only
        return request.user.is_superuser


class UserPermissionManagementViewSet(viewsets.ViewSet):
    """
    API for managing user permissions.
    
    Access control is configurable via UPR_CONFIG['can_manage_permissions'].
    Defaults to superuser only if not configured.
    
    Endpoints:
    - GET /api/permissions/users/{user_id}/ - Get all permissions for a user
    - POST /api/permissions/users/{user_id}/assign/ - Assign permission to user
    - POST /api/permissions/users/{user_id}/revoke/ - Revoke permission from user
    - POST /api/permissions/bulk-assign/ - Bulk assign permissions
    - POST /api/permissions/bulk-revoke/ - Bulk revoke permissions
    """
    permission_classes = [ConfigurablePermissionManagementPermission]

    @action(detail=False, methods=['get'], url_path='users/(?P<user_id>[^/.]+)')
    def user_permissions(self, request, user_id=None, *args, **kwargs):
        """
        Get all permissions for a specific user.
        
        GET /api/permissions/users/{user_id}/
        Supports both integer IDs and UUIDs.
        """
        from django.contrib.auth import get_user_model
        from .models import Permission, UserPermission
        
        User = get_user_model()
        
        try:
            # Try to get user by primary key (supports both int and UUID)
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response(
                {'error': f'User with id {user_id} not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        user_permissions = UserPermission.objects.filter(
            user=user,
            permission__is_active=True
        ).select_related('permission')

        permissions_data = [
            {
                'key': up.permission.key,
                'module': up.permission.module,
                'capability': up.permission.capability,
                'label': up.permission.label,
                'granted_at': up.granted_at,
                'granted_by': up.granted_by.username if up.granted_by else None,
            }
            for up in user_permissions
        ]

        return Response({
            'user_id': user.id,
            'username': getattr(user, 'username', str(user)),
            'permissions': permissions_data,
            'total': len(permissions_data),
        })

    @action(detail=False, methods=['post'], url_path='users/(?P<user_id>[^/.]+)/assign')
    def assign_permission(self, request, user_id=None, *args, **kwargs):
        """
        Assign a permission to a user.
        
        POST /api/permissions/users/{user_id}/assign/
        
        Supports both integer IDs and UUIDs for user_id.
        
        Body:
        {
            "permission_key": "complaints.view"
        }
        """
        from django.contrib.auth import get_user_model
        from .models import Permission, UserPermission
        
        User = get_user_model()
        
        try:
            # Try to get user by primary key (supports both int and UUID)
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response(
                {'error': f'User with id {user_id} not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except (ValueError, TypeError):
            return Response(
                {'error': f'Invalid user ID format: {user_id}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        permission_key = request.data.get('permission_key')
        if not permission_key:
            return Response(
                {'error': 'permission_key is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            permission = Permission.objects.get(key=permission_key, is_active=True)
        except Permission.DoesNotExist:
            return Response(
                {'error': f'Permission with key {permission_key} not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Create or get existing assignment
        user_permission, created = UserPermission.objects.get_or_create(
            user=user,
            permission=permission,
            defaults={'granted_by': request.user}
        )

        if not created:
            # Update granted_by if already exists
            user_permission.granted_by = request.user
            user_permission.save(update_fields=['granted_by'])

        return Response({
            'message': 'Permission assigned successfully',
            'user_id': user.id,
            'permission_key': permission.key,
            'created': created,
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='users/(?P<user_id>[^/.]+)/revoke')
    def revoke_permission(self, request, user_id=None, *args, **kwargs):
        """
        Revoke a permission from a user.
        
        POST /api/permissions/users/{user_id}/revoke/
        
        Body:
        {
            "permission_key": "complaints.view"
        }
        """
        from django.contrib.auth import get_user_model
        from .models import Permission, UserPermission
        
        User = get_user_model()
        
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response(
                {'error': f'User with id {user_id} not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        permission_key = request.data.get('permission_key')
        if not permission_key:
            return Response(
                {'error': 'permission_key is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            permission = Permission.objects.get(key=permission_key)
        except Permission.DoesNotExist:
            return Response(
                {'error': f'Permission with key {permission_key} not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            user_permission = UserPermission.objects.get(
                user=user,
                permission=permission
            )
            user_permission.delete()
            return Response({
                'message': 'Permission revoked successfully',
                'user_id': user.id,
                'permission_key': permission.key,
            })
        except UserPermission.DoesNotExist:
            return Response(
                {'error': 'Permission not assigned to this user'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['post'], url_path='bulk-assign')
    def bulk_assign(self, request, *args, **kwargs):
        """
        Bulk assign permissions to one or more users.
        
        POST /api/permissions/bulk-assign/
        
        Body:
        {
            "permission_keys": ["complaints.view", "complaints.create"],
            "user_ids": [1, 2, 3]
        }
        """
        from django.contrib.auth import get_user_model
        from .models import Permission, UserPermission
        
        User = get_user_model()
        
        permission_keys = request.data.get('permission_keys', [])
        user_ids = request.data.get('user_ids', [])

        if not permission_keys:
            return Response(
                {'error': 'permission_keys is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not user_ids:
            return Response(
                {'error': 'user_ids is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Ensure user_ids is a list (supports both single value and list)
        if not isinstance(user_ids, list):
            user_ids = [user_ids]

        # Validate permissions exist
        permissions = Permission.objects.filter(
            key__in=permission_keys,
            is_active=True
        )
        found_keys = set(permissions.values_list('key', flat=True))
        missing_keys = set(permission_keys) - found_keys

        if missing_keys:
            return Response(
                {'error': f'Permissions not found: {list(missing_keys)}'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Validate users exist (supports both int IDs and UUIDs)
        users = User.objects.filter(pk__in=user_ids)
        found_count = users.count()
        requested_count = len(user_ids)

        if found_count != requested_count:
            # Find which users are missing by comparing as strings
            found_user_pks = set(str(uid) for uid in users.values_list('id', flat=True))
            requested_user_pks = set(str(uid) for uid in user_ids)
            missing_user_ids = requested_user_pks - found_user_pks
            
            return Response(
                {'error': f'Users not found: {list(missing_user_ids)}'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Bulk assign
        assignments_created = 0
        assignments_updated = 0

        for user in users:
            for permission in permissions:
                user_permission, created = UserPermission.objects.get_or_create(
                    user=user,
                    permission=permission,
                    defaults={'granted_by': request.user}
                )
                if created:
                    assignments_created += 1
                else:
                    user_permission.granted_by = request.user
                    user_permission.save(update_fields=['granted_by'])
                    assignments_updated += 1

        return Response({
            'message': 'Permissions assigned successfully',
            'assignments_created': assignments_created,
            'assignments_updated': assignments_updated,
            'total_users': len(users),
            'total_permissions': len(permissions),
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], url_path='bulk-revoke')
    def bulk_revoke(self, request, *args, **kwargs):
        """
        Bulk revoke permissions from one or more users.
        
        POST /api/permissions/bulk-revoke/
        
        Body:
        {
            "permission_keys": ["complaints.view", "complaints.create"],
            "user_ids": [1, 2, 3]
        }
        """
        from django.contrib.auth import get_user_model
        from .models import Permission, UserPermission
        
        User = get_user_model()
        
        permission_keys = request.data.get('permission_keys', [])
        user_ids = request.data.get('user_ids', [])

        if not permission_keys:
            return Response(
                {'error': 'permission_keys is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not user_ids:
            return Response(
                {'error': 'user_ids is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get permissions
        permissions = Permission.objects.filter(key__in=permission_keys)
        found_keys = set(permissions.values_list('key', flat=True))
        missing_keys = set(permission_keys) - found_keys

        if missing_keys:
            return Response(
                {'error': f'Permissions not found: {list(missing_keys)}'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Ensure user_ids is a list (supports both single value and list)
        if not isinstance(user_ids, list):
            user_ids = [user_ids]

        # Get users (supports both int IDs and UUIDs)
        users = User.objects.filter(pk__in=user_ids)
        found_count = users.count()
        requested_count = len(user_ids)

        if found_count != requested_count:
            # Find which users are missing by comparing as strings
            found_user_pks = set(str(uid) for uid in users.values_list('id', flat=True))
            requested_user_pks = set(str(uid) for uid in user_ids)
            missing_user_ids = requested_user_pks - found_user_pks
            
            return Response(
                {'error': f'Users not found: {list(missing_user_ids)}'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Bulk revoke
        deleted_count, _ = UserPermission.objects.filter(
            user__in=users,
            permission__in=permissions
        ).delete()

        return Response({
            'message': 'Permissions revoked successfully',
            'revoked_count': deleted_count,
            'total_users': len(users),
            'total_permissions': len(permissions),
        })
