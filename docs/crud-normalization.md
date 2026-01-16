# CRUD Normalization Strategy

## Problem Statement

CRUD (Create, Read, Update, Delete) permissions are fundamental to most applications. However, without a standardized approach, they can become:

- **Duplicated** across modules
- **Inconsistent** in naming
- **Mismatched** between code and database
- **Unpredictable** for frontend developers

## Solution: CRUD Normalization

UPR solves this by defining CRUD capabilities **once globally** and automatically generating them for each module that opts in.

## Strategy Overview

### 1. Global CRUD Definition

CRUD capabilities are defined once at the library level:

```python
STANDARD_CRUD = ['view', 'create', 'update', 'delete']
```

These are:
- Immutable
- Consistent across all modules
- Well-documented
- Frontend-friendly

### 2. Module Opt-In

Modules explicitly opt into CRUD capabilities:

```python
@registry.module('users')
class UsersModule:
    crud = ['view', 'create', 'update', 'delete']  # Opt-in
```

### 3. Automatic Generation

The registry automatically generates CRUD permissions:

```python
# Definition
@registry.module('users')
class UsersModule:
    crud = ['view', 'create', 'update', 'delete']

# Generated permissions
users.view
users.create
users.update
users.delete
```

### 4. Consistent Naming

All CRUD permissions follow the same pattern:

```
<module>.view
<module>.create
<module>.update
<module>.delete
```

## Benefits

### Zero Duplication

CRUD is defined once, used everywhere:

```python
# ✅ Good: Define once
STANDARD_CRUD = ['view', 'create', 'update', 'delete']

# ❌ Bad: Define per module
users_crud = ['view', 'create', 'update', 'delete']
orders_crud = ['view', 'create', 'update', 'delete']  # Duplication!
```

### Zero Mismatch

No possibility of mismatch between modules:

```python
# ✅ Good: Consistent
users.view
orders.view
inventory.view

# ❌ Bad: Inconsistent
users.view
orders.read  # Mismatch!
inventory.list  # Mismatch!
```

### Predictable Frontend Behavior

Frontend can rely on consistent naming:

```javascript
// Frontend can assume all modules have same CRUD structure
function hasPermission(module, action) {
  return userPermissions.includes(`${module}.${action}`);
}

// Works for all modules
hasPermission('users', 'view');
hasPermission('orders', 'view');
hasPermission('inventory', 'view');
```

## CRUD Capabilities

### Standard CRUD Operations

| Capability | HTTP Method | DRF Action | Description |
|------------|-------------|------------|-------------|
| `view` | GET | `list`, `retrieve` | Read/list resources |
| `create` | POST | `create` | Create new resources |
| `update` | PUT, PATCH | `update`, `partial_update` | Modify existing resources |
| `delete` | DELETE | `destroy` | Remove resources |

### View Capability

The `view` capability covers both:
- **List**: GET `/resource/` → `list` action
- **Retrieve**: GET `/resource/{id}/` → `retrieve` action

Both map to the same permission: `<module>.view`

### Update Capability

The `update` capability covers both:
- **Full Update**: PUT `/resource/{id}/` → `update` action
- **Partial Update**: PATCH `/resource/{id}/` → `partial_update` action

Both map to the same permission: `<module>.update`

## Module CRUD Configuration

### Full CRUD

```python
@registry.module('users')
class UsersModule:
    crud = ['view', 'create', 'update', 'delete']
```

Generates all four CRUD permissions.

### Partial CRUD

```python
@registry.module('reports')
class ReportsModule:
    crud = ['view']  # Read-only module
```

Generates only view permission.

### No CRUD

```python
@registry.module('system')
class SystemModule:
    actions = ['restart', 'backup']  # No CRUD, only custom actions
```

No CRUD permissions generated.

### CRUD + Custom Actions

```python
@registry.module('orders')
class OrdersModule:
    crud = ['view', 'create', 'update', 'delete']
    actions = ['cancel', 'refund', 'ship']  # Custom actions in addition
```

Generates CRUD permissions plus custom action permissions.

## Implementation Details

### Registry Processing

```python
class PermissionRegistry:
    STANDARD_CRUD = ['view', 'create', 'update', 'delete']
    
    def process_module(self, module_def):
        permissions = []
        
        # Process CRUD
        if hasattr(module_def, 'crud'):
            for capability in module_def.crud:
                if capability in self.STANDARD_CRUD:
                    permissions.append(self.create_crud_permission(
                        module=module_def.name,
                        capability=capability
                    ))
                else:
                    raise ValidationError(f"Invalid CRUD capability: {capability}")
        
        # Process custom actions
        if hasattr(module_def, 'actions'):
            for action in module_def.actions:
                permissions.append(self.create_action_permission(
                    module=module_def.name,
                    action=action
                ))
        
        return permissions
```

### Permission Generation

```python
def create_crud_permission(self, module, capability):
    return Permission(
        key=f"{module}.{capability}",
        module=module,
        capability=capability,
        label=self.get_crud_label(capability, module),
        type='crud'
    )

def get_crud_label(self, capability, module):
    labels = {
        'view': f"View {module.title()}",
        'create': f"Create {module.title()}",
        'update': f"Update {module.title()}",
        'delete': f"Delete {module.title()}"
    }
    return labels.get(capability, capability)
```

## Validation

### CRUD Validation

The registry validates CRUD declarations:

```python
def validate_crud(self, crud_list):
    valid_crud = ['view', 'create', 'update', 'delete']
    
    for capability in crud_list:
        if capability not in valid_crud:
            raise ValidationError(
                f"Invalid CRUD capability: {capability}. "
                f"Valid options: {valid_crud}"
            )
    
    # Check for duplicates
    if len(crud_list) != len(set(crud_list)):
        raise ValidationError("Duplicate CRUD capabilities found")
```

### Consistency Checks

The registry ensures consistency:

```python
def validate_consistency(self):
    # All modules with CRUD should have same structure
    modules_with_crud = [m for m in modules if hasattr(m, 'crud')]
    
    # Check that all use standard CRUD
    for module in modules_with_crud:
        for capability in module.crud:
            if capability not in STANDARD_CRUD:
                raise ConsistencyError(
                    f"Module {module.name} uses non-standard CRUD: {capability}"
                )
```

## Frontend Integration

### Consistent Permission Checks

```javascript
// Frontend can rely on consistent CRUD structure
const CRUD_ACTIONS = ['view', 'create', 'update', 'delete'];

function checkCRUDPermission(module, action) {
  if (!CRUD_ACTIONS.includes(action)) {
    throw new Error(`Invalid CRUD action: ${action}`);
  }
  return userPermissions.includes(`${module}.${action}`);
}

// Works for all modules
checkCRUDPermission('users', 'view');
checkCRUDPermission('orders', 'create');
```

### Permission UI Components

```javascript
// Reusable CRUD permission component
function CRUDPermissions({ module, permissions }) {
  const crudActions = ['view', 'create', 'update', 'delete'];
  
  return (
    <div>
      {crudActions.map(action => (
        <PermissionCheckbox
          key={action}
          permission={`${module}.${action}`}
          checked={permissions.includes(`${module}.${action}`)}
        />
      ))}
    </div>
  );
}

// Usage
<CRUDPermissions module="users" permissions={userPermissions} />
<CRUDPermissions module="orders" permissions={userPermissions} />
```

## Migration from Non-Normalized Systems

### Step 1: Identify CRUD Permissions

```python
# Old system
users.read
users.write
users.delete

# New system
users.view
users.create
users.update
users.delete
```

### Step 2: Map Old to New

```python
MIGRATION_MAP = {
    'users.read': 'users.view',
    'users.write': ['users.create', 'users.update'],
    'users.delete': 'users.delete',
}
```

### Step 3: Migrate Assignments

```python
def migrate_permissions(user):
    for old_key, new_keys in MIGRATION_MAP.items():
        if user.has_permission(old_key):
            for new_key in new_keys:
                user.assign_permission(new_key)
            user.remove_permission(old_key)
```

## Best Practices

### 1. Always Use Standard CRUD

```python
# ✅ Good: Use standard CRUD
@registry.module('users')
class UsersModule:
    crud = ['view', 'create', 'update', 'delete']

# ❌ Bad: Custom CRUD names
@registry.module('users')
class UsersModule:
    crud = ['read', 'write', 'remove']  # Non-standard!
```

### 2. Be Explicit About CRUD

```python
# ✅ Good: Explicit CRUD list
@registry.module('users')
class UsersModule:
    crud = ['view', 'create', 'update', 'delete']

# ❌ Bad: Implicit or missing
@registry.module('users')
class UsersModule:
    # No CRUD declared - unclear intent
    actions = ['reset_password']
```

### 3. Use Selective CRUD When Appropriate

```python
# ✅ Good: Only declare needed CRUD
@registry.module('reports')
class ReportsModule:
    crud = ['view']  # Read-only

# ❌ Bad: Declare all CRUD even if not needed
@registry.module('reports')
class ReportsModule:
    crud = ['view', 'create', 'update', 'delete']  # But reports are read-only!
```

### 4. Document CRUD Decisions

```python
@registry.module('audit_logs')
class AuditLogsModule:
    # Audit logs are immutable - only view allowed
    crud = ['view']
```

## Common Patterns

### Pattern 1: Full CRUD Module

```python
@registry.module('users')
class UsersModule:
    crud = ['view', 'create', 'update', 'delete']
```

**Use When**: Standard resource management

### Pattern 2: Read-Only Module

```python
@registry.module('reports')
class ReportsModule:
    crud = ['view']
```

**Use When**: Data is generated, not user-created

### Pattern 3: Immutable Module

```python
@registry.module('audit_logs')
class AuditLogsModule:
    crud = ['view']  # Cannot create, update, or delete
```

**Use When**: Data is append-only or immutable

### Pattern 4: CRUD + Custom Actions

```python
@registry.module('orders')
class OrdersModule:
    crud = ['view', 'create', 'update', 'delete']
    actions = ['cancel', 'refund', 'ship']
```

**Use When**: Standard CRUD plus business-specific operations

## Summary

CRUD normalization provides:

- ✅ **Consistency**: Same CRUD structure everywhere
- ✅ **Simplicity**: Define once, use everywhere
- ✅ **Predictability**: Frontend can rely on structure
- ✅ **Maintainability**: Changes in one place affect all modules
- ✅ **Zero Drift**: No possibility of mismatch

This strategy eliminates one of the most common sources of permission system complexity and inconsistency.
