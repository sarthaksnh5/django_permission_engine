# Security Model

## Overview

UPR is built with security as a fundamental principle. The system provides strong security guarantees and follows security best practices.

## Security Guarantees

### 1. Deny by Default

**Principle**: If a permission is not explicitly granted, access is denied.

**Implementation**:
```python
def check_permission(user, permission_key):
    user_permissions = get_user_permissions(user)
    
    # Default to deny
    if permission_key not in user_permissions:
        return False  # Deny
    
    return True  # Allow only if explicitly granted
```

**Implications**:
- No implicit permissions
- No inheritance unless explicitly configured
- No default access
- Secure by default

### 2. Explicit Allow Only

**Principle**: Permissions must be explicitly assigned. No automatic or implicit grants.

**Implementation**:
```python
# ✅ Good: Explicit assignment
user.assign_permission('users.view')

# ❌ Bad: Implicit grants
# No automatic permissions based on role, group, etc.
# (Unless explicitly configured in your application)
```

**Implications**:
- Clear permission model
- Auditable permission assignments
- No surprise permissions

### 3. Immutable Permission Definitions

**Principle**: Permission keys cannot be changed once created.

**Implementation**:
```python
class Permission(models.Model):
    key = models.CharField(max_length=255, unique=True)
    
    def save(self, *args, **kwargs):
        if self.pk:  # Updating existing
            # Permission keys are immutable
            original = Permission.objects.get(pk=self.pk)
            if self.key != original.key:
                raise ValidationError("Permission keys cannot be changed")
        super().save(*args, **kwargs)
```

**Implications**:
- No permission key tampering
- Stable permission references
- Predictable behavior

### 4. No Implicit Access

**Principle**: No access is granted implicitly. All access must be through explicit permissions.

**Implementation**:
```python
# ✅ Good: Explicit permission check
if check_permission(user, 'users.view'):
    return data

# ❌ Bad: Implicit access
if user.is_staff:  # Not a permission check!
    return data
```

## Permission Key Security

### Validation

Permission keys are validated for security:

```python
def validate_permission_key(key):
    # Must match format
    if '.' not in key:
        raise ValidationError("Invalid permission key format")
    
    module, capability = key.split('.', 1)
    
    # Must be valid identifiers
    if not re.match(r'^[a-z0-9_]+$', key):
        raise ValidationError("Permission key contains invalid characters")
    
    # No SQL injection risk
    # No path traversal risk
    # No code injection risk
```

### Sanitization

Permission keys are sanitized:

```python
def sanitize_permission_key(key):
    # Lowercase
    key = key.lower()
    
    # Remove invalid characters
    key = re.sub(r'[^a-z0-9_.]', '', key)
    
    # Validate format
    if '.' not in key:
        raise ValidationError("Invalid permission key")
    
    return key
```

## Runtime Security

### No Permission Escalation

Users cannot grant themselves permissions:

```python
# ✅ Good: Permissions assigned through proper channels
admin.assign_permission(user, 'users.view')

# ❌ Bad: User cannot self-assign
# (Not possible through UPR - must be through your application logic)
```

### Secure Permission Checks

Permission checks are secure:

```python
def check_permission(user, permission_key):
    # Validate user
    if not user or not user.is_authenticated:
        return False
    
    # Validate permission key
    if not is_valid_permission_key(permission_key):
        logger.warning(f"Invalid permission key: {permission_key}")
        return False  # Deny on invalid key
    
    # Check permission
    user_permissions = get_user_permissions(user)
    return permission_key in user_permissions
```

### Error Handling

Errors default to deny:

```python
def check_permission(user, permission_key):
    try:
        return _check_permission(user, permission_key)
    except Exception as e:
        # Log error but deny access
        logger.error(f"Permission check error: {e}")
        return False  # Deny on error
```

## Database Security

### No Manual Edits

Permissions should not be manually edited:

```python
# ✅ Good: Through registry
@registry.module('users')
class UsersModule:
    crud = ['view']

# ❌ Bad: Manual database edits
Permission.objects.create(key='users.view')  # Not recommended
```

### Transaction Safety

Permission operations are transactional:

```python
@transaction.atomic
def assign_permission(user, permission_key):
    # All or nothing
    UserPermission.objects.create(user=user, permission_key=permission_key)
    invalidate_user_cache(user)
```

## API Security

### Authentication Required

Catalog API requires authentication:

```python
class PermissionCatalogViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    # Or more restrictive:
    # permission_classes = [IsAdminUser]
```

### Rate Limiting

API endpoints are rate limited:

```python
from rest_framework.throttling import UserRateThrottle

class CatalogThrottle(UserRateThrottle):
    rate = '100/hour'

class PermissionCatalogViewSet(viewsets.ViewSet):
    throttle_classes = [CatalogThrottle]
```

### Input Validation

All inputs are validated:

```python
def get_permission(request, permission_key):
    # Validate permission key format
    if not is_valid_permission_key(permission_key):
        raise ValidationError("Invalid permission key")
    
    # Check permission exists
    try:
        permission = Permission.objects.get(key=permission_key)
    except Permission.DoesNotExist:
        raise NotFound("Permission not found")
    
    return permission
```

## Registry Security

### No Runtime Permission Creation

Permissions cannot be created at runtime:

```python
# ✅ Good: Permissions defined in code
@registry.module('users')
class UsersModule:
    crud = ['view']

# ❌ Bad: Runtime creation (not supported)
# Permission.objects.create(key='users.view')  # Not allowed
```

### Validation of All Permissions

All permissions are validated:

```python
def validate_permissions(self):
    errors = []
    
    for permission in self.get_all_permissions():
        # Validate key format
        if not is_valid_permission_key(permission.key):
            errors.append(f"Invalid permission key: {permission.key}")
        
        # Validate module exists
        if not self.module_exists(permission.module):
            errors.append(f"Module not found: {permission.module}")
    
    if errors:
        raise ValidationError("\n".join(errors))
```

## Best Practices

### 1. Always Validate Permission Keys

```python
# ✅ Good: Validate before use
if is_valid_permission_key(permission_key):
    check_permission(user, permission_key)

# ❌ Bad: Trust user input
check_permission(user, request.GET['permission'])  # XSS risk!
```

### 2. Use Parameterized Queries

```python
# ✅ Good: Parameterized query
Permission.objects.filter(key=permission_key)

# ❌ Bad: String formatting (SQL injection risk)
Permission.objects.extra(where=[f"key = '{permission_key}'"])
```

### 3. Log Permission Denials

```python
# ✅ Good: Log for auditing
if not check_permission(user, permission_key):
    logger.warning(f"Permission denied: {user} -> {permission_key}")
    return False

# ❌ Bad: Silent failures
if not check_permission(user, permission_key):
    return False  # No audit trail
```

### 4. Secure Permission Assignment

```python
# ✅ Good: Secure assignment endpoint
@require_admin
def assign_permission(request, user_id, permission_key):
    user = get_object_or_404(User, id=user_id)
    validate_permission_key(permission_key)
    user.assign_permission(permission_key)
    return Response({'status': 'ok'})

# ❌ Bad: Public assignment
def assign_permission(request, user_id, permission_key):
    user = User.objects.get(id=user_id)
    user.assign_permission(permission_key)  # Anyone can assign!
    return Response({'status': 'ok'})
```

### 5. Regular Security Audits

```python
# ✅ Good: Regular audits
def audit_permissions():
    # Check for orphaned permissions
    # Check for invalid assignments
    # Check for security issues
    ...

# ❌ Bad: No audits
# Security issues go undetected
```

## Threat Model

### Threats Mitigated

1. **Permission Escalation**: Users cannot grant themselves permissions
2. **SQL Injection**: Parameterized queries, input validation
3. **XSS**: Permission keys are validated and sanitized
4. **Path Traversal**: Permission keys use dot notation, not paths
5. **Code Injection**: Permission keys are strings, not code
6. **Unauthorized Access**: Deny by default, explicit allow only

### Threats Not Mitigated (Application Responsibility)

1. **Role Management**: Application must implement role assignment securely
2. **User Authentication**: Relies on Django's authentication
3. **Object-Level Permissions**: Not in scope (can be extended)
4. **Time-Based Permissions**: Not in scope (can be extended)

## Security Checklist

- [ ] Permission keys are validated
- [ ] Deny by default is enforced
- [ ] No implicit permissions
- [ ] Permission assignments are audited
- [ ] API endpoints are authenticated
- [ ] Rate limiting is enabled
- [ ] Errors default to deny
- [ ] Permission keys are immutable
- [ ] Database operations are transactional
- [ ] Cache invalidation is secure
- [ ] Logging is enabled for security events
- [ ] Regular security audits are performed

## Summary

UPR provides strong security guarantees:

- ✅ **Deny by default** - No implicit access
- ✅ **Explicit allow only** - Clear permission model
- ✅ **Immutable definitions** - No tampering
- ✅ **Input validation** - Secure against injection
- ✅ **Error handling** - Secure defaults
- ✅ **Audit logging** - Security visibility

The system is designed to be secure by default, with clear security boundaries and strong guarantees.
