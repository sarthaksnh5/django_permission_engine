# Roles & Users Strategy

## Overview

UPR manages **permissions**, not **assignments**. The library provides the permission infrastructure, while applications manage how permissions are assigned to users and roles.

## Core Library Stance

### What UPR Provides

- ✅ Permission definitions
- ✅ Permission registry
- ✅ Permission resolution
- ✅ Permission catalog API

### What UPR Does NOT Provide

- ❌ Role management system
- ❌ User-permission assignment UI
- ❌ Opinionated RBAC rules
- ❌ Permission inheritance

### What Applications Provide

- User-permission assignments
- Role-permission assignments
- Permission inheritance (if needed)
- UI for permission management

## Supported Patterns

### Pattern 1: Direct User Permissions

Users have permissions directly assigned:

```python
# Models
class User(AbstractUser):
    permissions = models.ManyToManyField(Permission, through='UserPermission')

class UserPermission(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE)
    granted_at = models.DateTimeField(auto_now_add=True)
```

**Usage**:
```python
# Assign permission
user.permissions.add(permission)

# Check permission
user.permissions.filter(key='users.view').exists()
```

### Pattern 2: Role-Based Permissions

Users have roles, roles have permissions:

```python
# Models
class Role(models.Model):
    name = models.CharField(max_length=100)
    permissions = models.ManyToManyField(Permission)

class User(AbstractUser):
    roles = models.ManyToManyField(Role)
```

**Usage**:
```python
# Assign role
user.roles.add(admin_role)

# Check permission (through role)
user.roles.filter(permissions__key='users.view').exists()
```

### Pattern 3: Hybrid (Roles + Direct)

Users can have both roles and direct permissions:

```python
def get_user_permissions(user):
    # From roles
    role_permissions = Permission.objects.filter(
        roles__users=user
    ).values_list('key', flat=True)
    
    # Direct permissions
    direct_permissions = user.permissions.values_list('key', flat=True)
    
    # Combine (direct permissions override role permissions)
    return set(role_permissions) | set(direct_permissions)
```

## Implementation Examples

### Simple User Permissions

```python
# models.py
from upr.models import Permission

class UserPermission(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE)
    granted_by = models.ForeignKey(User, related_name='granted_permissions')
    granted_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'permission']

# Usage
def assign_permission(user, permission_key, granted_by):
    permission = Permission.objects.get(key=permission_key)
    UserPermission.objects.get_or_create(
        user=user,
        permission=permission,
        defaults={'granted_by': granted_by}
    )

def check_permission(user, permission_key):
    return UserPermission.objects.filter(
        user=user,
        permission__key=permission_key
    ).exists()
```

### Role-Based System

```python
# models.py
class Role(models.Model):
    name = models.CharField(max_length=100, unique=True)
    permissions = models.ManyToManyField(Permission)
    description = models.TextField(blank=True)

class UserRole(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    assigned_at = models.DateTimeField(auto_now_add=True)
    assigned_by = models.ForeignKey(User, related_name='assigned_roles')

# Usage
def assign_role(user, role_name, assigned_by):
    role = Role.objects.get(name=role_name)
    UserRole.objects.get_or_create(
        user=user,
        role=role,
        defaults={'assigned_by': assigned_by}
    )

def get_user_permissions(user):
    return Permission.objects.filter(
        roles__userroles__user=user
    ).values_list('key', flat=True)
```

### Hybrid System

```python
def get_user_permissions(user):
    """Get all permissions for user (roles + direct)"""
    # From roles
    role_permissions = set(
        Permission.objects.filter(
            roles__userroles__user=user
        ).values_list('key', flat=True)
    )
    
    # Direct permissions
    direct_permissions = set(
        user.userpermissions.values_list('permission__key', flat=True)
    )
    
    # Direct permissions override role permissions
    return role_permissions | direct_permissions

def check_permission(user, permission_key):
    """Check if user has permission (roles or direct)"""
    return permission_key in get_user_permissions(user)
```

## Integration with UPR

### Permission Resolution

UPR's permission resolver can work with any assignment pattern:

```python
from upr.permissions import PermissionResolver

class CustomPermissionResolver(PermissionResolver):
    def get_user_permissions(self, user):
        # Implement your assignment pattern
        return get_user_permissions(user)  # Your implementation
```

### Permission Assignment API

Applications can build their own assignment APIs:

```python
# views.py
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

class UserPermissionViewSet(viewsets.ViewSet):
    permission_classes = [IsAdminUser]
    
    @action(detail=True, methods=['post'])
    def assign_permission(self, request, pk=None):
        user = get_object_or_404(User, pk=pk)
        permission_key = request.data.get('permission_key')
        
        # Validate permission exists
        permission = get_object_or_404(Permission, key=permission_key)
        
        # Assign
        UserPermission.objects.get_or_create(
            user=user,
            permission=permission,
            defaults={'granted_by': request.user}
        )
        
        return Response({'status': 'permission assigned'})
    
    @action(detail=True, methods=['delete'])
    def revoke_permission(self, request, pk=None):
        user = get_object_or_404(User, pk=pk)
        permission_key = request.data.get('permission_key')
        
        UserPermission.objects.filter(
            user=user,
            permission__key=permission_key
        ).delete()
        
        return Response({'status': 'permission revoked'})
```

## Best Practices

### 1. Use Consistent Assignment Patterns

```python
# ✅ Good: Consistent pattern
def assign_permission(user, permission_key):
    permission = Permission.objects.get(key=permission_key)
    UserPermission.objects.get_or_create(user=user, permission=permission)

# ❌ Bad: Inconsistent patterns
# Sometimes direct, sometimes through roles, sometimes through groups
```

### 2. Audit Permission Assignments

```python
# ✅ Good: Audit trail
class UserPermission(models.Model):
    user = models.ForeignKey(User)
    permission = models.ForeignKey(Permission)
    granted_by = models.ForeignKey(User, related_name='granted_permissions')
    granted_at = models.DateTimeField(auto_now_add=True)
    reason = models.TextField(blank=True)

# ❌ Bad: No audit trail
# No record of who granted what and when
```

### 3. Cache User Permissions

```python
# ✅ Good: Cache permissions
def get_user_permissions(user):
    cache_key = f'user_permissions:{user.id}'
    permissions = cache.get(cache_key)
    if permissions is None:
        permissions = load_user_permissions(user)
        cache.set(cache_key, permissions, timeout=3600)
    return permissions

# ❌ Bad: Query every time
# Performance issues with many permission checks
```

### 4. Validate Permission Existence

```python
# ✅ Good: Validate permission exists
def assign_permission(user, permission_key):
    try:
        permission = Permission.objects.get(key=permission_key)
    except Permission.DoesNotExist:
        raise ValidationError(f"Permission not found: {permission_key}")
    
    UserPermission.objects.get_or_create(user=user, permission=permission)

# ❌ Bad: Assume permission exists
# Can create invalid assignments
```

### 5. Provide Permission Management UI

```python
# ✅ Good: UI for permission management
# Admin interface for assigning permissions
# Role editor for managing role permissions
# User permission viewer

# ❌ Bad: Only programmatic assignment
# Difficult to manage permissions
```

## Common Patterns

### Pattern 1: Admin-Only Assignment

Only admins can assign permissions:

```python
class UserPermissionViewSet(viewsets.ViewSet):
    permission_classes = [IsAdminUser]
    
    @action(detail=True, methods=['post'])
    def assign_permission(self, request, pk=None):
        # Only admins can assign
        ...
```

### Pattern 2: Self-Service for Some Permissions

Users can request some permissions:

```python
class PermissionRequestViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def request_permission(self, request):
        permission_key = request.data.get('permission_key')
        
        # Check if user can request this permission
        if permission_key in SELF_SERVICE_PERMISSIONS:
            PermissionRequest.objects.create(
                user=request.user,
                permission_key=permission_key
            )
            return Response({'status': 'request submitted'})
        else:
            return Response(
                {'error': 'Permission cannot be self-requested'},
                status=403
            )
```

### Pattern 3: Time-Limited Permissions

Permissions expire after a period:

```python
class UserPermission(models.Model):
    user = models.ForeignKey(User)
    permission = models.ForeignKey(Permission)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    def is_valid(self):
        if self.expires_at:
            return timezone.now() < self.expires_at
        return True
```

## Summary

UPR provides the permission infrastructure, while applications manage assignments:

- ✅ **Flexible assignment patterns** - Direct, role-based, or hybrid
- ✅ **No opinionated RBAC** - Applications choose their model
- ✅ **Easy integration** - Works with any assignment pattern
- ✅ **Clear separation** - Permissions vs assignments
- ✅ **Extensible** - Can build complex assignment logic

Applications are free to implement the assignment model that fits their needs, while UPR provides the solid permission foundation.
