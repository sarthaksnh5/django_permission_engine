# Core Concepts

## Domain Model

UPR is built around three core domain concepts that work together to create a comprehensive permission system.

## 1. Permission Key

A **permission key** is the atomic unit of permission in UPR. It is the fundamental identifier used throughout the system.

### Definition

A permission key is:
- **Immutable** - Once created, it cannot be changed
- **String-based** - Simple, readable identifier
- **Globally unique** - No two permissions share the same key
- **Stable** - Does not change across releases

### Format

```
<module>.<capability>
```

### Examples

```
users.view
users.create
users.update
users.delete
users.reset_password
orders.view
orders.create
orders.cancel
breakdown.visit.assign_engineer
breakdown.visit.close
inventory.stock.adjust
```

### Rules

1. **Module Required**: Every permission key must have a module
2. **Capability Required**: Every permission key must have a capability
3. **Dot Separator**: Module and capability separated by a single dot
4. **Lowercase**: Convention is lowercase with underscores
5. **No Spaces**: Spaces are not allowed
6. **No Special Characters**: Only alphanumeric and underscores

### Validation

The registry validates all permission keys:
- Format validation
- Uniqueness checks
- Reserved word checks

### Usage

Permission keys are used:
- In permission definitions
- In database storage
- In runtime checks
- In API responses
- In frontend code

## 2. Module

A **module** is a logical domain grouping of related permissions. It represents a functional area of your application.

### Definition

A module:
- Groups related permissions
- Represents a business domain
- Can have nested submodules
- Is frontend-visible
- Is not necessarily a Django app

### Examples

```
users          # User management
orders         # Order processing
breakdown      # Equipment breakdown management
inventory      # Inventory management
reports        # Reporting system
settings       # Application settings
```

### Module Structure

Modules can be flat or hierarchical:

**Flat Structure**:
```
users
orders
inventory
```

**Hierarchical Structure**:
```
breakdown
  └── visit
      └── assign_engineer
      └── close
inventory
  └── stock
      └── adjust
      └── transfer
```

### Module Characteristics

1. **Owns Permissions**: Modules own their permissions
2. **Can Have Submodules**: Supports nested organization
3. **Frontend-Visible**: Modules appear in permission catalogs
4. **Business Domain**: Represents functional areas, not technical layers

### Module vs Django App

**Important**: A module is **not** the same as a Django app.

- **Django App**: Technical organization (models, views, etc.)
- **Module**: Business domain organization (users, orders, etc.)

A single Django app might have multiple modules, or a module might span multiple Django apps.

### Module Declaration

Modules are declared in the permission definition layer:

```python
@registry.module('users')
class UsersModule:
    crud = ['view', 'create', 'update', 'delete']
    actions = ['reset_password', 'export_data']
```

## 3. Capability

A **capability** represents what can be done. It is the action or operation that a permission grants.

### Types of Capabilities

#### A. Standard (CRUD)

Standard CRUD capabilities are predefined and consistent across all modules:

```
view      # Read/list resources
create    # Create new resources
update    # Modify existing resources
delete    # Remove resources
```

These are:
- Globally defined
- Auto-generated per module
- Consistent naming
- Frontend-friendly

#### B. Action-based

Action-based capabilities are custom and specific to modules:

```
reset_password      # Custom user action
assign_engineer     # Custom breakdown action
export_report       # Custom reporting action
cancel_order        # Custom order action
```

These are:
- Module-specific
- DRF action-aware
- Declared explicitly
- Mapped to ViewSet actions

### Capability Rules

1. **Standard CRUD**: Defined once, used everywhere
2. **Custom Actions**: Declared per module
3. **DRF Mapping**: Custom actions map to DRF action names
4. **Naming Convention**: Lowercase with underscores

### Capability Examples

**Standard CRUD**:
```
users.view
users.create
users.update
users.delete
```

**Custom Actions**:
```
users.reset_password
users.export_data
users.bulk_delete
orders.cancel
orders.refund
breakdown.visit.assign_engineer
breakdown.visit.close
inventory.stock.adjust
```

## Permission Key Construction

### Standard CRUD Permissions

For modules that opt into CRUD, permissions are automatically generated:

```python
@registry.module('users')
class UsersModule:
    crud = ['view', 'create', 'update', 'delete']
```

Generates:
- `users.view`
- `users.create`
- `users.update`
- `users.delete`

### Custom Action Permissions

Custom actions are declared explicitly:

```python
@registry.module('users')
class UsersModule:
    actions = ['reset_password', 'export_data']
```

Generates:
- `users.reset_password`
- `users.export_data`

### Combined Example

```python
@registry.module('users')
class UsersModule:
    crud = ['view', 'create', 'update', 'delete']
    actions = ['reset_password', 'export_data']
```

Generates:
- `users.view`
- `users.create`
- `users.update`
- `users.delete`
- `users.reset_password`
- `users.export_data`

## Permission Hierarchy

While permissions themselves are flat (module.capability), modules can be hierarchical:

```
breakdown
  └── visit
      ├── view
      ├── create
      ├── assign_engineer
      └── close
```

Permission keys remain flat:
- `breakdown.visit.view`
- `breakdown.visit.create`
- `breakdown.visit.assign_engineer`
- `breakdown.visit.close`

## Permission Metadata

Each permission can have associated metadata:

- **Label**: Human-readable name
- **Description**: Detailed explanation
- **Category**: Optional grouping
- **Platform**: Optional platform-specific metadata

### Example

```python
@registry.module('users')
class UsersModule:
    crud = ['view', 'create', 'update', 'delete']
    
    @registry.action('reset_password', label='Reset User Password')
    def reset_password(self):
        pass
```

## Permission Relationships

### Module → Permissions

One module owns many permissions:
```
users → [
    users.view,
    users.create,
    users.update,
    users.delete,
    users.reset_password
]
```

### Capability → Permissions

One capability appears in many modules:
```
view → [
    users.view,
    orders.view,
    inventory.view
]
```

## Permission Lifecycle

### Creation

1. Defined in permission definition layer
2. Registered by registry engine
3. Stored in database
4. Available for assignment

### Usage

1. Assigned to users/roles
2. Checked at runtime
3. Enforced by DRF

### Deprecation

1. Marked as deprecated
2. Removed from new assignments
3. Still valid for existing assignments
4. Eventually removed (with migration)

## Best Practices

### Naming

- Use clear, descriptive module names
- Use action names that match DRF actions
- Keep permission keys short but meaningful
- Follow consistent naming conventions

### Organization

- Group related permissions in modules
- Use hierarchical modules for complex domains
- Keep modules focused on single domains
- Avoid overly granular modules

### Capabilities

- Prefer standard CRUD when possible
- Use custom actions for business-specific operations
- Keep action names consistent with DRF
- Document custom actions clearly
