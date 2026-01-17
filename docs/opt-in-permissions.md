# Opt-In Permission Model

## Overview

Django Permission Engine uses an **opt-in permission model**. This means that only actions explicitly defined in your UPR configuration require permission checks. Actions that are not defined in the registry are automatically allowed (assuming the user is authenticated).

## Core Principle

> **If an action is not defined in the UPR registry, it does not require permission checking.**

This allows you to:
- Gradually adopt permission checking for your ViewSets
- Have some actions that are always allowed (public or authenticated-only)
- Avoid having to define permissions for every single action

## How It Works

### Permission Resolution Flow

```
1. User makes request to ViewSet action
   ↓
2. Check if ViewSet has module assigned
   ├─ No module → Allow (skip permission checking)
   └─ Has module → Continue
   ↓
3. Construct permission key: <module>.<action>
   ↓
4. Check if permission exists in UPR registry
   ├─ Not in registry → Allow (opt-in model)
   └─ In registry → Check user permissions
       ├─ User has permission → Allow
       └─ User lacks permission → Deny
```

### Example Scenarios

#### Scenario 1: Action Not Defined in Registry

```python
# UPR Config
@module('users', label='User Management')
class UsersModule:
    crud = ['view', 'create', 'update', 'delete']
    actions = ['reset_password']  # 'export_data' is NOT defined

# ViewSet
class UserViewSet(viewsets.ModelViewSet):
    permission_classes = [PermissionRequired]
    module = 'users'
    
    @action(detail=False, methods=['get'])
    def export_data(self, request):
        # This action is NOT in the UPR config
        # Result: ALLOWED (no permission check)
        return Response({'data': ...})
```

**Result**: The `export_data` action is allowed because it's not defined in the UPR registry.

#### Scenario 2: Action Defined in Registry

```python
# UPR Config
@module('users', label='User Management')
class UsersModule:
    crud = ['view', 'create', 'update', 'delete']
    actions = ['reset_password', 'export_data']  # 'export_data' IS defined

# ViewSet
class UserViewSet(viewsets.ModelViewSet):
    permission_classes = [PermissionRequired]
    module = 'users'
    
    @action(detail=False, methods=['get'])
    def export_data(self, request):
        # This action IS in the UPR config
        # Result: Requires 'users.export_data' permission
        return Response({'data': ...})
```

**Result**: The `export_data` action requires the `users.export_data` permission.

#### Scenario 3: CRUD Actions

```python
# UPR Config
@module('users', label='User Management')
class UsersModule:
    crud = ['view', 'create', 'update']  # 'delete' is NOT defined
    actions = []

# ViewSet
class UserViewSet(viewsets.ModelViewSet):
    permission_classes = [PermissionRequired]
    module = 'users'
    
    # DELETE /users/1/ → 'destroy' action
    # Maps to 'users.delete' permission
    # 'delete' is NOT in crud list
    # Result: ALLOWED (no permission check)
```

**Result**: The `destroy` action (DELETE) is allowed because `delete` is not in the `crud` list.

## Benefits

### 1. Gradual Adoption

You can start using UPR without defining permissions for every action:

```python
# Start with just a few permissions
@module('users', label='User Management')
class UsersModule:
    crud = ['view', 'create']  # Only protect read and create
    actions = ['reset_password']  # Only protect password reset

# Other actions (update, delete, export, etc.) are automatically allowed
```

### 2. Public Actions

Some actions can remain public (authenticated-only) without permission checks:

```python
@module('public', label='Public API')
class PublicModule:
    crud = []  # No CRUD permissions
    actions = []  # No action permissions

class PublicViewSet(viewsets.ViewSet):
    permission_classes = [PermissionRequired]
    module = 'public'
    
    @action(detail=False, methods=['get'])
    def health_check(self, request):
        # Always allowed (authenticated users only)
        return Response({'status': 'ok'})
```

### 3. Flexible Permission Strategy

You can have different permission strategies for different modules:

```python
# Strict module: All actions require permissions
@module('admin', label='Admin Panel')
class AdminModule:
    crud = ['view', 'create', 'update', 'delete']
    actions = ['export', 'import', 'backup', 'restore']

# Loose module: Only critical actions require permissions
@module('public', label='Public API')
class PublicModule:
    crud = ['view']  # Only read requires permission
    actions = ['subscribe']  # Only subscription requires permission
```

## Implementation Details

### Registry Check

The permission resolver checks if a permission exists in the registry before enforcing it:

```python
def resolve(self, user, viewset, action, http_method):
    # Get module
    module = self.get_module(viewset)
    if not module:
        return True  # No module = allow
    
    # Normalize action
    capability = self.normalize_action(action, http_method)
    
    # Construct permission key
    permission_key = f"{module}.{capability}"
    
    # Check if permission exists in registry
    if not self.permission_exists_in_registry(permission_key):
        return True  # Not in registry = allow (opt-in model)
    
    # Permission exists - check user permissions
    return self.check_permission(user, permission_key)
```

### Registry Lookup

The resolver queries the registry to check if a permission is defined:

```python
def permission_exists_in_registry(self, permission_key: str) -> bool:
    """Check if permission exists in UPR registry"""
    from django_permission_engine import get_registry
    registry = get_registry()
    return permission_key in registry.get_all_permission_keys()
```

## Best Practices

### 1. Explicit Permission Definition

For actions that should be protected, explicitly define them:

```python
# ✅ Good: Explicit permission definition
@module('users', label='User Management')
class UsersModule:
    crud = ['view', 'create', 'update', 'delete']
    actions = ['reset_password', 'export_data', 'bulk_delete']

# All protected actions are clearly visible
```

### 2. Document Public Actions

If an action is intentionally public, document it:

```python
class UserViewSet(viewsets.ModelViewSet):
    permission_classes = [PermissionRequired]
    module = 'users'
    
    @action(detail=False, methods=['get'])
    def public_profile(self, request):
        """
        Public user profile endpoint.
        Note: This action is intentionally NOT in UPR config,
        so it's accessible to all authenticated users.
        """
        return Response({'profile': ...})
```

### 3. Regular Audits

Periodically review your ViewSets to ensure all sensitive actions are protected:

```python
# Review checklist:
# 1. List all ViewSet actions
# 2. Check which are in UPR config
# 3. Verify unprotected actions are intentionally public
# 4. Add missing permissions to UPR config if needed
```

### 4. Use Dry Run for Validation

Use the validation command to check for inconsistencies:

```bash
python manage.py upr_validate
```

This will help identify:
- Actions that require permissions but aren't defined
- Permissions defined but not used

## Migration Strategy

### Phase 1: Start with Critical Actions

```python
# Begin with only the most critical permissions
@module('users', label='User Management')
class UsersModule:
    crud = ['delete']  # Only protect deletion
    actions = ['reset_password']  # Only protect password reset
```

### Phase 2: Expand Gradually

```python
# Add more permissions over time
@module('users', label='User Management')
class UsersModule:
    crud = ['view', 'create', 'update', 'delete']  # All CRUD
    actions = ['reset_password', 'export_data']  # More actions
```

### Phase 3: Full Coverage

```python
# Eventually cover all sensitive actions
@module('users', label='User Management')
class UsersModule:
    crud = ['view', 'create', 'update', 'delete']
    actions = [
        'reset_password',
        'export_data',
        'bulk_delete',
        'change_role',
        # ... all sensitive actions
    ]
```

## Common Patterns

### Pattern 1: Public Read, Protected Write

```python
@module('articles', label='Article Management')
class ArticlesModule:
    crud = ['create', 'update', 'delete']  # Write operations protected
    # 'view' not in crud = public read access

class ArticleViewSet(viewsets.ModelViewSet):
    permission_classes = [PermissionRequired]
    module = 'articles'
    # GET /articles/ → allowed (no permission)
    # POST /articles/ → requires 'articles.create'
```

### Pattern 2: Admin-Only Actions

```python
@module('admin', label='Admin Operations')
class AdminModule:
    crud = []
    actions = ['backup', 'restore', 'migrate']  # Only admin actions

class AdminViewSet(viewsets.ViewSet):
    permission_classes = [PermissionRequired]
    module = 'admin'
    
    @action(detail=False, methods=['post'])
    def backup(self, request):
        # Requires 'admin.backup' permission
        ...
    
    @action(detail=False, methods=['get'])
    def status(self, request):
        # No permission required (not in config)
        ...
```

### Pattern 3: Mixed Protection Levels

```python
@module('orders', label='Order Management')
class OrdersModule:
    crud = ['view', 'create', 'update']  # Standard CRUD
    actions = ['cancel', 'refund']  # Critical actions

class OrderViewSet(viewsets.ModelViewSet):
    permission_classes = [PermissionRequired]
    module = 'orders'
    
    # Protected actions
    # - list, retrieve → 'orders.view'
    # - create → 'orders.create'
    # - update → 'orders.update'
    # - cancel → 'orders.cancel'
    # - refund → 'orders.refund'
    
    # Unprotected actions (not in config)
    # - destroy → allowed (delete not in crud)
    # - export → allowed (not in actions)
    # - print → allowed (not in actions)
```

## Security Considerations

### Important Notes

1. **Authentication Still Required**: The opt-in model doesn't bypass authentication. Users must still be authenticated (unless you use `AllowAny`).

2. **Explicit is Better**: It's better to explicitly define permissions for all sensitive actions rather than relying on the opt-in model.

3. **Regular Reviews**: Periodically review your ViewSets to ensure all sensitive actions are protected.

4. **Documentation**: Document which actions are intentionally public and why.

### When to Use Opt-In

✅ **Good Use Cases**:
- Public read endpoints
- Health check endpoints
- Public API endpoints
- Utility endpoints (not sensitive)

❌ **Avoid Using Opt-In For**:
- Data modification actions
- Sensitive operations (delete, update)
- Admin operations
- Financial transactions

## Testing

### Test Opt-In Behavior

```python
def test_unprotected_action_allowed():
    """Test that actions not in registry are allowed"""
    user = create_user()  # No special permissions
    client = APIClient()
    client.force_authenticate(user=user)
    
    # Action 'export_data' is NOT in UPR config
    response = client.get('/api/users/export_data/')
    assert response.status_code == 200  # Allowed

def test_protected_action_requires_permission():
    """Test that actions in registry require permission"""
    user = create_user()  # No special permissions
    client = APIClient()
    client.force_authenticate(user=user)
    
    # Action 'reset_password' IS in UPR config
    response = client.post('/api/users/1/reset_password/')
    assert response.status_code == 403  # Denied (no permission)
    
    # Grant permission
    grant_permission(user, 'users.reset_password')
    response = client.post('/api/users/1/reset_password/')
    assert response.status_code == 200  # Allowed
```

## Summary

The opt-in permission model provides flexibility and gradual adoption:

- **Actions not in UPR config** → Allowed (authenticated users)
- **Actions in UPR config** → Require permission
- **No module assigned** → Allowed (skip permission checking)

This allows you to:
- Start using UPR without defining every permission
- Have public actions alongside protected ones
- Gradually expand permission coverage
- Maintain flexibility in your permission strategy
