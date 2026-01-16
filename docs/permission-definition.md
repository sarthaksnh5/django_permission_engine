# Permission Definition Layer

## Overview

The Permission Definition Layer is the **single source of truth** for all permissions in your application. This is where you declare what permissions exist, how they're organized, and what they mean.

## Purpose

This layer defines **everything** about permissions:
- Which modules exist
- What CRUD operations each module supports
- What custom actions each module has
- Labels, descriptions, and metadata

## Responsibilities

1. **Declare Modules**: Define all permission modules
2. **Declare CRUD Support**: Specify which CRUD operations each module supports
3. **Declare Action Permissions**: Define custom action-based permissions
4. **Provide Metadata**: Labels, descriptions, and other metadata
5. **Ensure Completeness**: No permission exists outside this layer

## Guarantees

- ✅ No permission exists outside this layer
- ✅ No permission is defined twice
- ✅ No permission is defined implicitly
- ✅ All permissions are version-controlled
- ✅ All permissions are validated

## Basic Definition

### Simple Module with CRUD

```python
from upr import PermissionRegistry

registry = PermissionRegistry()

@registry.module('users')
class UsersModule:
    crud = ['view', 'create', 'update', 'delete']
```

This creates four permissions:
- `users.view`
- `users.create`
- `users.update`
- `users.delete`

### Module with Custom Actions

```python
@registry.module('users')
class UsersModule:
    crud = ['view', 'create', 'update', 'delete']
    actions = ['reset_password', 'export_data']
```

This creates six permissions:
- `users.view`
- `users.create`
- `users.update`
- `users.delete`
- `users.reset_password`
- `users.export_data`

### Module with Metadata

```python
@registry.module('users', label='User Management', description='Manage application users')
class UsersModule:
    crud = ['view', 'create', 'update', 'delete']
    actions = ['reset_password', 'export_data']
```

## Advanced Definitions

### Hierarchical Modules

```python
@registry.module('breakdown')
class BreakdownModule:
    crud = ['view', 'create', 'update', 'delete']

@registry.module('breakdown.visit')
class BreakdownVisitModule:
    crud = ['view', 'create', 'update']
    actions = ['assign_engineer', 'close', 'reopen']
```

This creates:
- `breakdown.view`
- `breakdown.create`
- `breakdown.update`
- `breakdown.delete`
- `breakdown.visit.view`
- `breakdown.visit.create`
- `breakdown.visit.update`
- `breakdown.visit.assign_engineer`
- `breakdown.visit.close`
- `breakdown.visit.reopen`

### Action with Metadata

```python
@registry.module('users')
class UsersModule:
    crud = ['view', 'create', 'update', 'delete']
    
    @registry.action('reset_password', label='Reset User Password', description='Allows resetting user passwords')
    def reset_password(self):
        pass
    
    @registry.action('export_data', label='Export User Data')
    def export_data(self):
        pass
```

### Selective CRUD

Not all modules need all CRUD operations:

```python
@registry.module('reports')
class ReportsModule:
    crud = ['view']  # Reports are read-only

@registry.module('audit_logs')
class AuditLogsModule:
    crud = ['view']  # Audit logs are immutable
```

### Action-Only Module

Some modules might not need CRUD:

```python
@registry.module('system')
class SystemModule:
    actions = ['restart', 'backup', 'maintenance_mode']
```

## Definition Patterns

### Pattern 1: Standard CRUD Module

```python
@registry.module('orders')
class OrdersModule:
    crud = ['view', 'create', 'update', 'delete']
```

**Use When**: Standard resource management

### Pattern 2: CRUD + Custom Actions

```python
@registry.module('orders')
class OrdersModule:
    crud = ['view', 'create', 'update', 'delete']
    actions = ['cancel', 'refund', 'ship']
```

**Use When**: Standard resource with business-specific operations

### Pattern 3: Read-Only Module

```python
@registry.module('reports')
class ReportsModule:
    crud = ['view']
```

**Use When**: Data is generated, not created by users

### Pattern 4: Action-Only Module

```python
@registry.module('system')
class SystemModule:
    actions = ['restart', 'backup']
```

**Use When**: No standard resource model

### Pattern 5: Hierarchical Module

```python
@registry.module('inventory')
class InventoryModule:
    crud = ['view', 'create', 'update', 'delete']

@registry.module('inventory.stock')
class InventoryStockModule:
    crud = ['view', 'update']
    actions = ['adjust', 'transfer']
```

**Use When**: Complex domain with sub-domains

## Registry Configuration

### Creating the Registry

```python
# upr_config.py
from upr import PermissionRegistry

registry = PermissionRegistry()

# Import all modules
from .modules import users, orders, inventory

# Registry is automatically populated
```

### Registry Settings

```python
registry = PermissionRegistry(
    validate_on_startup=True,  # Validate on app startup
    strict_mode=True,          # Fail on inconsistencies
    auto_sync=False            # Don't auto-sync (use management command)
)
```

## Module Organization

### Recommended Structure

```
your_project/
├── upr_config.py          # Registry definition
├── modules/
│   ├── __init__.py
│   ├── users.py          # Users module
│   ├── orders.py         # Orders module
│   └── inventory.py      # Inventory module
└── ...
```

### Module File Example

```python
# modules/users.py
from upr_config import registry

@registry.module('users', label='User Management')
class UsersModule:
    crud = ['view', 'create', 'update', 'delete']
    actions = ['reset_password', 'export_data', 'bulk_delete']
```

## Validation Rules

### Module Validation

- Module name must be valid identifier
- Module name must be unique
- Module must have at least one permission (CRUD or action)

### CRUD Validation

- CRUD list must contain only: `view`, `create`, `update`, `delete`
- CRUD list cannot be empty (if provided)
- CRUD operations are case-sensitive

### Action Validation

- Action names must be valid identifiers
- Action names must be unique within module
- Action names should match DRF action names

### Permission Key Validation

- Must follow format: `<module>.<capability>`
- Must be globally unique
- Must not contain spaces or special characters
- Must be lowercase with underscores

## Common Mistakes

### ❌ Defining Permissions in Multiple Places

```python
# WRONG: Don't define permissions in ViewSets
class UserViewSet(viewsets.ModelViewSet):
    permission_required = 'users.view'  # Don't do this
```

```python
# CORRECT: Define in permission definition layer
@registry.module('users')
class UsersModule:
    crud = ['view']
```

### ❌ Manual Database Edits

```python
# WRONG: Don't create permissions manually
Permission.objects.create(key='users.view')  # Don't do this
```

```python
# CORRECT: Define in code, sync via registry
@registry.module('users')
class UsersModule:
    crud = ['view']
# Then run: python manage.py upr_sync
```

### ❌ Inconsistent Naming

```python
# WRONG: Inconsistent action names
@registry.module('users')
class UsersModule:
    actions = ['resetPassword', 'export-data']  # Inconsistent
```

```python
# CORRECT: Consistent naming
@registry.module('users')
class UsersModule:
    actions = ['reset_password', 'export_data']  # Consistent
```

## Best Practices

### 1. Organize by Business Domain

Group permissions by business function, not technical structure:

```python
# GOOD: Business domain
@registry.module('customer_orders')
class CustomerOrdersModule:
    crud = ['view', 'create']
```

```python
# BAD: Technical structure
@registry.module('api_v1_orders')
class APIOrdersModule:
    crud = ['view', 'create']
```

### 2. Use Descriptive Names

Choose clear, self-documenting names:

```python
# GOOD: Clear and descriptive
@registry.module('breakdown.visit')
class BreakdownVisitModule:
    actions = ['assign_engineer', 'close_visit']
```

```python
# BAD: Unclear abbreviations
@registry.module('bd.v')
class BDVModule:
    actions = ['ae', 'cv']
```

### 3. Match DRF Action Names

Custom actions should match DRF action names:

```python
# In permission definition
@registry.module('users')
class UsersModule:
    actions = ['reset_password']

# In ViewSet
class UserViewSet(viewsets.ModelViewSet):
    @action(detail=True, methods=['post'])
    def reset_password(self, request, pk=None):
        # Action name matches permission
        ...
```

### 4. Document Complex Permissions

Add descriptions for non-obvious permissions:

```python
@registry.module('orders')
class OrdersModule:
    crud = ['view', 'create', 'update', 'delete']
    
    @registry.action(
        'cancel',
        label='Cancel Order',
        description='Allows canceling orders that are not yet shipped'
    )
    def cancel(self):
        pass
```

### 5. Version Control Everything

Keep all permission definitions in version control:

- Track changes over time
- Review permission additions
- Document permission removals
- Maintain change history

## Migration Strategy

### Adding Permissions

1. Add to definition layer
2. Run registry sync
3. Assign to users/roles
4. Deploy

### Removing Permissions

1. Mark as deprecated in definition
2. Remove from new assignments
3. Wait for deprecation period
4. Remove from definition
5. Run registry sync (with cleanup)

### Renaming Permissions

Permissions cannot be renamed (immutable keys). Instead:

1. Create new permission
2. Migrate assignments
3. Deprecate old permission
4. Remove old permission
