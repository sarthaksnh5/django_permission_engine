# User Groups

Permission groups let you assign a set of permissions to a **group**, then assign users to that group. Users get those permissions in addition to any **direct** permissions. This is separate from Django's built-in `auth.Group` (tables: `upr_permission_groups`, `upr_group_permissions`, `upr_user_group_memberships`).

---

## Concepts

- **PermissionGroup**: A named group (e.g. "Editors", "Viewers") with optional slug and description.
- **GroupPermission**: Links a group to a permission; users in the group receive that permission.
- **UserGroupMembership**: Links a user to a group; the user receives all permissions of the group (when the group is active).

**Effective permissions** = direct permissions (UserPermission) ∪ permissions from all active groups the user belongs to.

---

## Models

- **PermissionGroup**: `name`, `slug` (optional, unique), `description`, `is_active`, `created_at`, `updated_at`
- **GroupPermission**: `group`, `permission`, `granted_at`, `granted_by`
- **UserGroupMembership**: `user`, `group`, `joined_at`, `granted_by`

---

## UPRHelper: Groups and Permission Keys

Use `UPRHelper(user)` to work with groups and permission keys separately.

### Get user's groups

```python
from django_permission_engine import UPRHelper

helper = UPRHelper(request.user)

# Queryset of UserGroupMembership (user's active groups)
memberships = helper.get_user_groups()

# Serialized list of groups (id, name, slug, description, joined_at, granted_by)
groups_data = helper.serialize_user_groups()
```

### Get permission keys separately

```python
# Set of permission keys from direct assignments only
direct_keys = helper.get_direct_permission_keys()   # set of str

# Set of permission keys from groups only (no direct)
from_groups_keys = helper.get_permission_keys_from_groups()   # set of str

# Set of all effective permission keys (direct + groups), cached
effective_keys = helper.get_effective_permission_keys()   # set of str
```

### Serialize effective permissions with source

```python
# List of {key, module, capability, label, source}
# source is 'direct' or 'group:<slug>' (or 'group' if no slug)
effective_list = helper.serialize_effective_permissions(include_source=True)
```

### Direct permissions (existing)

```python
# Queryset of UserPermission (direct assignments)
direct_queryset = helper.get_user_permissions()

# Serialized direct permissions (each with source='direct')
direct_data = helper.serialize_user_permissions()
```

---

## APIs

Same access control as permission management (`UPR_CONFIG['can_manage_permissions']`).

### Groups

- **GET** `/api/permissions/groups/` – List groups (query: `active_only=true|false`)
- **POST** `/api/permissions/groups/` – Create group (body: `name`, optional `slug`, `description`, `is_active`)
- **GET** `/api/permissions/groups/{group_id}/` – Get group
- **PUT/PATCH** `/api/permissions/groups/{group_id}/` – Update group
- **DELETE** `/api/permissions/groups/{group_id}/` – Delete group
- **GET** `/api/permissions/groups/{group_id}/permissions/` – List group's permissions
- **POST** `/api/permissions/groups/{group_id}/assign/` – Assign permission to group (body: `permission_key`)
- **POST** `/api/permissions/groups/{group_id}/revoke/` – Revoke permission from group (body: `permission_key`)

### User–group membership

- **GET** `/api/permissions/users/{user_id}/groups/` – List user's groups
- **POST** `/api/permissions/users/{user_id}/groups/assign/` – Assign group to user (body: `group_id` or `group_slug`)
- **POST** `/api/permissions/users/{user_id}/groups/revoke/` – Revoke group from user (body: `group_id` or `group_slug`)

### User permissions (extended)

- **GET** `/api/permissions/users/{user_id}/?effective=1` – Same as before, plus `effective_permissions` (list with `source`: `direct` or `group:<slug>`) and `effective_total`.

---

## Example: Create group and assign to user

```python
from django_permission_engine.models import PermissionGroup, GroupPermission, UserGroupMembership, Permission

# Create group
group = PermissionGroup.objects.create(
    name='Editors',
    slug='editors',
    description='Can edit content',
    is_active=True
)

# Assign permissions to group
for key in ['content.view', 'content.create', 'content.update']:
    perm = Permission.objects.get(key=key)
    GroupPermission.objects.get_or_create(group=group, permission=perm)

# Assign user to group
UserGroupMembership.objects.get_or_create(user=user, group=group)
```

Using the helper to check effective permissions:

```python
from django_permission_engine import UPRHelper

helper = UPRHelper(user)
assert 'content.update' in helper.get_effective_permission_keys()
assert 'content.update' in helper.get_permission_keys_from_groups()
```

---

## Caching

User permission cache key `user_permissions:{user_id}` includes both direct and group permissions. Cache is invalidated when:

- UserPermission is added/removed for that user
- UserGroupMembership is added/removed for that user
- GroupPermission is added/removed for any group the user is in
- PermissionGroup (e.g. `is_active`) changes for any group the user is in

---

## Backward compatibility

- Existing code that only uses direct permissions is unchanged.
- If you do not create any groups or memberships, behavior is the same as before.
- Resolution: `check_permission(user, key)` is true if the user has the key **directly or via any group**.
