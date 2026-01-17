# Runtime Permission Resolution

## Overview

Runtime Permission Resolution is the process of determining whether a user is allowed to perform a specific action at request time. This is the core functionality that enforces permissions in your application.

## Purpose

The runtime resolver answers one question efficiently:

> **"Is this user allowed to perform this request?"**

## Resolution Flow

### High-Level Flow

```
HTTP Request
    ↓
DRF ViewSet identified
    ↓
Module extracted from ViewSet
    ↓
Action identified (from DRF)
    ↓
Permission key constructed
    ↓
User permissions checked
    ↓
Allow/Deny decision
```

### Detailed Flow

1. **Request arrives** at DRF endpoint
2. **ViewSet identified** from URL routing
3. **Module extracted** from ViewSet configuration
   - No module → Allow (skip permission checking)
4. **Action identified** from DRF action or HTTP method
5. **Action normalized** (CRUD or custom)
6. **Permission key constructed** (`<module>.<capability>`)
7. **Check if permission exists in registry**
   - Not in registry → Allow (opt-in model)
   - In registry → Continue
8. **User permissions loaded** (cached)
9. **Permission key checked** in user's permission set
10. **Decision returned** (allow or deny)

## Inputs

### Required Inputs

**Authenticated User**
- The user making the request
- Must be authenticated (Django user object)

**DRF ViewSet**
- The ViewSet handling the request
- Must declare its module

**DRF Action**
- The specific action being performed
- Can be standard CRUD or custom action

**HTTP Method**
- GET, POST, PUT, PATCH, DELETE
- Used for CRUD normalization

## Resolution Steps

### Step 1: Identify Module

```python
class UserViewSet(viewsets.ModelViewSet):
    module = 'users'  # Declared in ViewSet
    ...
```

The resolver extracts the module from the ViewSet:

```python
def get_module(viewset):
    return getattr(viewset, 'module', None)
```

### Step 2: Identify Action

#### Standard CRUD Actions

```python
# HTTP method → action mapping
GET /users/          → 'list'   → 'view'
GET /users/1/        → 'retrieve' → 'view'
POST /users/         → 'create' → 'create'
PUT /users/1/        → 'update' → 'update'
PATCH /users/1/      → 'partial_update' → 'update'
DELETE /users/1/     → 'destroy' → 'delete'
```

#### Custom Actions

```python
# Custom action name → action
POST /users/1/reset_password/ → 'reset_password'
```

### Step 3: Normalize Action

```python
def normalize_action(action, http_method):
    # Standard CRUD mapping
    crud_map = {
        'list': 'view',
        'retrieve': 'view',
        'create': 'create',
        'update': 'update',
        'partial_update': 'update',
        'destroy': 'delete',
    }
    
    # Check if standard CRUD
    if action in crud_map:
        return crud_map[action]
    
    # Custom action (use as-is)
    return action
```

### Step 4: Construct Permission Key

```python
def construct_permission_key(module, capability):
    return f"{module}.{capability}"

# Examples:
# module='users', capability='view' → 'users.view'
# module='users', capability='reset_password' → 'users.reset_password'
```

### Step 5: Check if Permission Exists in Registry

```python
def permission_exists_in_registry(permission_key):
    """Check if permission is defined in UPR registry"""
    from django_permission_engine import get_registry
    registry = get_registry()
    return permission_key in registry.get_all_permission_keys()
```

**Important**: If the permission doesn't exist in the registry, the action is allowed (opt-in model).

### Step 6: Check User Permissions

```python
def check_permission(user, permission_key):
    # First check if permission exists in registry
    if not permission_exists_in_registry(permission_key):
        return True  # Not in registry = allow (opt-in model)
    
    # Get user's permissions (cached)
    user_permissions = get_user_permissions(user)
    
    # Check if permission key exists in user's permissions
    return permission_key in user_permissions
```

## Implementation

### Permission Resolver Class

```python
class PermissionResolver:
    def resolve(self, user, viewset, action, http_method):
        # Step 1: Get module
        module = self.get_module(viewset)
        if not module:
            return True  # No module = allow (skip permission checking)
        
        # Step 2: Normalize action
        capability = self.normalize_action(action, http_method)
        
        # Step 3: Construct key
        permission_key = self.construct_permission_key(module, capability)
        
        # Step 4: Check if permission exists in registry
        if not self.permission_exists_in_registry(permission_key):
            return True  # Not in registry = allow (opt-in model)
        
        # Step 5: Check permission
        return self.check_permission(user, permission_key)
    
    def permission_exists_in_registry(self, permission_key: str) -> bool:
        """Check if permission exists in UPR registry"""
        from django_permission_engine import get_registry
        registry = get_registry()
        return permission_key in registry.get_all_permission_keys()
    
    def get_module(self, viewset):
        return getattr(viewset, 'module', None)
    
    def normalize_action(self, action, http_method):
        crud_map = {
            'list': 'view',
            'retrieve': 'view',
            'create': 'create',
            'update': 'update',
            'partial_update': 'update',
            'destroy': 'delete',
        }
        return crud_map.get(action, action)
    
    def construct_permission_key(self, module, capability):
        return f"{module}.{capability}"
    
    def check_permission(self, user, permission_key):
        """Check if user has permission (assumes permission exists in registry)"""
        user_permissions = self.get_user_permissions(user)
        return permission_key in user_permissions
    
    def get_user_permissions(self, user):
        # Cached permission lookup
        cache_key = f'user_permissions:{user.id}'
        permissions = cache.get(cache_key)
        if permissions is None:
            permissions = self._load_user_permissions(user)
            cache.set(cache_key, permissions, timeout=3600)
        return permissions
    
    def _load_user_permissions(self, user):
        # Load from database or role system
        # Returns set of permission keys
        return set(user.permissions.values_list('key', flat=True))
```

## DRF Integration

### Permission Class

```python
from rest_framework.permissions import BasePermission

class PermissionRequired(BasePermission):
    resolver = PermissionResolver()
    
    def has_permission(self, request, view):
        # Deny if not authenticated
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Get action
        action = self.get_action(view, request)
        
        # Resolve permission
        return self.resolver.resolve(
            user=request.user,
            viewset=view,
            action=action,
            http_method=request.method
        )
    
    def get_action(self, view, request):
        # Get action from view
        if hasattr(view, 'action'):
            return view.action
        
        # Fallback to HTTP method mapping
        method_map = {
            'GET': 'list' if not view.kwargs.get('pk') else 'retrieve',
            'POST': 'create',
            'PUT': 'update',
            'PATCH': 'partial_update',
            'DELETE': 'destroy',
        }
        return method_map.get(request.method, 'list')
```

### Usage in ViewSet

```python
from upr.permissions import PermissionRequired

class UserViewSet(viewsets.ModelViewSet):
    permission_classes = [PermissionRequired]
    module = 'users'  # Required: Declare module
    queryset = User.objects.all()
    serializer_class = UserSerializer
    
    @action(detail=True, methods=['post'])
    def reset_password(self, request, pk=None):
        # Automatically requires 'users.reset_password' permission
        ...
```

## Performance Optimization

### Caching Strategy

```python
# Cache user permissions
def get_user_permissions(user):
    cache_key = f'user_permissions:{user.id}'
    permissions = cache.get(cache_key)
    if permissions is None:
        permissions = load_permissions_from_db(user)
        cache.set(cache_key, permissions, timeout=3600)
    return permissions

# Invalidate cache on permission changes
@receiver(post_save, sender=UserPermission)
def invalidate_user_cache(sender, instance, **kwargs):
    cache.delete(f'user_permissions:{instance.user.id}')
```

### Permission Key Caching

```python
# Cache permission key lookups
def get_permission_key(module, capability):
    cache_key = f'permission_key:{module}:{capability}'
    key = cache.get(cache_key)
    if key is None:
        key = f"{module}.{capability}"
        cache.set(cache_key, key, timeout=86400)  # 24 hours
    return key
```

### Bulk Permission Loading

```python
# Load all permissions for user at once
def get_user_permissions(user):
    # Single query instead of multiple
    return set(
        UserPermission.objects
        .filter(user=user)
        .values_list('permission__key', flat=True)
    )
```

## Error Handling

### Missing Module

```python
def resolve(self, user, viewset, action, http_method):
    module = self.get_module(viewset)
    if not module:
        # No module = allow (skip permission checking)
        return True
```

**Note**: ViewSets without a module are allowed to provide flexibility. If you want to enforce module declaration, you can override this behavior.

### Invalid Permission Key

```python
def check_permission(self, user, permission_key):
    # Validate key format
    if not self.is_valid_key(permission_key):
        logger.error(f"Invalid permission key: {permission_key}")
        return False
    
    return permission_key in self.get_user_permissions(user)
```

### Database Errors

```python
def get_user_permissions(self, user):
    try:
        return self._load_user_permissions(user)
    except DatabaseError as e:
        logger.error(f"Database error loading permissions: {e}")
        return set()  # Deny on error
```

## Security Guarantees

### Deny by Default

```python
def resolve(self, user, viewset, action, http_method):
    # Default to deny
    try:
        # ... resolution logic ...
        return has_permission
    except Exception:
        # Any error = deny
        return False
```

### No Permission Escalation

```python
# User cannot grant themselves permissions
# Permissions are only assigned through proper channels
# Runtime resolver only checks, never modifies
```

### Immutable Permission Keys

```python
# Permission keys are validated and immutable
# Cannot be manipulated at runtime
```

## Testing

### Unit Tests

```python
def test_resolve_view_permission():
    user = create_user_with_permission('users.view')
    viewset = UserViewSet()
    
    resolver = PermissionResolver()
    result = resolver.resolve(
        user=user,
        viewset=viewset,
        action='list',
        http_method='GET'
    )
    
    assert result is True
```

### Integration Tests

```python
def test_viewset_permission_enforcement():
    user = create_user_without_permission()
    client = APIClient()
    client.force_authenticate(user=user)
    
    response = client.get('/api/users/')
    assert response.status_code == 403
```

## Best Practices

### 1. Always Declare Module

```python
# ✅ Good
class UserViewSet(viewsets.ModelViewSet):
    module = 'users'

# ⚠️ Note: No module = allow all (skip permission checking)
# This is intentional for flexibility, but it's better to declare modules
class UserViewSet(viewsets.ModelViewSet):
    # No module = allow all (not recommended for production)
```

### 2. Use Consistent Action Names

```python
# ✅ Good: Action name matches permission
@action(detail=True, methods=['post'])
def reset_password(self, request, pk=None):
    # Requires 'users.reset_password'
    ...

# ❌ Bad: Mismatched names
@action(detail=True, methods=['post'], name='reset-password')
def reset_password(self, request, pk=None):
    # Action name is 'reset-password' but permission is 'users.reset_password'
    # This will fail!
```

### 3. Cache User Permissions

```python
# ✅ Good: Cache permissions
permissions = cache.get(f'user_permissions:{user.id}')

# ❌ Bad: Query database every time
permissions = UserPermission.objects.filter(user=user)
```

### 4. Handle Errors Gracefully

```python
# ✅ Good: Deny on error
try:
    return check_permission(user, key)
except Exception:
    return False

# ❌ Bad: Allow on error
try:
    return check_permission(user, key)
except Exception:
    return True  # Security risk!
```

### 5. Log Permission Denials

```python
# ✅ Good: Log for auditing
if not has_permission:
    logger.info(f"Permission denied: {user} -> {permission_key}")
    return False
```
