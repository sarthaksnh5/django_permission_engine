# Drift Prevention

## Overview

Drift prevention is a **critical feature** of UPR. It ensures that permissions remain consistent across code, database, API, and frontend - eliminating one of the most common sources of bugs in permission systems.

## What Is Drift?

Permission drift occurs when different parts of the system have different views of what permissions exist:

- **Code vs Database**: Permissions defined in code but not in database (or vice versa)
- **API vs Code**: API exposes permissions that don't exist in code
- **Action vs Permission**: DRF actions without corresponding permissions
- **Frontend vs Backend**: Frontend expects permissions that backend doesn't have

## Types of Drift

### 1. Database vs Code Drift

**Problem**: Permissions exist in database but not in code (or vice versa)

**Example**:
```python
# Code: Permission removed
@registry.module('users')
class UsersModule:
    # reset_password removed
    actions = ['export_data']

# Database: Permission still exists
Permission.objects.filter(key='users.reset_password')
# Returns: <Permission: users.reset_password>
```

**Impact**: 
- Code expects permission doesn't exist
- Database has orphaned permission
- Users may have assignments to non-existent permission

### 2. API vs Code Drift

**Problem**: API exposes permissions that don't match code definitions

**Example**:
```python
# Code: Permission renamed
@registry.module('users')
class UsersModule:
    actions = ['reset_user_password']  # Renamed

# API: Still returns old permission
GET /api/permissions/catalog/
# Returns: users.reset_password (old name)
```

**Impact**:
- Frontend sees wrong permissions
- Role editors show incorrect options
- Users assigned to wrong permissions

### 3. Action vs Permission Drift

**Problem**: DRF actions exist without corresponding permissions

**Example**:
```python
# Code: Action added but permission not defined
@action(detail=True, methods=['post'])
def new_feature(self, request, pk=None):
    ...

# Permission: Not defined
@registry.module('users')
class UsersModule:
    actions = []  # new_feature missing!
```

**Impact**:
- Action accessible without permission check
- Security vulnerability
- Inconsistent behavior

### 4. Frontend vs Backend Drift

**Problem**: Frontend expects permissions that backend doesn't provide

**Example**:
```javascript
// Frontend: Expects permission
if (userPermissions.includes('users.export_data')) {
  showExportButton();
}

// Backend: Permission doesn't exist
@registry.module('users')
class UsersModule:
    actions = []  # export_data missing
```

**Impact**:
- Frontend shows/hides features incorrectly
- User experience issues
- Potential security issues

## How Drift Is Prevented

### 1. Startup Validation

The registry validates consistency on application startup:

```python
# On startup
registry.validate()

# Checks:
# - All code permissions exist in database
# - All database permissions exist in code
# - All actions have permissions
# - All permissions have valid format
```

**Failure Mode**: Application refuses to start if validation fails

```python
# settings.py
UPR_CONFIG = {
    'validate_on_startup': True,
    'strict_mode': True,  # Fail fast on errors
}
```

### 2. Registry Synchronization

The registry synchronizes database with code definitions:

```python
# Sync command
python manage.py upr_sync

# Actions:
# - Creates missing permissions
# - Updates metadata
# - Detects orphaned permissions
# - Reports inconsistencies
```

**Output**:
```
Syncing permissions...
  Created: 3 permissions
  Updated: 2 permissions
  Orphaned: 1 permission (users.old_action)
  Unchanged: 45 permissions
Sync complete.
```

### 3. Strict Failure on Mismatch

The registry fails strictly when mismatches are detected:

```python
# Strict mode
registry = PermissionRegistry(strict_mode=True)

# On mismatch:
# - Raises ValidationError
# - Refuses to continue
# - Provides clear error message
```

**Error Example**:
```
ValidationError: Permission 'users.new_action' is defined in code but not in database.
Run 'python manage.py upr_sync' to synchronize.
```

### 4. CI/CD Integration

Drift prevention can be integrated into CI/CD pipelines:

```yaml
# .github/workflows/ci.yml
- name: Validate Permissions
  run: python manage.py upr_validate

- name: Sync Permissions (Dry Run)
  run: python manage.py upr_sync --dry-run
```

**Benefits**:
- Catches drift before deployment
- Prevents production issues
- Maintains consistency

## Validation Mechanisms

### Code-to-Database Validation

```python
def validate_code_to_database(self):
    """Validate that all code permissions exist in database"""
    code_permissions = set(self.get_all_permission_keys())
    db_permissions = set(
        Permission.objects.values_list('key', flat=True)
    )
    
    missing_in_db = code_permissions - db_permissions
    if missing_in_db:
        raise ValidationError(
            f"Permissions defined in code but not in database: {missing_in_db}"
        )
```

### Database-to-Code Validation

```python
def validate_database_to_code(self):
    """Validate that all database permissions exist in code"""
    code_permissions = set(self.get_all_permission_keys())
    db_permissions = set(
        Permission.objects.values_list('key', flat=True)
    )
    
    orphaned = db_permissions - code_permissions
    if orphaned:
        if self.strict_mode:
            raise ValidationError(
                f"Orphaned permissions in database: {orphaned}"
            )
        else:
            warnings.warn(f"Orphaned permissions: {orphaned}")
```

### Action-to-Permission Validation

```python
def validate_actions(self):
    """Validate that all actions have permissions"""
    errors = []
    
    for viewset in self.registered_viewsets:
        module = getattr(viewset, 'module', None)
        if not module:
            continue
        
        actions = self.discover_actions(viewset)
        permissions = self.get_module_permissions(module)
        
        for action in actions:
            if action in ['list', 'retrieve', 'create', 'update', 'destroy']:
                continue  # CRUD handled separately
            
            permission_key = f"{module}.{action}"
            if permission_key not in permissions:
                errors.append(
                    f"Action '{action}' in {viewset.__name__} "
                    f"has no permission: {permission_key}"
                )
    
    if errors:
        raise ValidationError("\n".join(errors))
```

## Synchronization Process

### Step 1: Collect Definitions

```python
def collect_definitions(self):
    """Collect all permission definitions from code"""
    definitions = {}
    
    for module in self.modules:
        # CRUD permissions
        for capability in module.crud:
            key = f"{module.name}.{capability}"
            definitions[key] = {
                'module': module.name,
                'capability': capability,
                'type': 'crud',
                'label': self.get_crud_label(capability, module.name)
            }
        
        # Action permissions
        for action in module.actions:
            key = f"{module.name}.{action}"
            definitions[key] = {
                'module': module.name,
                'capability': action,
                'type': 'action',
                'label': self.get_action_label(action, module.name)
            }
    
    return definitions
```

### Step 2: Compare with Database

```python
def compare_with_database(self, definitions):
    """Compare definitions with database state"""
    db_permissions = {
        p.key: p for p in Permission.objects.all()
    }
    
    plan = {
        'create': [],
        'update': [],
        'orphaned': []
    }
    
    # Find new permissions
    for key, definition in definitions.items():
        if key not in db_permissions:
            plan['create'].append(definition)
        else:
            # Check if metadata changed
            existing = db_permissions[key]
            if self.metadata_changed(existing, definition):
                plan['update'].append(definition)
    
    # Find orphaned permissions
    for key, permission in db_permissions.items():
        if key not in definitions:
            plan['orphaned'].append(permission)
    
    return plan
```

### Step 3: Execute Changes

```python
def execute_sync(self, plan):
    """Execute synchronization plan"""
    # Create new permissions
    for definition in plan['create']:
        Permission.objects.create(**definition)
        logger.info(f"Created permission: {definition['key']}")
    
    # Update existing permissions
    for definition in plan['update']:
        Permission.objects.filter(key=definition['key']).update(**definition)
        logger.info(f"Updated permission: {definition['key']}")
    
    # Handle orphaned permissions
    for permission in plan['orphaned']:
        if self.orphan_action == 'delete':
            permission.delete()
            logger.info(f"Deleted orphaned permission: {permission.key}")
        elif self.orphan_action == 'warn':
            logger.warning(f"Orphaned permission: {permission.key}")
        elif self.orphan_action == 'error':
            raise ValidationError(f"Orphaned permission: {permission.key}")
```

## Configuration

### Strict Mode

```python
# Strict mode: Fail on any inconsistency
registry = PermissionRegistry(strict_mode=True)

# On inconsistency:
# - Raises ValidationError
# - Application refuses to start
# - Clear error messages
```

### Lenient Mode

```python
# Lenient mode: Warn but continue
registry = PermissionRegistry(strict_mode=False)

# On inconsistency:
# - Logs warnings
# - Application continues
# - Issues reported but not blocking
```

### Orphan Handling

```python
# Options for orphaned permissions
registry = PermissionRegistry(
    orphan_action='warn'  # 'warn', 'error', or 'delete'
)

# warn: Log warning, keep permission
# error: Raise error, refuse to continue
# delete: Delete orphaned permission
```

## Best Practices

### 1. Validate on Startup

```python
# ✅ Good: Validate on startup
UPR_CONFIG = {
    'validate_on_startup': True,
    'strict_mode': True,
}

# ❌ Bad: No validation
UPR_CONFIG = {
    'validate_on_startup': False,
}
```

### 2. Run Sync in CI/CD

```yaml
# ✅ Good: Validate in CI
- name: Validate Permissions
  run: python manage.py upr_validate

# ❌ Bad: No CI validation
```

### 3. Use Strict Mode in Production

```python
# ✅ Good: Strict in production
if settings.DEBUG:
    strict_mode = False
else:
    strict_mode = True

# ❌ Bad: Lenient in production
strict_mode = False  # In production!
```

### 4. Regular Syncs

```bash
# ✅ Good: Regular syncs
python manage.py upr_sync

# ❌ Bad: Never syncing
# Permissions drift over time
```

### 5. Monitor Orphaned Permissions

```python
# ✅ Good: Monitor and clean up
python manage.py upr_sync --clean-orphans

# ❌ Bad: Ignore orphaned permissions
# They accumulate over time
```

## Troubleshooting

### Validation Fails on Startup

**Problem**: Application won't start due to validation errors

**Solution**:
1. Check error message
2. Run `python manage.py upr_sync`
3. Fix permission definitions
4. Re-run validation

### Orphaned Permissions

**Problem**: Permissions in database but not in code

**Solution**:
1. Check if permission should be removed
2. If yes, remove assignments first
3. Remove from code
4. Run sync with `--clean-orphans`

### Missing Permissions

**Problem**: Permissions in code but not in database

**Solution**:
1. Run `python manage.py upr_sync`
2. Check sync output
3. Verify permissions created

### Action-Permission Mismatch

**Problem**: Actions without permissions

**Solution**:
1. Add permission to module definition
2. Run sync
3. Verify action has permission

## Summary

Drift prevention ensures:

- ✅ **Consistency**: Code and database always match
- ✅ **Early Detection**: Problems found before deployment
- ✅ **Automation**: Sync process handles updates
- ✅ **Safety**: Strict mode prevents inconsistencies
- ✅ **Maintainability**: System stays in sync automatically

This is one of the most valuable features of UPR, eliminating a major source of bugs and maintenance burden in permission systems.
