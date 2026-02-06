"""
Helper for querying user permissions and groups.

Use UPRHelper(user) to get direct permissions, group memberships,
and effective permission keys (direct + from groups).
"""
from typing import List, Set


class UPRHelper:
    """
    Helper for a given user: direct permissions, groups, and effective permissions.

    - get_user_permissions(): direct UserPermission assignments (queryset)
    - get_user_groups(): groups the user belongs to (queryset of group model)
    - get_direct_permission_keys(): set of permission keys from direct assignments only
    - get_permission_keys_from_groups(): set of permission keys from groups only
    - get_effective_permission_keys(): set of all permission keys (direct + groups), cached
    - add_permission(permission_keys): replace user's direct permissions with the given list
    - add_groups(group_ids=..., group_slugs=..., granted_by=...): replace user's groups with the given list
    """

    def __init__(self, user):
        self.user = user

    def get_user_permissions(self):
        """Direct permission assignments only (UserPermission). Returns queryset."""
        return self.user.upr_permissions.select_related('permission').all()

    def get_user_groups(self):
        """
        Groups the user belongs to (active groups only).
        Returns queryset of the configured group model.
        """
        from .models import UserGroupMembership
        return UserGroupMembership.objects.filter(
            user=self.user, group__is_active=True
        ).select_related('group').order_by('group__name')

    def get_direct_permission_keys(self) -> Set[str]:
        """Set of permission keys from direct UserPermission assignments only."""
        return set(
            self.get_user_permissions()
            .filter(permission__is_active=True)
            .values_list('permission__key', flat=True)
        )

    def get_permission_keys_from_groups(self) -> Set[str]:
        """Set of permission keys the user has via their groups only (no direct)."""
        from .models import UserGroupMembership, GroupPermission
        group_ids = UserGroupMembership.objects.filter(
            user=self.user, group__is_active=True
        ).values_list('group_id', flat=True)
        if not group_ids:
            return set()
        return set(
            GroupPermission.objects.filter(
                group_id__in=group_ids,
                permission__is_active=True
            ).values_list('permission__key', flat=True)
        )

    def get_effective_permission_keys(self) -> Set[str]:
        """
        Set of all permission keys for this user (direct + from groups).
        Uses same cached resolution as PermissionResolver (check_permission).
        """
        from .permissions import PermissionResolver
        resolver = PermissionResolver()
        return resolver.get_user_permissions(self.user)

    def serialize_user_permissions(self):
        """Serialize direct permission assignments (no group-sourced)."""
        user_permissions = self.get_user_permissions()
        return [
            {
                'key': up.permission.key,
                'module': up.permission.module,
                'capability': up.permission.capability,
                'label': up.permission.label,
                'granted_at': up.granted_at,
                'granted_by': getattr(up.granted_by, 'username', str(up.granted_by)) if up.granted_by else None,
                'source': 'direct',
            }
            for up in user_permissions
        ]

    def serialize_user_groups(self) -> List[dict]:
        """Serialize user's groups (id, name, slug, description)."""
        memberships = self.get_user_groups()
        return [
            {
                'id': m.group.id,
                'name': m.group.name,
                'slug': m.group.slug,
                'description': m.group.description or '',
                'joined_at': m.joined_at,
                'granted_by': getattr(m.granted_by, 'username', str(m.granted_by)) if m.granted_by else None,
            }
            for m in memberships
        ]

    def serialize_effective_permissions(self, include_source: bool = True) -> List[dict]:
        """
        Serialize effective permissions (direct + from groups) with optional source.

        Each item: key, module, capability, label, source.
        source is 'direct' or 'group:<slug>' (or 'group' if slug missing).
        """
        from .models import Permission, GroupPermission
        effective = self.get_effective_permission_keys()
        if not effective:
            return []
        perms = Permission.objects.filter(key__in=effective, is_active=True)
        key_to_direct = self.get_direct_permission_keys()
        # key -> source from groups (one query)
        key_to_group_slug = {}
        group_slug_keys = GroupPermission.objects.filter(
            group__members__user=self.user,
            group__is_active=True,
            permission__is_active=True
        ).values_list('group__slug', 'group__id', 'permission__key')
        for slug, gid, key in group_slug_keys:
            key_to_group_slug[key] = f'group:{slug or gid}'
        result = []
        for p in perms:
            item = {
                'key': p.key,
                'module': p.module,
                'capability': p.capability,
                'label': p.label,
            }
            if include_source:
                if p.key in key_to_direct:
                    item['source'] = 'direct'
                else:
                    item['source'] = key_to_group_slug.get(p.key, 'group')
            result.append(item)
        return result

    def add_permission(self, permission_keys=None):
        """
        Replace user's direct permissions with the given list of permission keys.
        Does not change group memberships or group permissions.
        """
        from .models import UserPermission, Permission
        if permission_keys is None:
            permission_keys = []
        self.user.upr_permissions.all().delete()
        permissions = Permission.objects.filter(key__in=permission_keys)
        to_create = [UserPermission(user=self.user, permission=perm) for perm in permissions]
        if to_create:
            UserPermission.objects.bulk_create(to_create, ignore_conflicts=True)
        return True

    def add_groups(self, group_ids=None, group_slugs=None, granted_by=None):
        """
        Replace user's groups and sync direct permissions to match.

        1. Get permission IDs that belong to the user's current groups.
        2. Remove only those permissions from the user's direct permissions (not all).
        3. Remove previous groups (all UserGroupMembership for this user).
        4. If new groups: assign user to new groups and add their permissions to direct.
        5. If empty: only previous groups and their permissions are removed; other direct
           permissions (e.g. manually assigned) are kept.

        Args:
            group_ids: List of PermissionGroup primary keys (e.g. [1, 2]).
            group_slugs: List of PermissionGroup slugs (e.g. ['editors', 'viewers']).
            granted_by: User who granted (optional, for audit).

        Returns:
            int: Number of groups assigned.
        """
        from .models import get_group_model, UserGroupMembership, GroupPermission, UserPermission, Permission

        GroupModel = get_group_model()

        if group_ids is None:
            group_ids = []
        if group_slugs is None:
            group_slugs = []

        # 1. Permission IDs that belong to the user's current groups (before we remove them)
        current_group_ids = list(
            self.user.upr_group_memberships.values_list('group_id', flat=True)
        )
        if current_group_ids:
            permission_ids_from_groups = set(
                GroupPermission.objects.filter(group_id__in=current_group_ids)
                .values_list('permission_id', flat=True)
                .distinct()
            )
            # 2. Remove only those permissions (from removed groups), not all
            UserPermission.objects.filter(
                user=self.user,
                permission_id__in=permission_ids_from_groups
            ).delete()

        # 3. Remove previous groups
        self.user.upr_group_memberships.all().delete()

        if not group_ids and not group_slugs:
            return 0

        # 4. Assign new groups (use swappable group model)
        if group_ids:
            groups = GroupModel.objects.filter(pk__in=group_ids, is_active=True)
        else:
            groups = GroupModel.objects.filter(slug__in=group_slugs, is_active=True)

        to_create = [
            UserGroupMembership(user=self.user, group=group, granted_by=granted_by)
            for group in groups
        ]
        if to_create:
            UserGroupMembership.objects.bulk_create(to_create)

        # 5. Add direct permissions from the new groups (ignore if already has from manual assign)
        group_ids_list = [g.id for g in groups]
        permission_ids = GroupPermission.objects.filter(
            group_id__in=group_ids_list,
            permission__is_active=True
        ).values_list('permission_id', flat=True).distinct()
        if permission_ids:
            perms = Permission.objects.filter(pk__in=permission_ids)
            new_user_perms = [
                UserPermission(user=self.user, permission=p, granted_by=granted_by)
                for p in perms
            ]
            UserPermission.objects.bulk_create(new_user_perms, ignore_conflicts=True)

        return len(to_create)
