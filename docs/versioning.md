# Versioning & Backward Compatibility

## Overview

UPR handles permission system evolution over time while maintaining backward compatibility and providing clear migration paths.

## Core Principles

### 1. Permission Keys Are Immutable

Permission keys cannot be changed once created:

```python
# ✅ Good: Permission key is stable
users.view  # Always 'users.view'

# ❌ Bad: Cannot rename
users.view → users.read  # Not allowed!
```

**Implications**:
- Permission keys are stable across releases
- Frontend can rely on permission keys
- No breaking changes to permission keys

### 2. Deprecation Before Removal

Permissions are deprecated before removal:

```python
# Step 1: Mark as deprecated
@registry.module('users')
class UsersModule:
    @registry.action('old_action', deprecated=True)
    def old_action(self):
        pass

# Step 2: Wait for migration period
# (Users migrate to new permission)

# Step 3: Remove permission
@registry.module('users')
class UsersModule:
    # old_action removed
    actions = ['new_action']
```

### 3. Backward Compatibility

The system maintains backward compatibility:

- Old permission keys continue to work
- Deprecated permissions are still valid
- Migration paths are provided

## Versioning Strategies

### Adding Permissions

**Strategy**: Add permissions freely - no breaking changes

```python
# Version 1.0
@registry.module('users')
class UsersModule:
    crud = ['view', 'create']

# Version 1.1 - Add new permission
@registry.module('users')
class UsersModule:
    crud = ['view', 'create', 'update']  # New permission
```

**Migration**: None required - new permission is added, existing permissions unchanged

### Removing Permissions

**Strategy**: Deprecate first, then remove after migration period

```python
# Version 1.0
@registry.module('users')
class UsersModule:
    actions = ['old_action']

# Version 1.1 - Deprecate
@registry.module('users')
class UsersModule:
    @registry.action('old_action', deprecated=True)
    def old_action(self):
        pass

# Version 2.0 - Remove (after migration)
@registry.module('users')
class UsersModule:
    # old_action removed
    actions = []
```

**Migration Steps**:
1. Mark permission as deprecated
2. Notify users/developers
3. Wait for migration period (e.g., 6 months)
4. Remove permission
5. Clean up assignments

### Renaming Permissions

**Strategy**: Cannot rename - create new, migrate, remove old

```python
# Version 1.0
@registry.module('users')
class UsersModule:
    actions = ['old_name']

# Version 1.1 - Add new, deprecate old
@registry.module('users')
class UsersModule:
    actions = ['new_name']
    
    @registry.action('old_name', deprecated=True)
    def old_name(self):
        pass

# Version 2.0 - Remove old
@registry.module('users')
class UsersModule:
    actions = ['new_name']
    # old_name removed
```

**Migration Steps**:
1. Create new permission with new name
2. Deprecate old permission
3. Migrate assignments to new permission
4. Wait for migration period
5. Remove old permission

### Changing Permission Metadata

**Strategy**: Metadata can be updated freely

```python
# Version 1.0
@registry.module('users')
class UsersModule:
    @registry.action('reset_password', label='Reset Password')
    def reset_password(self):
        pass

# Version 1.1 - Update label
@registry.module('users')
class UsersModule:
    @registry.action('reset_password', label='Reset User Password')
    def reset_password(self):
        pass
```

**Migration**: None required - metadata changes don't affect functionality

## Deprecation Process

### Step 1: Mark as Deprecated

```python
@registry.module('users')
class UsersModule:
    @registry.action('old_action', deprecated=True, deprecation_message='Use new_action instead')
    def old_action(self):
        pass
```

### Step 2: Update Documentation

```markdown
## Deprecated Permissions

- `users.old_action` - Deprecated in v1.1, use `users.new_action` instead
  - Removal planned for v2.0
  - Migration guide: [link]
```

### Step 3: Notify Users

```python
# In API responses
{
  "key": "users.old_action",
  "is_deprecated": true,
  "deprecation_message": "Use new_action instead",
  "removal_version": "2.0"
}
```

### Step 4: Migration Period

Wait for users to migrate:
- Monitor usage
- Provide migration tools
- Support both old and new permissions

### Step 5: Removal

After migration period:
```python
@registry.module('users')
class UsersModule:
    # old_action removed
    actions = ['new_action']
```

## Backward Compatibility Guarantees

### Permission Keys

- ✅ Permission keys never change
- ✅ Old permission keys continue to work
- ✅ No breaking changes to permission keys

### API Responses

- ✅ API response format is stable
- ✅ New fields are optional/additive
- ✅ Old fields are maintained

### Runtime Behavior

- ✅ Permission checks work the same way
- ✅ Deprecated permissions still work
- ✅ No breaking changes to resolution logic

## Migration Tools

### Permission Migration Script

```python
def migrate_permission_assignments(old_key, new_key):
    """Migrate assignments from old to new permission"""
    old_permission = Permission.objects.get(key=old_key)
    new_permission = Permission.objects.get(key=new_key)
    
    # Get all assignments
    assignments = UserPermission.objects.filter(permission=old_permission)
    
    # Migrate
    for assignment in assignments:
        # Check if user already has new permission
        if not UserPermission.objects.filter(
            user=assignment.user,
            permission=new_permission
        ).exists():
            # Assign new permission
            UserPermission.objects.create(
                user=assignment.user,
                permission=new_permission
            )
        
        # Remove old permission
        assignment.delete()
    
    logger.info(f"Migrated {assignments.count()} assignments")
```

### Deprecation Checker

```python
def check_deprecated_permissions():
    """Check for deprecated permissions still in use"""
    deprecated = Permission.objects.filter(is_deprecated=True)
    
    for permission in deprecated:
        assignments = UserPermission.objects.filter(permission=permission)
        if assignments.exists():
            logger.warning(
                f"Deprecated permission {permission.key} "
                f"still assigned to {assignments.count()} users"
            )
```

## Versioning Best Practices

### 1. Document Changes

```python
# ✅ Good: Document version changes
"""
Version 1.1 Changes:
- Added: users.update permission
- Deprecated: users.old_action (use users.new_action)
- Removed: None
"""

# ❌ Bad: No documentation
# Changes go undocumented
```

### 2. Use Semantic Versioning

```python
# ✅ Good: Semantic versioning
# v1.0.0 - Initial release
# v1.1.0 - Added permissions (minor)
# v2.0.0 - Removed deprecated permissions (major)

# ❌ Bad: No versioning
# Changes unclear
```

### 3. Provide Migration Guides

```markdown
## Migration Guide: v1.0 → v1.1

### Deprecated Permissions

- `users.old_action` → `users.new_action`
  - Migration: Run `python manage.py migrate_permissions`
  - Deadline: v2.0 release
```

### 4. Test Backward Compatibility

```python
# ✅ Good: Test old permissions still work
def test_backward_compatibility():
    # Old permission should still work
    assert check_permission(user, 'users.old_action') == True
    
    # New permission should work
    assert check_permission(user, 'users.new_action') == True
```

### 5. Gradual Migration

```python
# ✅ Good: Gradual migration
# Phase 1: Add new permission, deprecate old
# Phase 2: Migrate assignments
# Phase 3: Remove old permission

# ❌ Bad: Abrupt removal
# Remove permission immediately - breaks existing assignments
```

## Breaking Changes

### What Constitutes Breaking Changes

1. **Removing Permissions**: Breaks existing assignments
2. **Changing Permission Keys**: Breaks references
3. **Changing API Response Format**: Breaks frontend
4. **Changing Resolution Logic**: Breaks behavior

### How to Handle Breaking Changes

1. **Deprecate First**: Mark as deprecated before removal
2. **Provide Migration Path**: Tools and guides
3. **Version API**: Use API versioning for breaking changes
4. **Communicate Clearly**: Release notes, documentation

## API Versioning

### URL Versioning

```
/api/v1/permissions/catalog/
/api/v2/permissions/catalog/
```

### Header Versioning

```
GET /api/permissions/catalog/
Accept: application/vnd.upr.v2+json
```

### Response Versioning

```json
{
  "version": "1.1",
  "modules": [...]
}
```

## Summary

UPR handles versioning through:

- ✅ **Immutable permission keys** - Stable references
- ✅ **Deprecation process** - Clear migration path
- ✅ **Backward compatibility** - Old permissions work
- ✅ **Migration tools** - Automated migration support
- ✅ **Clear documentation** - Version changes documented

The system is designed to evolve over time while maintaining stability and providing clear migration paths.
