"""
Group Management API: CRUD for permission groups, assign/revoke permissions to groups.
Uses same access control as permission management (UPR_CONFIG['can_manage_permissions']).
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import serializers

from .models import PermissionGroup, GroupPermission, Permission
from .permission_management import ConfigurablePermissionManagementPermission


class PermissionGroupSerializer(serializers.ModelSerializer):
    """Serializer for PermissionGroup list, create, retrieve, update."""

    class Meta:
        model = PermissionGroup
        fields = ['id', 'name', 'slug', 'description', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
        extra_kwargs = {
            'slug': {'required': False, 'allow_blank': True, 'allow_null': True},
            'description': {'required': False, 'allow_blank': True},
        }

    def validate_slug(self, value):
        if value is None or value == '':
            return value
        qs = PermissionGroup.objects.filter(slug=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('Group with this slug already exists.')
        return value


class GroupManagementViewSet(viewsets.ModelViewSet):
    """
    API for managing permission groups and their permissions.

    Endpoints:
    - GET/POST /api/permissions/groups/ - List, create groups (list returns results + total)
    - GET/PUT/PATCH/DELETE /api/permissions/groups/{id}/ - Detail, update, delete
    - GET /api/permissions/groups/{id}/permissions/ - List group permissions
    - POST /api/permissions/groups/{id}/assign/ - Assign permission to group
    - POST /api/permissions/groups/{id}/revoke/ - Revoke permission from group
    """
    permission_classes = [ConfigurablePermissionManagementPermission]
    serializer_class = PermissionGroupSerializer
    queryset = PermissionGroup.objects.all().order_by('name')
    # Restrict ordering to model fields (PermissionGroup has created_at, not created)
    ordering_fields = ['id', 'name', 'slug', 'created_at', 'updated_at', 'is_active']
    ordering = ['name']

    def get_queryset(self):
        qs = super().get_queryset()
        active_only = self.request.query_params.get('active_only', 'true').lower() == 'true'
        if active_only:
            qs = qs.filter(is_active=True)
        return qs

    def get_ordering(self):
        """Return valid ordering; map 'created' -> 'created_at' (PermissionGroup has no 'created' field)."""
        ordering = super().get_ordering()
        if not ordering:
            return self.ordering
        allowed = set(self.ordering_fields)
        result = []
        for term in ordering:
            raw = term.lstrip('-')
            if raw == 'created':
                term = ('-' if term.startswith('-') else '') + 'created_at'
            if term.lstrip('-') in allowed:
                result.append(term)
        return result if result else self.ordering

    def filter_queryset(self, queryset):
        """Apply filters; avoid FieldError when project uses ordering='created' (model has created_at)."""
        from django.core.exceptions import FieldError
        try:
            return super().filter_queryset(queryset)
        except FieldError as e:
            if 'created' in str(e) or 'ordering' in str(e).lower():
                return queryset.order_by(*self.ordering)
            raise

    def list(self, request, *args, **kwargs):
        """List groups with results and total for consistency."""
        qs = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(qs, many=True)
        return Response({
            'results': serializer.data,
            'total': qs.count(),
        })

    @action(detail=True, methods=['get'], url_path='permissions')
    def permissions_list(self, request, pk=None, *args, **kwargs):
        """List permissions assigned to this group. URL: /api/permissions/groups/{id}/permissions/"""
        group = self.get_object()
        perms = GroupPermission.objects.filter(
            group=group, permission__is_active=True
        ).select_related('permission')
        data = [
            {
                'key': gp.permission.key,
                'module': gp.permission.module,
                'capability': gp.permission.capability,
                'label': gp.permission.label,
                'granted_at': gp.granted_at,
            }
            for gp in perms
        ]
        return Response({
            'group_id': group.id,
            'group_name': group.name,
            'results': data,
            'total': len(data),
        })

    @action(detail=True, methods=['post'], url_path='assign')
    def assign_permission(self, request, pk=None, *args, **kwargs):
        """
        Replace all permissions for this group with the given list.
        Body: {"permission_keys": ["module.capability", ...]}
        Deletes existing group permissions and assigns only the keys passed.
        """
        group = self.get_object()
        permission_keys = request.data.get('permission_keys', [])
        if not isinstance(permission_keys, list):
            return Response(
                {'error': 'permission_keys must be a list'},
                status=status.HTTP_400_BAD_REQUEST
            )
        GroupPermission.objects.filter(group=group).delete()
        if not permission_keys:
            return Response({
                'message': 'Group permissions updated (all removed)',
                'group_id': group.id,
                'assigned_count': 0,
            }, status=status.HTTP_200_OK)
        perms = Permission.objects.filter(key__in=permission_keys, is_active=True)
        to_create = [
            GroupPermission(group=group, permission=p, granted_by=request.user)
            for p in perms
        ]
        GroupPermission.objects.bulk_create(to_create)
        return Response({
            'message': 'Group permissions updated successfully',
            'group_id': group.id,
            'assigned_count': len(to_create),
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='revoke')
    def revoke_permission(self, request, pk=None, *args, **kwargs):
        """Revoke a permission from this group. Body: {"permission_key": "module.capability"}"""
        group = self.get_object()
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
        deleted, _ = GroupPermission.objects.filter(
            group=group, permission=permission
        ).delete()
        if not deleted:
            return Response(
                {'error': 'Permission not assigned to this group'},
                status=status.HTTP_404_NOT_FOUND
            )
        return Response({
            'message': 'Permission revoked from group successfully',
            'group_id': group.id,
            'permission_key': permission.key,
        })
