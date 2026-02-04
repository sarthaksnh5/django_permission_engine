# User Groups – Implementation Plan

This document describes how to add **User Groups** to the Django Permission Engine without breaking existing behavior. Groups allow assigning a set of default permissions to a group, then assigning users to groups; users get those permissions in addition to any direct permissions.

---

## 1. Goals

- **Store** which group(s) a user belongs to (user–group membership).
- **Store** which permissions each group has (group–permission assignment).
- **Resolution**: A user has a permission if they have it **directly** (existing `UserPermission`) **or** via any of their **groups** (new).
- **Direct + group**: Users can have both direct permissions and group-based permissions; the union is used for checks.
- **No breaking changes**: All current APIs, models, and resolution behavior remain; we only extend resolution to include group permissions.

---

## 2. Naming and Django’s auth.Group

Django already has `django.contrib.auth.models.Group` and `User.groups`. To avoid clashes and confusion:

- **Do not** use the name `Group` or touch `User.groups`.
- Use a distinct name, e.g. **`PermissionGroup`** (or `UPRGroup`), with table name `upr_permission_groups`.
- User–group membership uses a dedicated model (e.g. **`UserGroupMembership`**) with `related_name` like `upr_group_memberships` on the user side.

---

## 3. New Models

### 3.1 PermissionGroup

- **Purpose**: A named group that can hold a set of permissions.
- **Fields**:
  - `name` (CharField, required)
  - `slug` (CharField, unique, optional but recommended for stable references)
  - `description` (TextField, blank=True)
  - `is_active` (BooleanField, default=True) – inactive groups don’t grant permissions.
  - `created_at`, `updated_at`
- **Meta**: `db_table = "upr_permission_groups"`, ordering, indexes.
- **Note**: No FK to Permission here; the link is via GroupPermission (many-to-many with optional through model).

### 3.2 GroupPermission (through / explicit M2M)

- **Purpose**: Which permissions a group has.
- **Fields**:
  - `group` (ForeignKey → PermissionGroup, related_name='permission_assignments' or 'group_permissions')
  - `permission` (ForeignKey → Permission, related_name='group_assignments')
  - Optional: `granted_at`, `granted_by` for audit.
- **Meta**: `unique_together = [group, permission]`, `db_table = "upr_group_permissions"`.

### 3.3 UserGroupMembership

- **Purpose**: Which groups a user belongs to.
- **Fields**:
  - `user` (ForeignKey → `settings.AUTH_USER_MODEL`, related_name='upr_group_memberships')
  - `group` (ForeignKey → PermissionGroup, related_name='members')
  - Optional: `joined_at`, `granted_by` for audit.
- **Meta**: `unique_together = [user, group]`, `db_table = "upr_user_group_memberships"`.

**No changes** to existing models: `Permission`, `Module`, `UserPermission` stay as they are.

---

## 4. Permission Resolution (Core Change)

**Current behavior** (unchanged):

- `PermissionResolver._load_user_permissions(user)` returns permission keys from **`UserPermission`** only.
- `check_permission(user, key)` is true iff `key` is in that set.

**New behavior** (additive only):

- **Effective user permissions** = (direct permissions from `UserPermission`) ∪ (permissions from all groups the user is in via `UserGroupMembership` → `GroupPermission`).
- Implementation: In `_load_user_permissions(user)`:
  1. Load direct: `UserPermission.objects.filter(user=user, permission__is_active=True).values_list('permission__key', flat=True)`.
  2. Load from groups: get user’s groups from `UserGroupMembership` where group is active; for those groups, get all `GroupPermission.permission.key` where `permission.is_active=True`.
  3. Return the **union** of both sets (as before, still a set of strings).
- **Caching**: Same cache key `user_permissions:{user.id}`; the cached value now includes both direct and group permissions. No new cache key.

**Backward compatibility**: If there are no groups, no memberships, and no group permissions, the union equals the current direct set. No behavior change for existing data or code.

---

## 5. Cache Invalidation

**Current**: Signals on `UserPermission` and `Permission` invalidate `user_permissions:{user_id}` and `permission_catalog`.

**Add**:

- **UserGroupMembership** (post_save, post_delete): Invalidate `user_permissions:{instance.user_id}` (user’s effective permissions changed).
- **GroupPermission** (post_save, post_delete): Invalidate `user_permissions:{user_id}` for **every user in that group** (all members of `instance.group`). This can be done by:
  - Querying `UserGroupMembership.objects.filter(group=instance.group).values_list('user_id', flat=True)` and deleting `user_permissions:{uid}` for each; or
  - Using a cache key pattern if the cache backend supports delete by pattern (e.g. `user_permissions:*`); otherwise loop over member user IDs.
- **PermissionGroup** (post_save, post_delete): If `is_active` or existence changes, same as GroupPermission – invalidate cache for all users in that group.

So: any change in group membership or group permissions invalidates the affected users’ permission caches.

---

## 6. APIs (Optional but Recommended)

All of these are **additive**; existing user-permission APIs stay as they are.

### 6.1 Group CRUD (optional)

- List groups: `GET /api/permissions/groups/`
- Create: `POST /api/permissions/groups/`
- Detail: `GET /api/permissions/groups/{id}/`
- Update: `PATCH /api/permissions/groups/{id}/`
- Delete: `DELETE /api/permissions/groups/{id}/`

Same access control as permission management (e.g. `UPR_CONFIG['can_manage_permissions']`).

### 6.2 Group permissions

- List permissions of a group: `GET /api/permissions/groups/{id}/permissions/`
- Assign permission to group: `POST /api/permissions/groups/{id}/assign/` (body: `{"permission_key": "module.capability"}` or list).
- Revoke permission from group: `POST /api/permissions/groups/{id}/revoke/`

### 6.3 User–group membership

- List groups of a user: `GET /api/permissions/users/{user_id}/groups/`
- Assign group to user: `POST /api/permissions/users/{user_id}/groups/assign/` (body: `{"group_id": 1}` or `{"group_slug": "editors"}`).
- Revoke group from user: `POST /api/permissions/users/{user_id}/groups/revoke/`

### 6.4 “Get user permissions” response (optional enhancement)

- Current: `GET /api/permissions/users/{user_id}/` returns a flat list of permissions.
- Optional: Add a field `source` per permission: `"direct"` vs `"group:<group_slug>"` so the UI can show whether a permission comes from direct assignment or from a group. This is a response shape extension only; resolution logic stays “union of direct + group”.

---

## 7. Helpers / Public API

- **UPRHelper** (existing): `get_user_permissions()` already goes through the resolver or the same load logic; once `_load_user_permissions` includes groups, `UPRHelper.get_user_permissions()` will automatically reflect direct + group permissions. No API change needed; behavior is extended.
- Optional: Add `UPRHelper.get_user_groups()` returning the user’s groups (for UI or debugging). Not required for resolution.

---

## 8. Migrations

- One migration that:
  - Creates `PermissionGroup` (table `upr_permission_groups`).
  - Creates `GroupPermission` (table `upr_group_permissions`).
  - Creates `UserGroupMembership` (table `upr_user_group_memberships`).
- No migrations that alter existing tables (Permission, UserPermission) except if we add an index for performance later; not required for correctness.

---

## 9. Tests

- **Resolution**: User with no direct permission but in a group that has permission X → `check_permission(user, X)` is True. User with direct permission and same permission via group → still True. User in no groups and no direct → unchanged.
- **Cache**: After adding/removing UserGroupMembership or GroupPermission, next `get_user_permissions(user)` returns updated set (cache invalidated).
- **APIs**: If implemented, tests for group CRUD, assign/revoke group permissions, assign/revoke user groups, and that user permissions response includes group-sourced permissions when applicable.

---

## 10. Documentation Updates

- **README / SETUP.md**: Short section on “User Groups” – create groups, assign permissions to groups, assign users to groups; effective permissions = direct + group.
- **docs/**: New `user-groups.md` (or section in `roles-users.md`) describing models, resolution semantics, cache invalidation, and APIs.
- **CHANGELOG**: New entry for “User Groups” feature (additive, backward compatible).

---

## 11. Summary of “What Does Not Change”

- **Permission**, **Module**, **UserPermission** models: unchanged.
- **Registry**, **opt-in** logic, **ViewSet/module/action** mapping: unchanged.
- **Catalog API** (including `allowed_keys` / `get_allowed_permission_keys`): unchanged.
- **User permission management API** (assign/revoke direct permissions): unchanged.
- **PermissionResolver** public API: same `check_permission(user, key)` and `get_user_permissions(user)`; only the **implementation** of `_load_user_permissions` is extended to add group permissions to the set.
- **Cache key** for user permissions: same `user_permissions:{user_id}`; value is now the union of direct + group permissions.

---

## 12. Implementation Order (Suggested)

1. **Models**: Add `PermissionGroup`, `GroupPermission`, `UserGroupMembership`; migration; register signals for cache invalidation.
2. **Resolution**: Update `_load_user_permissions(user)` to union direct + group permissions; add tests.
3. **APIs** (optional): Group CRUD, group permissions assign/revoke, user groups assign/revoke; optionally extend user-permissions response with `source`.
4. **Helpers**: Optional `get_user_groups()` on UPRHelper.
5. **Docs**: README/SETUP + user-groups.md (or roles-users section) + CHANGELOG.

This order keeps the core “permission check” correct and cached first, then adds management and UX on top.
