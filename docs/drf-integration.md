# DRF Integration

## Overview

UPR integrates seamlessly with Django REST Framework (DRF) to provide automatic permission enforcement based on ViewSet actions and HTTP methods.

## Integration Model

### ViewSet Responsibilities

Each ViewSet must:
1. **Declare its module identity** - Which module it belongs to
2. **Not declare permissions manually** - Permissions are inferred automatically

### Action Awareness

- DRF actions automatically map to permissions
- CRUD actions are normalized to standard capabilities
- Custom actions are matched by name

## Basic Integration

### Simple ViewSet

```python
from rest_framework import viewsets
from upr.permissions import PermissionRequired

class UserViewSet(viewsets.ModelViewSet):
    permission_classes = [PermissionRequired]
    module = 'users'  # Required: Declare module
    queryset = User.objects.all()
    serializer_class = UserSerializer
```

This automatically enforces:
- `users.view` for GET requests (list, retrieve)
- `users.create` for POST requests
- `users.update` for PUT/PATCH requests
- `users.delete` for DELETE requests

### ViewSet with Custom Actions

```python
class UserViewSet(viewsets.ModelViewSet):
    permission_classes = [PermissionRequired]
    module = 'users'
    queryset = User.objects.all()
    serializer_class = UserSerializer
    
    @action(detail=True, methods=['post'])
    def reset_password(self, request, pk=None):
        # Automatically requires 'users.reset_password' permission
        user = self.get_object()
        # ... reset password logic ...
        return Response({'status': 'password reset'})
    
    @action(detail=False, methods=['get'])
    def export_data(self, request):
        # Automatically requires 'users.export_data' permission
        # ... export logic ...
        return Response({'data': ...})
```

## Permission Mapping

### Standard CRUD Mapping

| DRF Action | HTTP Method | Permission Key |
|------------|-------------|----------------|
| `list` | GET | `<module>.view` |
| `retrieve` | GET | `<module>.view` |
| `create` | POST | `<module>.create` |
| `update` | PUT | `<module>.update` |
| `partial_update` | PATCH | `<module>.update` |
| `destroy` | DELETE | `<module>.delete` |

### Custom Action Mapping

| DRF Action | HTTP Method | Permission Key |
|------------|-------------|----------------|
| `reset_password` | POST | `<module>.reset_password` |
| `export_data` | GET | `<module>.export_data` |
| `bulk_delete` | POST | `<module>.bulk_delete` |

**Rule**: Custom action name = capability name

## Module Declaration

### Required: Module Attribute

Every ViewSet must declare its module:

```python
class UserViewSet(viewsets.ModelViewSet):
    module = 'users'  # Required
    ...
```

### Module Inheritance

Modules can be inherited from base classes:

```python
class BaseUserViewSet(viewsets.ModelViewSet):
    module = 'users'

class UserViewSet(BaseUserViewSet):
    # Inherits module = 'users'
    ...
```

### Dynamic Module (Advanced)

For complex scenarios, you can override module detection:

```python
class UserViewSet(viewsets.ModelViewSet):
    def get_module(self):
        # Dynamic module based on context
        if self.request.user.is_staff:
            return 'admin.users'
        return 'users'
```

## Action Detection

### Automatic Action Detection

The permission class automatically detects actions:

```python
class PermissionRequired(BasePermission):
    def has_permission(self, request, view):
        # Get action from view
        action = getattr(view, 'action', None)
        
        # If no action, infer from HTTP method
        if action is None:
            action = self.infer_action(view, request)
        
        # Resolve permission
        return self.resolve_permission(request.user, view, action)
```

### Action Inference

When action is not explicitly set:

```python
def infer_action(self, view, request):
    method = request.method
    has_pk = 'pk' in view.kwargs
    
    if method == 'GET':
        return 'retrieve' if has_pk else 'list'
    elif method == 'POST':
        return 'create'
    elif method in ['PUT', 'PATCH']:
        return 'update'
    elif method == 'DELETE':
        return 'destroy'
    return 'list'
```

## Custom Permission Classes

### Extending PermissionRequired

```python
from upr.permissions import PermissionRequired

class CustomPermissionRequired(PermissionRequired):
    def has_permission(self, request, view):
        # Custom logic before standard check
        if request.user.is_superuser:
            return True
        
        # Standard permission check
        return super().has_permission(request, view)
```

### Combining with Other Permissions

```python
from rest_framework.permissions import IsAuthenticated
from upr.permissions import PermissionRequired

class UserViewSet(viewsets.ModelViewSet):
    permission_classes = [
        IsAuthenticated,  # First: Check authentication
        PermissionRequired,  # Then: Check permissions
    ]
    module = 'users'
```

### Conditional Permissions

```python
class UserViewSet(viewsets.ModelViewSet):
    def get_permissions(self):
        if self.action == 'list':
            # Public list view
            return [AllowAny()]
        else:
            # Protected actions
            return [PermissionRequired()]
    
    module = 'users'
```

## ViewSet Patterns

### Pattern 1: Standard CRUD

```python
class OrderViewSet(viewsets.ModelViewSet):
    permission_classes = [PermissionRequired]
    module = 'orders'
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
```

**Permissions Required**:
- `orders.view`
- `orders.create`
- `orders.update`
- `orders.delete`

### Pattern 2: Read-Only ViewSet

```python
class ReportViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [PermissionRequired]
    module = 'reports'
    queryset = Report.objects.all()
    serializer_class = ReportSerializer
```

**Permissions Required**:
- `reports.view` (only)

### Pattern 3: Custom Actions Only

```python
class SystemViewSet(viewsets.ViewSet):
    permission_classes = [PermissionRequired]
    module = 'system'
    
    @action(detail=False, methods=['post'])
    def restart(self, request):
        # Requires 'system.restart'
        ...
    
    @action(detail=False, methods=['post'])
    def backup(self, request):
        # Requires 'system.backup'
        ...
```

### Pattern 4: Mixed Permissions

```python
class UserViewSet(viewsets.ModelViewSet):
    permission_classes = [PermissionRequired]
    module = 'users'
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            # Public read access
            return []
        return [PermissionRequired()]
    
    @action(detail=True, methods=['post'])
    def reset_password(self, request, pk=None):
        # Still requires 'users.reset_password'
        ...
```

## Action Naming Conventions

### Matching Permission Names

Action names must match permission capability names:

```python
# ✅ Good: Action matches permission
@registry.module('users')
class UsersModule:
    actions = ['reset_password']

@action(detail=True, methods=['post'])
def reset_password(self, request, pk=None):
    # Matches 'users.reset_password'
    ...

# ❌ Bad: Mismatched names
@registry.module('users')
class UsersModule:
    actions = ['reset_password']

@action(detail=True, methods=['post'], name='reset-password')
def reset_password(self, request, pk=None):
    # Action name is 'reset-password' but permission is 'users.reset_password'
    # This will fail!
```

### Naming Best Practices

1. **Use underscores**: `reset_password` not `reset-password`
2. **Be consistent**: Match permission definition exactly
3. **Use descriptive names**: `bulk_delete` not `bulk_del`
4. **Follow DRF conventions**: Lowercase with underscores

## Error Responses

### Permission Denied Response

When permission is denied:

```json
{
    "detail": "You do not have permission to perform this action."
}
```

Status code: `403 Forbidden`

### Custom Error Messages

```python
class PermissionRequired(BasePermission):
    def has_permission(self, request, view):
        if not self.check_permission(request.user, view):
            raise PermissionDenied(
                detail=f"Permission required: {self.get_required_permission(view)}"
            )
        return True
```

## Testing DRF Integration

### Testing ViewSet Permissions

```python
from rest_framework.test import APIClient

def test_user_list_permission():
    user = create_user_with_permission('users.view')
    client = APIClient()
    client.force_authenticate(user=user)
    
    response = client.get('/api/users/')
    assert response.status_code == 200

def test_user_create_permission_denied():
    user = create_user_without_permission('users.create')
    client = APIClient()
    client.force_authenticate(user=user)
    
    response = client.post('/api/users/', {'name': 'Test'})
    assert response.status_code == 403

def test_custom_action_permission():
    user = create_user_with_permission('users.reset_password')
    client = APIClient()
    client.force_authenticate(user=user)
    
    response = client.post('/api/users/1/reset_password/')
    assert response.status_code == 200
```

### Testing Action Detection

```python
def test_action_detection():
    viewset = UserViewSet()
    viewset.action = 'list'
    
    permission_class = PermissionRequired()
    # Test that 'list' maps to 'view'
    ...
```

## Advanced Scenarios

### Multiple Modules in One ViewSet

```python
class UserViewSet(viewsets.ModelViewSet):
    permission_classes = [PermissionRequired]
    
    def get_module(self):
        # Different module based on action
        if self.action == 'admin_list':
            return 'admin.users'
        return 'users'
    
    @action(detail=False, methods=['get'])
    def admin_list(self, request):
        # Requires 'admin.users.view'
        ...
```

### Object-Level Permissions

```python
class PermissionRequired(BasePermission):
    def has_permission(self, request, view):
        # Standard permission check
        return self.check_module_permission(request.user, view)
    
    def has_object_permission(self, request, view, obj):
        # Object-level check (optional extension)
        if hasattr(obj, 'user') and obj.user == request.user:
            return True
        return self.has_permission(request, view)
```

### Context-Aware Permissions

```python
class UserViewSet(viewsets.ModelViewSet):
    permission_classes = [PermissionRequired]
    module = 'users'
    
    def get_permissions(self):
        # Adjust permissions based on context
        if self.request.user.is_staff:
            # Staff can do everything
            return []
        return [PermissionRequired()]
```

## Best Practices

### 1. Always Declare Module

```python
# ✅ Good
class UserViewSet(viewsets.ModelViewSet):
    module = 'users'

# ❌ Bad
class UserViewSet(viewsets.ModelViewSet):
    # No module = deny all requests
```

### 2. Match Action Names

```python
# ✅ Good: Action matches permission
@action(detail=True, methods=['post'])
def reset_password(self, request, pk=None):
    # Permission: 'users.reset_password'
    ...

# ❌ Bad: Mismatched names
@action(detail=True, methods=['post'], name='reset-password')
def reset_password(self, request, pk=None):
    # Permission: 'users.reset_password'
    # Action name: 'reset-password'
    # Mismatch!
```

### 3. Use Permission Classes Consistently

```python
# ✅ Good: Consistent across ViewSets
class UserViewSet(viewsets.ModelViewSet):
    permission_classes = [PermissionRequired]
    module = 'users'

class OrderViewSet(viewsets.ModelViewSet):
    permission_classes = [PermissionRequired]
    module = 'orders'

# ❌ Bad: Inconsistent
class UserViewSet(viewsets.ModelViewSet):
    permission_classes = [PermissionRequired]
    module = 'users'

class OrderViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]  # Different!
    module = 'orders'
```

### 4. Test Permission Enforcement

```python
# ✅ Good: Test permissions
def test_permission_enforcement():
    user = create_user_without_permission('users.create')
    response = client.post('/api/users/', data={...})
    assert response.status_code == 403

# ❌ Bad: No permission tests
```

### 5. Document Custom Actions

```python
# ✅ Good: Document permission requirement
@action(
    detail=True,
    methods=['post'],
    permission_required='users.reset_password'  # Documented
)
def reset_password(self, request, pk=None):
    """Reset user password. Requires 'users.reset_password' permission."""
    ...
```
