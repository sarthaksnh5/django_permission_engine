# Registry Engine

## Overview

The Permission Registry Engine is responsible for ensuring that the **real system matches the declared system**. It synchronizes permission definitions from code to the database and validates consistency.

## Purpose

The registry engine:
1. **Registers permissions** from the definition layer
2. **Synchronizes database state** with code definitions
3. **Validates consistency** between code and database
4. **Detects breaking changes** and inconsistencies
5. **Reports orphaned permissions** that no longer exist in code

## Core Responsibilities

### 1. Permission Registration

The registry reads permission definitions and registers them:

```python
# Definition
@registry.module('users')
class UsersModule:
    crud = ['view', 'create', 'update', 'delete']
    actions = ['reset_password']

# Registry processes this and creates:
# - users.view
# - users.create
# - users.update
# - users.delete
# - users.reset_password
```

### 2. Database Synchronization

The registry ensures the database matches the definitions:

- **Creates** missing permissions
- **Updates** existing permissions (metadata only, keys are immutable)
- **Detects** orphaned permissions (exist in DB but not in code)
- **Validates** permission key format

### 3. Consistency Validation

The registry validates:
- Permission key format
- Module existence
- Capability validity
- Uniqueness constraints
- Required metadata

### 4. Change Detection

The registry detects:
- New permissions (to be created)
- Modified permissions (metadata changes)
- Orphaned permissions (to be flagged)
- Breaking changes (removed permissions with assignments)

## When Registry Runs

### 1. Application Startup

```python
# settings.py
UPR_CONFIG = {
    'validate_on_startup': True,  # Validate on startup
    'sync_on_startup': False,      # Don't auto-sync (use command)
}
```

**Startup Validation**:
- Checks for consistency
- Reports errors
- Optionally fails fast on errors

### 2. Management Command

```bash
python manage.py upr_sync
```

**Sync Command**:
- Synchronizes all permissions
- Creates missing permissions
- Updates metadata
- Reports changes
- Optionally cleans up orphans

### 3. Explicit API Call

```python
from upr.registry import sync_registry

sync_registry()
```

**Programmatic Sync**:
- Useful for testing
- Useful for migrations
- Useful for deployment scripts

## Synchronization Process

### Step 1: Collect Definitions

```python
# Registry collects all defined permissions
definitions = registry.collect_definitions()
# Returns: {
#     'users.view': {...},
#     'users.create': {...},
#     ...
# }
```

### Step 2: Load Database State

```python
# Load existing permissions from database
existing = Permission.objects.all()
# Returns: QuerySet of Permission objects
```

### Step 3: Compare and Plan

```python
# Compare definitions vs database
plan = registry.plan_sync(definitions, existing)
# Returns: {
#     'create': [...],      # New permissions
#     'update': [...],      # Modified permissions
#     'orphaned': [...],    # Permissions in DB but not in code
#     'unchanged': [...]    # Permissions that match
# }
```

### Step 4: Execute Changes

```python
# Execute the sync plan
registry.execute_sync(plan)
# Creates, updates, and reports
```

### Step 5: Validate Results

```python
# Validate final state
registry.validate()
# Ensures consistency
```

## Sync Operations

### Creating Permissions

```python
# New permission in definition
@registry.module('users')
class UsersModule:
    actions = ['new_action']  # New action

# Registry creates:
Permission.objects.create(
    key='users.new_action',
    module='users',
    capability='new_action',
    label='New Action',
    ...
)
```

### Updating Permissions

```python
# Updated metadata in definition
@registry.module('users')
class UsersModule:
    @registry.action('reset_password', label='Reset Password (Updated)')
    def reset_password(self):
        pass

# Registry updates:
Permission.objects.filter(key='users.reset_password').update(
    label='Reset Password (Updated)',
    ...
)
```

**Note**: Permission keys are immutable. Only metadata can be updated.

### Detecting Orphaned Permissions

```python
# Permission exists in DB but not in code
# DB: users.old_action
# Code: (not defined)

# Registry reports:
{
    'orphaned': [
        {
            'key': 'users.old_action',
            'has_assignments': True,  # Still assigned to users
            'action': 'warn'  # or 'error' or 'delete'
        }
    ]
}
```

## Validation Rules

### Permission Key Validation

```python
def validate_permission_key(key):
    # Must match format: <module>.<capability>
    assert '.' in key, "Permission key must contain a dot"
    module, capability = key.split('.', 1)
    assert module, "Module cannot be empty"
    assert capability, "Capability cannot be empty"
    assert key.islower(), "Permission key must be lowercase"
    assert re.match(r'^[a-z0-9_]+$', key), "Invalid characters"
```

### Module Validation

```python
def validate_module(module_name):
    assert module_name, "Module name cannot be empty"
    assert re.match(r'^[a-z0-9_]+(\.[a-z0-9_]+)*$', module_name), "Invalid module name"
```

### Capability Validation

```python
def validate_capability(capability):
    standard_crud = ['view', 'create', 'update', 'delete']
    if capability in standard_crud:
        return True
    # Custom capabilities must be valid identifiers
    assert re.match(r'^[a-z0-9_]+$', capability), "Invalid capability name"
```

### Uniqueness Validation

```python
def validate_uniqueness(permissions):
    keys = [p.key for p in permissions]
    assert len(keys) == len(set(keys)), "Duplicate permission keys found"
```

## Error Handling

### Validation Errors

```python
# Invalid permission key
@registry.module('users')
class UsersModule:
    actions = ['invalid-key']  # Hyphen not allowed

# Registry raises:
ValidationError("Invalid permission key format: users.invalid-key")
```

### Consistency Errors

```python
# Permission in DB but not in code
# If strict_mode=True:
RegistryError("Orphaned permission found: users.old_action")

# If strict_mode=False:
Warning("Orphaned permission found: users.old_action")
```

### Breaking Change Detection

```python
# Permission removed but still assigned
# DB: users.old_action (assigned to 5 users)
# Code: (not defined)

# Registry reports:
BreakingChangeError(
    "Permission 'users.old_action' is assigned to 5 users but no longer exists in code"
)
```

## Registry Configuration

### Configuration Options

```python
registry = PermissionRegistry(
    # Validation
    validate_on_startup=True,      # Validate on app startup
    strict_mode=True,               # Fail on inconsistencies
    
    # Synchronization
    auto_sync=False,                # Don't auto-sync (use command)
    sync_on_startup=False,          # Don't sync on startup
    
    # Orphaned Permissions
    orphan_action='warn',          # 'warn', 'error', or 'delete'
    delete_orphans=False,           # Don't auto-delete orphans
    
    # Breaking Changes
    fail_on_breaking_changes=True,  # Fail if permissions removed with assignments
)
```

### Environment-Specific Settings

```python
# settings.py
UPR_CONFIG = {
    'validate_on_startup': True,
    'strict_mode': True,  # Production: strict
    # 'strict_mode': False,  # Development: lenient
}
```

## Management Commands

### Sync Command

```bash
python manage.py upr_sync
```

**Options**:
- `--dry-run`: Show what would change without making changes
- `--force`: Force sync even with warnings
- `--clean-orphans`: Delete orphaned permissions
- `--verbose`: Show detailed output

**Output**:
```
Syncing permissions...
  Created: 3 permissions
  Updated: 2 permissions
  Orphaned: 1 permission (users.old_action)
  Unchanged: 45 permissions
Sync complete.
```

### Validate Command

```bash
python manage.py upr_validate
```

**Checks**:
- Permission key format
- Module consistency
- Capability validity
- Uniqueness
- Orphaned permissions

**Output**:
```
Validating permissions...
  ✓ All permission keys valid
  ✓ No duplicate permissions
  ⚠ 1 orphaned permission found
Validation complete.
```

### List Command

```bash
python manage.py upr_list
```

**Output**:
```
Registered Permissions:
  users.view
  users.create
  users.update
  users.delete
  users.reset_password
  orders.view
  ...
Total: 52 permissions
```

## Best Practices

### 1. Run Sync in CI/CD

```yaml
# .github/workflows/ci.yml
- name: Validate Permissions
  run: python manage.py upr_validate

- name: Sync Permissions
  run: python manage.py upr_sync --dry-run
```

### 2. Fail Fast in Production

```python
# Production settings
UPR_CONFIG = {
    'validate_on_startup': True,
    'strict_mode': True,
    'fail_on_breaking_changes': True,
}
```

### 3. Handle Orphaned Permissions

```python
# Development: Warn
UPR_CONFIG = {
    'orphan_action': 'warn',
}

# Production: Error
UPR_CONFIG = {
    'orphan_action': 'error',
}
```

### 4. Document Permission Changes

When adding/removing permissions:
1. Update permission definitions
2. Run sync command
3. Update migration notes
4. Update API documentation

## Troubleshooting

### Permission Not Found

**Problem**: Permission exists in code but not in database

**Solution**: Run sync command
```bash
python manage.py upr_sync
```

### Orphaned Permission

**Problem**: Permission exists in database but not in code

**Solution**: 
1. Check if permission should be removed
2. If yes, remove assignments first
3. Then remove from code
4. Run sync with `--clean-orphans`

### Validation Failure

**Problem**: Registry validation fails on startup

**Solution**:
1. Check error message
2. Fix permission definitions
3. Run `python manage.py upr_validate`
4. Fix any remaining issues

### Breaking Change

**Problem**: Permission removed but still assigned

**Solution**:
1. Don't remove permission yet
2. Mark as deprecated
3. Migrate assignments to new permission
4. Wait for deprecation period
5. Remove permission
6. Run sync
