# User Groups

Permission groups let you assign a set of permissions to a **group**, then assign users to that group. Users get those permissions in addition to any **direct** permissions. This is separate from Django's built-in `auth.Group` (tables: `upr_permission_groups`, `upr_group_permissions`, `upr_user_group_memberships`).

---

## Concepts

- **Group model** (default: **PermissionGroup**): A named group (e.g. "Editors", "Viewers") with optional slug and description. You can swap this for a custom model via **UPR_GROUP_MODEL** (see [Swappable group model](#swappable-group-model)).
- **GroupPermission**: Links a group to a permission; users in the group receive that permission.
- **UserGroupMembership**: Links a user to a group; the user receives all permissions of the group (when the group is active).

**Effective permissions** = direct permissions (UserPermission) ∪ permissions from all active groups the user belongs to.

---

## Models

- **Group model** (default **PermissionGroup**): `name`, `slug` (optional, unique), `description`, `is_active`, `created_at`, `updated_at`
- **GroupPermission**: `group`, `permission`, `granted_at`, `granted_by`
- **UserGroupMembership**: `user`, `group`, `joined_at`, `granted_by`

---

## Swappable group model

If you set **UPR_GROUP_MODEL** in settings (e.g. `'myapp.DepartmentUserGroup'`), the engine uses that model instead of **PermissionGroup**. If unset or invalid, **PermissionGroup** is used.

- Your custom model must provide the same fields as the default group (or subclass **AbstractPermissionGroup** from `django_permission_engine.models`).
- Use **get_group_model()** from `django_permission_engine.models` when you need the active group model in code (e.g. for queries or serializers). The helper, group management API, and user–group APIs already use the swappable model.

### Using AbstractPermissionGroup for a custom group model

The recommended way to define a custom group model is to subclass **AbstractPermissionGroup**. You get all required fields (`name`, `slug`, `description`, `is_active`, `created_at`, `updated_at`) and can add your own.

**1. Define your model** (e.g. in `myapp/models.py`):

```python
from django.db import models
from django_permission_engine.models import AbstractPermissionGroup


class DepartmentUserGroup(AbstractPermissionGroup):
    """
    Custom permission group scoped to a department.
    Subclasses AbstractPermissionGroup so it works with GroupPermission and UserGroupMembership.
    """
    department = models.ForeignKey(
        'myapp.Department',
        on_delete=models.CASCADE,
        related_name='permission_groups',
        null=True,
        blank=True,
    )

    class Meta:
        db_table = 'myapp_department_user_groups'
        verbose_name = 'Department permission group'
        verbose_name_plural = 'Department permission groups'
```

**2. Create and run migrations** for your app so the new table exists.

**3. Point the engine at your model** in `settings.py`:

```python
UPR_GROUP_MODEL = 'myapp.DepartmentUserGroup'
```

After that, all group behaviour (UPRHelper, group management API, user–group assign/revoke, cache invalidation) uses **DepartmentUserGroup**. You can still use **get_group_model()** in code when you need the active model:

```python
from django_permission_engine.models import get_group_model

GroupModel = get_group_model()  # Returns DepartmentUserGroup when UPR_GROUP_MODEL is set
groups = GroupModel.objects.filter(department=some_dept, is_active=True)
```

**Notes:**

- Your custom model must subclass **AbstractPermissionGroup** (or implement the same field names and behaviour). Do not change the names of the base fields the engine expects (`name`, `slug`, `description`, `is_active`, `created_at`, `updated_at`).
- **GroupPermission** and **UserGroupMembership** reference the group via a foreign key to the swappable model; ensure your app’s migrations run after `django_permission_engine` so the FK can resolve to your table.
- If you need a minimal custom model with no extra fields, subclass **AbstractPermissionGroup** and only set **Meta** (e.g. `db_table`, `verbose_name`).

### Custom group model with UUID primary key

The default **PermissionGroup** uses Django’s **BigAutoField** (integer/bigint) for its primary key. The engine’s migrations therefore create `group_id` in **GroupPermission** and **UserGroupMembership** as **bigint**. If your custom group model uses a **UUID** primary key, Django may generate an **AlterField** migration that tries to change `group_id` from bigint to uuid. In PostgreSQL that fails with: **cannot cast type bigint to uuid**, because the column type cannot be converted in place.

**Fix:** use a migration that **removes** the `group` field and then **adds** it again, so the column is recreated as UUID instead of altered. That avoids any cast.

1. **Do not use** the auto-generated migration that only does `AlterField(..., name='group', ...)`.
2. **Create a migration** in the `django_permission_engine` app (or replace the failing one) with the operations below. Replace `'department.departmentusergroup'` and the dependency `'department', '0008_departmentusergroup'` with your app label, model name, and your group model’s migration.

**Example migration** (e.g. `django_permission_engine/migrations/0003_switch_to_uuid_group_fk.py`):

```python
# django_permission_engine/migrations/0003_switch_to_uuid_group_fk.py
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('django_permission_engine', '0002_user_groups'),
        ('department', '0008_departmentusergroup'),  # Your app + migration that creates your UUID group model
    ]

    operations = [
        # GroupPermission: drop bigint group_id, add UUID group_id (no cast)
        migrations.RemoveField(model_name='grouppermission', name='group'),
        migrations.AddField(
            model_name='grouppermission',
            name='group',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='permission_assignments',
                to='department.departmentusergroup',  # Your group model
            ),
        ),
        # UserGroupMembership: same
        migrations.RemoveField(model_name='usergroupmembership', name='group'),
        migrations.AddField(
            model_name='usergroupmembership',
            name='group',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='members',
                to='department.departmentusergroup',  # Your group model
            ),
        ),
    ]
```

**Important:** `RemoveField` drops the column and its data. Use this only on empty tables (e.g. before you have group permissions/memberships) or accept that existing `group_id` values will be lost. For an existing database with data you need to keep, you would need a custom data migration (copy to a temporary table, recreate columns, backfill with a mapping from old group ids to new UUIDs).

**Alternative:** if you do not need a UUID primary key for your custom group, use **BigAutoField** (or leave the default) so the primary key stays integer. Then the auto-generated **AlterField** only changes the FK target, not the column type, and the migration runs without error.

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
from django_permission_engine.models import get_group_model, GroupPermission, UserGroupMembership, Permission

GroupModel = get_group_model()

# Create group
group = GroupModel.objects.create(
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
- The configured group model (e.g. `is_active` on the group) changes for any group the user is in

---

## Backward compatibility

- Existing code that only uses direct permissions is unchanged.
- If you do not create any groups or memberships, behavior is the same as before.
- Resolution: `check_permission(user, key)` is true if the user has the key **directly or via any group**.
