# DRF Action Coupling Strategy

## Problem Statement

In traditional permission systems, there's often a disconnect between:

- **DRF action names** (e.g., `reset_password`, `cancel_order`)
- **Permission names** (e.g., `can_reset_password`, `can_cancel_order`)
- **Database permission keys** (e.g., `users.reset_password`, `orders.cancel`)

This leads to:
- **Drift** between actions and permissions
- **Manual mapping** required everywhere
- **Runtime surprises** when actions don't match permissions
- **Maintenance burden** of keeping them in sync

## Solution: Action Coupling

UPR solves this by making **DRF action names canonical** - they become the permission capability names directly.

## Strategy Overview

### 1. Action Names Are Canonical

DRF action names are the source of truth:

```python
# DRF action
@action(detail=True, methods=['post'])
def reset_password(self, request, pk=None):
    ...

# Permission automatically: users.reset_password
# No mapping needed!
```

### 2. Permissions Reference Actions Directly

Permissions are defined using action names:

```python
@registry.module('users')
class UsersModule:
    actions = ['reset_password']  # Matches DRF action name
```

### 3. Registry Introspects ViewSets

The registry can introspect ViewSets to detect actions:

```python
# Registry can discover actions automatically
registry.discover_actions(UserViewSet)
# Finds: reset_password, export_data, etc.
```

### 4. Missing Permissions Detected Early

The registry validates that all actions have permissions:

```python
# Validation on startup
registry.validate_actions()
# Error if action exists without permission
```

## Guarantees

### No Action Without Permission

Every DRF action must have a corresponding permission:

```python
# ✅ Good: Action has permission
@registry.module('users')
class UsersModule:
    actions = ['reset_password']

@action(detail=True, methods=['post'])
def reset_password(self, request, pk=None):
    # Permission: users.reset_password exists
    ...

# ❌ Bad: Action without permission
@action(detail=True, methods=['post'])
def reset_password(self, request, pk=None):
    # Permission: users.reset_password does NOT exist
    # Registry will error on startup
    ...
```

### No Permission Without Action

Every action permission should have a corresponding DRF action:

```python
# ✅ Good: Permission has action
@registry.module('users')
class UsersModule:
    actions = ['reset_password']

@action(detail=True, methods=['post'])
def reset_password(self, request, pk=None):
    ...

# ⚠️ Warning: Permission without action
@registry.module('users')
class UsersModule:
    actions = ['reset_password', 'old_action']  # old_action has no DRF action
    # Registry will warn
```

### No Runtime Surprises

Actions and permissions are validated before deployment:

```python
# Registry validates on startup
if not registry.validate_actions():
    raise ValidationError("Actions and permissions are out of sync")
    # App refuses to start
```

## Implementation

### Action Discovery

```python
class ActionDiscovery:
    def discover_actions(self, viewset_class):
        """Discover all actions in a ViewSet"""
        actions = []
        
        # Get standard actions
        if issubclass(viewset_class, ModelViewSet):
            actions.extend(['list', 'retrieve', 'create', 'update', 'destroy'])
        
        # Get custom actions
        for attr_name in dir(viewset_class):
            attr = getattr(viewset_class, attr_name, None)
            if hasattr(attr, 'mapping'):  # DRF action decorator
                actions.append(attr_name)
        
        return actions
```

### Permission Validation

```python
class PermissionRegistry:
    def validate_actions(self):
        """Validate that all actions have permissions"""
        errors = []
        
        for viewset_class in self.registered_viewsets:
            module = getattr(viewset_class, 'module', None)
            if not module:
                continue
            
            actions = self.discover_actions(viewset_class)
            defined_permissions = self.get_module_permissions(module)
            
            for action in actions:
                # Skip standard CRUD (handled separately)
                if action in ['list', 'retrieve', 'create', 'update', 'destroy']:
                    continue
                
                permission_key = f"{module}.{action}"
                if permission_key not in defined_permissions:
                    errors.append(
                        f"Action '{action}' in {viewset_class.__name__} "
                        f"has no permission: {permission_key}"
                    )
        
        return errors
```

### Runtime Resolution

```python
class PermissionResolver:
    def resolve_action(self, viewset, action_name):
        """Resolve permission for a DRF action"""
        module = getattr(viewset, 'module', None)
        if not module:
            return None
        
        # Standard CRUD actions are normalized
        if action_name in ['list', 'retrieve']:
            capability = 'view'
        elif action_name == 'create':
            capability = 'create'
        elif action_name in ['update', 'partial_update']:
            capability = 'update'
        elif action_name == 'destroy':
            capability = 'delete'
        else:
            # Custom actions use action name directly
            capability = action_name
        
        return f"{module}.{capability}"
```

## Action Name Rules

### Naming Convention

Action names must follow Python identifier rules:

```python
# ✅ Good: Valid identifiers
reset_password
export_data
bulk_delete
assign_engineer

# ❌ Bad: Invalid identifiers
reset-password  # Hyphen not allowed
export data     # Space not allowed
123action       # Cannot start with number
```

### Consistency

Action names should be consistent:

```python
# ✅ Good: Consistent naming
@action(detail=True, methods=['post'])
def reset_password(self, request, pk=None):
    ...

@action(detail=True, methods=['post'])
def export_data(self, request, pk=None):
    ...

# ❌ Bad: Inconsistent naming
@action(detail=True, methods=['post'])
def resetPassword(self, request, pk=None):  # camelCase
    ...

@action(detail=True, methods=['post'])
def export-data(self, request, pk=None):  # kebab-case
    ...
```

### Matching Permission Definitions

Action names must match permission definitions exactly:

```python
# ✅ Good: Exact match
@registry.module('users')
class UsersModule:
    actions = ['reset_password']

@action(detail=True, methods=['post'])
def reset_password(self, request, pk=None):
    # Matches: users.reset_password
    ...

# ❌ Bad: Mismatch
@registry.module('users')
class UsersModule:
    actions = ['reset_password']

@action(detail=True, methods=['post'], name='reset-password')
def reset_password(self, request, pk=None):
    # Action name is 'reset-password' but permission is 'users.reset_password'
    # Mismatch!
    ...
```

## ViewSet Integration

### Declaring Actions

```python
class UserViewSet(viewsets.ModelViewSet):
    permission_classes = [PermissionRequired]
    module = 'users'
    
    @action(detail=True, methods=['post'])
    def reset_password(self, request, pk=None):
        # Automatically requires 'users.reset_password'
        # No manual permission check needed
        ...
```

### Action with Custom Name

If you need a custom URL name but keep the action name:

```python
@action(
    detail=True,
    methods=['post'],
    url_path='reset-password',  # URL: /users/1/reset-password/
    url_name='reset-password'    # URL name
)
def reset_password(self, request, pk=None):
    # Action name is still 'reset_password'
    # Permission is still 'users.reset_password'
    # URL is 'reset-password' (kebab-case for URLs)
    ...
```

## Validation Workflow

### Startup Validation

```python
# On application startup
registry.validate_actions()

# Output:
# ✓ All actions have permissions
# ⚠ Warning: Permission 'users.old_action' has no corresponding action
# ✗ Error: Action 'new_action' in UserViewSet has no permission: users.new_action
```

### CI/CD Validation

```bash
# In CI/CD pipeline
python manage.py upr_validate_actions

# Fails if actions and permissions are out of sync
```

### Development Validation

```python
# During development
@action(detail=True, methods=['post'])
def new_action(self, request, pk=None):
    # Developer adds action
    ...

# Registry detects missing permission on next sync
python manage.py upr_sync
# Error: Action 'new_action' has no permission
```

## Common Patterns

### Pattern 1: Simple Action

```python
@registry.module('users')
class UsersModule:
    actions = ['reset_password']

@action(detail=True, methods=['post'])
def reset_password(self, request, pk=None):
    ...
```

### Pattern 2: Multiple Actions

```python
@registry.module('users')
class UsersModule:
    actions = ['reset_password', 'export_data', 'bulk_delete']

@action(detail=True, methods=['post'])
def reset_password(self, request, pk=None):
    ...

@action(detail=False, methods=['get'])
def export_data(self, request):
    ...

@action(detail=False, methods=['post'])
def bulk_delete(self, request):
    ...
```

### Pattern 3: Action with Conditions

```python
@registry.module('orders')
class OrdersModule:
    actions = ['cancel', 'refund']

@action(detail=True, methods=['post'])
def cancel(self, request, pk=None):
    order = self.get_object()
    if order.status != 'pending':
        raise ValidationError("Can only cancel pending orders")
    # Permission: orders.cancel
    ...
```

## Troubleshooting

### Action Not Found

**Problem**: Action exists but permission check fails

**Solution**: 
1. Check action name matches permission
2. Verify module is declared
3. Run `python manage.py upr_validate_actions`

### Permission Not Found

**Problem**: Permission exists but action validation fails

**Solution**:
1. Check if action exists in ViewSet
2. Verify action name matches permission
3. Check for typos in action name

### Mismatched Names

**Problem**: Action name doesn't match permission

**Solution**:
1. Use consistent naming (underscores)
2. Match action name exactly in permission definition
3. Don't use custom `name` parameter unless necessary

## Best Practices

### 1. Use Consistent Naming

```python
# ✅ Good: Consistent
reset_password
export_data

# ❌ Bad: Inconsistent
resetPassword
export-data
```

### 2. Match Names Exactly

```python
# ✅ Good: Exact match
# Permission: users.reset_password
# Action: reset_password

# ❌ Bad: Mismatch
# Permission: users.reset_password
# Action: reset-password (different!)
```

### 3. Validate Early

```python
# ✅ Good: Validate on startup
registry.validate_actions()

# ❌ Bad: Discover at runtime
# User gets 403, then you debug
```

### 4. Document Actions

```python
@action(
    detail=True,
    methods=['post'],
    permission_required='users.reset_password'  # Documented
)
def reset_password(self, request, pk=None):
    """Reset user password. Requires 'users.reset_password' permission."""
    ...
```

### 5. Use Action Discovery

```python
# ✅ Good: Let registry discover actions
registry.discover_actions(UserViewSet)

# ❌ Bad: Manually maintain action list
actions = ['reset_password', 'export_data']  # Easy to miss updates
```

## Summary

Action coupling provides:

- ✅ **No Drift**: Actions and permissions stay in sync
- ✅ **No Manual Mapping**: Actions become permissions automatically
- ✅ **Early Detection**: Problems found before deployment
- ✅ **Consistency**: Same naming everywhere
- ✅ **Maintainability**: One source of truth (action names)

This strategy eliminates the disconnect between DRF actions and permissions, making the system more maintainable and less error-prone.
