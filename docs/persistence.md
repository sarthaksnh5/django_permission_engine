# Persistence Layer

## Overview

The Persistence Layer stores permission data in the database. It's important to understand that **persistence is not authority** - the database stores state, but the code definitions are the source of truth.

## Purpose

The persistence layer:
- Stores permission data for efficient runtime access
- Provides a queryable interface for permission lookups
- Maintains metadata about permissions
- Supports permission assignment tracking

## Database Models

### Permission Model

The core model for storing permissions:

```python
class Permission(models.Model):
    # Core fields
    key = models.CharField(max_length=255, unique=True, db_index=True)
    module = models.CharField(max_length=100, db_index=True)
    capability = models.CharField(max_length=100)
    
    # Metadata
    label = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    is_deprecated = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'upr_permissions'
        indexes = [
            models.Index(fields=['module']),
            models.Index(fields=['key']),
        ]
    
    def __str__(self):
        return self.key
```

### Module Model (Optional)

For hierarchical module organization:

```python
class Module(models.Model):
    key = models.CharField(max_length=255, unique=True)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE)
    label = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    
    class Meta:
        db_table = 'upr_modules'
    
    def __str__(self):
        return self.key
```

## Field Descriptions

### Core Fields

**`key`** (required)
- Unique identifier for the permission
- Format: `<module>.<capability>`
- Immutable once created
- Indexed for fast lookups

**`module`** (required)
- Module name the permission belongs to
- Indexed for filtering
- Examples: `users`, `orders`, `breakdown.visit`

**`capability`** (required)
- The action or operation
- Examples: `view`, `create`, `reset_password`

### Metadata Fields

**`label`** (required)
- Human-readable name
- Displayed in UIs
- Example: "View Users", "Reset Password"

**`description`** (optional)
- Detailed explanation
- Help text in UIs
- Documentation

### Status Fields

**`is_active`** (default: True)
- Whether permission is active
- Inactive permissions are not assigned
- Soft delete mechanism

**`is_deprecated`** (default: False)
- Whether permission is deprecated
- Still valid but not recommended
- Migration path indicator

### Timestamp Fields

**`created_at`**
- When permission was created
- Auto-set on creation

**`updated_at`**
- When permission was last updated
- Auto-updated on changes

## Data Rules

### Immutability

Permission keys are **immutable**:
- Cannot be changed after creation
- Cannot be renamed
- Must be deleted and recreated (with migration)

### No Manual Editing

Permissions should **never** be manually edited:
- ❌ Don't create permissions via Django admin
- ❌ Don't edit permissions directly in database
- ❌ Don't use `Permission.objects.create()` in application code
- ✅ Always use the registry to create/update permissions

### Regenerability

The database should be **fully regenerable** from definitions:
- All permissions come from code definitions
- Database can be rebuilt from definitions
- No manual data required

## Query Patterns

### Get Permission by Key

```python
permission = Permission.objects.get(key='users.view')
```

### Get All Permissions for Module

```python
permissions = Permission.objects.filter(module='users')
```

### Get Active Permissions

```python
permissions = Permission.objects.filter(is_active=True)
```

### Get Deprecated Permissions

```python
permissions = Permission.objects.filter(is_deprecated=True)
```

### Get Permissions by Capability

```python
view_permissions = Permission.objects.filter(capability='view')
```

## Indexing Strategy

### Primary Indexes

```python
# Permission key (most common lookup)
Permission.objects.filter(key='users.view')

# Module (for filtering)
Permission.objects.filter(module='users')
```

### Composite Indexes

```python
# Module + Capability (for specific lookups)
Permission.objects.filter(module='users', capability='view')
```

## Migration Strategy

### Adding Permissions

```python
# Migration automatically created by registry
# No manual migration needed
python manage.py upr_sync
```

### Removing Permissions

```python
# 1. Mark as deprecated
permission.is_deprecated = True
permission.save()

# 2. Remove assignments
# (handled by application)

# 3. Remove from code
# (removed from definition)

# 4. Sync (removes from DB)
python manage.py upr_sync --clean-orphans
```

### Updating Metadata

```python
# Update label/description
# Changed in code definition
# Synced via registry
python manage.py upr_sync
```

## Performance Considerations

### Caching

Permission data is relatively static, making it ideal for caching:

```python
from django.core.cache import cache

def get_permission(key):
    cache_key = f'permission:{key}'
    permission = cache.get(cache_key)
    if permission is None:
        permission = Permission.objects.get(key=key)
        cache.set(cache_key, permission, timeout=3600)
    return permission
```

### Bulk Operations

For bulk permission lookups:

```python
# Efficient: Single query
permissions = Permission.objects.filter(
    key__in=['users.view', 'users.create', 'orders.view']
)

# Inefficient: Multiple queries
permissions = [
    Permission.objects.get(key=k) 
    for k in ['users.view', 'users.create', 'orders.view']
]
```

### Query Optimization

```python
# Use select_related for related data
permissions = Permission.objects.select_related('module').all()

# Use only() for specific fields
permissions = Permission.objects.only('key', 'label').all()
```

## Data Integrity

### Constraints

```python
class Permission(models.Model):
    # Unique constraint
    key = models.CharField(unique=True)
    
    # Check constraint (if supported)
    class Meta:
        constraints = [
            models.CheckConstraint(
                check=Q(key__contains='.'),
                name='key_contains_dot'
            )
        ]
```

### Validation

```python
def clean(self):
    # Validate key format
    if '.' not in self.key:
        raise ValidationError("Permission key must contain a dot")
    
    # Validate module matches key
    module, capability = self.key.split('.', 1)
    if self.module != module:
        raise ValidationError("Module must match key prefix")
```

## Backup and Recovery

### Backup Strategy

Permissions are critical data:
- Include in regular database backups
- Version control definitions (code)
- Backup before major syncs

### Recovery Strategy

If database is corrupted:
1. Restore from backup, or
2. Rebuild from code definitions:
   ```bash
   python manage.py upr_sync --force
   ```

## Monitoring

### Key Metrics

- Total permission count
- Active vs deprecated permissions
- Permissions per module
- Permission assignment counts

### Health Checks

```python
def check_permission_health():
    # Check for orphaned permissions
    defined_keys = set(registry.get_all_keys())
    db_keys = set(Permission.objects.values_list('key', flat=True))
    orphaned = db_keys - defined_keys
    
    if orphaned:
        return {
            'status': 'warning',
            'orphaned_count': len(orphaned)
        }
    
    return {'status': 'healthy'}
```

## Best Practices

### 1. Never Edit Manually

Always use the registry:
```python
# ❌ Don't do this
Permission.objects.create(key='users.view')

# ✅ Do this
@registry.module('users')
class UsersModule:
    crud = ['view']
# Then: python manage.py upr_sync
```

### 2. Use Transactions

Registry sync uses transactions:
```python
with transaction.atomic():
    # All or nothing
    registry.sync()
```

### 3. Monitor Changes

Track permission changes:
```python
# Use Django signals
@receiver(post_save, sender=Permission)
def log_permission_change(sender, instance, **kwargs):
    log_change('permission', instance.key, instance)
```

### 4. Regular Validation

Run validation regularly:
```bash
# In CI/CD
python manage.py upr_validate
```

### 5. Backup Before Sync

Always backup before major syncs:
```bash
# Backup database
python manage.py dumpdata upr > backup.json

# Run sync
python manage.py upr_sync
```
