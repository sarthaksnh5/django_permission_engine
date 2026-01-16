# Performance & Scalability

## Overview

UPR is designed to handle permission systems at scale - from small applications with dozens of permissions to enterprise systems with thousands of permissions and millions of users.

## Performance Characteristics

### Runtime Permission Checks

**Complexity**: O(1) - Constant time

**Implementation**:
```python
def check_permission(user, permission_key):
    # O(1) set lookup
    user_permissions = get_user_permissions(user)  # Cached
    return permission_key in user_permissions  # O(1)
```

**Performance**:
- Single set lookup
- No database queries (with caching)
- Sub-millisecond response time

### Permission Loading

**Initial Load**: O(n) where n = number of user permissions

**Cached Load**: O(1) - Cache hit

**Implementation**:
```python
def get_user_permissions(user):
    cache_key = f'user_permissions:{user.id}'
    permissions = cache.get(cache_key)
    if permissions is None:
        # O(n) database query
        permissions = set(
            UserPermission.objects
            .filter(user=user)
            .values_list('permission__key', flat=True)
        )
        cache.set(cache_key, permissions, timeout=3600)
    return permissions  # O(1) subsequent calls
```

## Scalability Targets

### Permission Count

- **Small**: 10-100 permissions
- **Medium**: 100-1,000 permissions
- **Large**: 1,000-10,000 permissions
- **Enterprise**: 10,000+ permissions

### User Count

- **Small**: 10-1,000 users
- **Medium**: 1,000-100,000 users
- **Large**: 100,000-1,000,000 users
- **Enterprise**: 1,000,000+ users

### Performance Targets

- **Permission Check**: < 1ms (with cache)
- **User Permission Load**: < 10ms (first load), < 0.1ms (cached)
- **Catalog API Response**: < 100ms (with cache)
- **Registry Sync**: < 5s for 1,000 permissions

## Caching Strategy

### User Permission Caching

```python
from django.core.cache import cache

def get_user_permissions(user):
    cache_key = f'user_permissions:{user.id}'
    permissions = cache.get(cache_key)
    
    if permissions is None:
        # Load from database
        permissions = load_permissions_from_db(user)
        # Cache for 1 hour
        cache.set(cache_key, permissions, timeout=3600)
    
    return permissions
```

**Cache Key**: `user_permissions:{user_id}`

**Cache Duration**: 1 hour (configurable)

**Invalidation**: On permission assignment changes

### Permission Key Caching

```python
def get_permission_key(module, capability):
    cache_key = f'permission_key:{module}:{capability}'
    key = cache.get(cache_key)
    
    if key is None:
        key = f"{module}.{capability}"
        # Cache for 24 hours (permission keys are immutable)
        cache.set(cache_key, key, timeout=86400)
    
    return key
```

**Cache Key**: `permission_key:{module}:{capability}`

**Cache Duration**: 24 hours (keys are immutable)

### Catalog API Caching

```python
def get_catalog():
    cache_key = 'permission_catalog'
    catalog = cache.get(cache_key)
    
    if catalog is None:
        catalog = build_catalog()
        # Cache for 1 hour
        cache.set(cache_key, catalog, timeout=3600)
    
    return catalog
```

**Cache Key**: `permission_catalog`

**Cache Duration**: 1 hour

**Invalidation**: On permission changes

## Cache Invalidation

### User Permission Invalidation

```python
from django.db.models.signals import post_save, post_delete

@receiver(post_save, sender=UserPermission)
@receiver(post_delete, sender=UserPermission)
def invalidate_user_cache(sender, instance, **kwargs):
    cache.delete(f'user_permissions:{instance.user.id}')
```

### Permission Invalidation

```python
@receiver(post_save, sender=Permission)
@receiver(post_delete, sender=Permission)
def invalidate_permission_cache(sender, instance, **kwargs):
    # Invalidate catalog
    cache.delete('permission_catalog')
    
    # Invalidate permission key cache
    cache.delete(f'permission_key:{instance.module}:{instance.capability}')
```

## Database Optimization

### Indexing Strategy

```python
class Permission(models.Model):
    key = models.CharField(max_length=255, unique=True, db_index=True)
    module = models.CharField(max_length=100, db_index=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['module']),
            models.Index(fields=['key']),
            models.Index(fields=['module', 'capability']),
        ]
```

**Indexes**:
- `key`: For permission lookups
- `module`: For module filtering
- `(module, capability)`: For composite queries

### Query Optimization

```python
# ✅ Good: Single query with select_related
permissions = Permission.objects.select_related('module').filter(module='users')

# ❌ Bad: N+1 queries
permissions = Permission.objects.filter(module='users')
for p in permissions:
    module = p.module  # Additional query per permission
```

### Bulk Operations

```python
# ✅ Good: Bulk permission lookup
permission_keys = ['users.view', 'users.create', 'orders.view']
permissions = Permission.objects.filter(key__in=permission_keys)

# ❌ Bad: Individual lookups
permissions = [
    Permission.objects.get(key=k) for k in permission_keys
]  # N queries
```

## Registry Performance

### Batch Processing

```python
def sync_permissions(self, definitions):
    # Batch create
    Permission.objects.bulk_create(
        [Permission(**def) for def in definitions['create']],
        ignore_conflicts=True
    )
    
    # Batch update
    Permission.objects.bulk_update(
        [Permission(**def) for def in definitions['update']],
        fields=['label', 'description', 'is_active', 'is_deprecated']
    )
```

### Transaction Management

```python
from django.db import transaction

@transaction.atomic
def sync_permissions(self, definitions):
    # All operations in single transaction
    # Rollback on error
    ...
```

## API Performance

### Pagination

For large permission catalogs:

```python
class PermissionCatalogViewSet(viewsets.ViewSet):
    pagination_class = PageNumberPagination
    
    def catalog(self, request):
        queryset = Permission.objects.all()
        page = self.paginate_queryset(queryset)
        return self.get_paginated_response(page)
```

### Field Selection

```python
# ✅ Good: Select only needed fields
permissions = Permission.objects.only('key', 'label', 'module')

# ❌ Bad: Load all fields
permissions = Permission.objects.all()
```

### Response Compression

```python
# Enable gzip compression in Django
MIDDLEWARE = [
    'django.middleware.gzip.GZipMiddleware',
    ...
]
```

## Monitoring

### Key Metrics

**Permission Check Latency**:
```python
import time

def check_permission(user, permission_key):
    start = time.time()
    result = _check_permission(user, permission_key)
    latency = time.time() - start
    
    # Log if slow
    if latency > 0.001:  # 1ms
        logger.warning(f"Slow permission check: {latency}s")
    
    return result
```

**Cache Hit Rate**:
```python
cache_hits = 0
cache_misses = 0

def get_user_permissions(user):
    global cache_hits, cache_misses
    
    cache_key = f'user_permissions:{user.id}'
    permissions = cache.get(cache_key)
    
    if permissions is None:
        cache_misses += 1
        permissions = load_permissions_from_db(user)
        cache.set(cache_key, permissions)
    else:
        cache_hits += 1
    
    return permissions
```

**Database Query Count**:
```python
from django.db import connection

def check_permission(user, permission_key):
    queries_before = len(connection.queries)
    result = _check_permission(user, permission_key)
    queries_after = len(connection.queries)
    
    if queries_after > queries_before:
        logger.warning("Permission check triggered database query")
    
    return result
```

## Performance Testing

### Load Testing

```python
def test_permission_check_performance():
    user = create_user_with_permissions(100)  # 100 permissions
    
    start = time.time()
    for _ in range(1000):
        check_permission(user, 'users.view')
    elapsed = time.time() - start
    
    # Should be < 1 second for 1000 checks
    assert elapsed < 1.0
    assert elapsed / 1000 < 0.001  # < 1ms per check
```

### Scalability Testing

```python
def test_scalability():
    # Test with different permission counts
    for count in [10, 100, 1000, 10000]:
        user = create_user_with_permissions(count)
        
        start = time.time()
        check_permission(user, 'users.view')
        elapsed = time.time() - start
        
        # Should be O(1) - constant time
        assert elapsed < 0.001  # < 1ms regardless of count
```

## Best Practices

### 1. Always Use Caching

```python
# ✅ Good: Cached permissions
permissions = get_user_permissions(user)  # Cached

# ❌ Bad: Database query every time
permissions = UserPermission.objects.filter(user=user)
```

### 2. Batch Permission Checks

```python
# ✅ Good: Batch check
permission_keys = ['users.view', 'users.create', 'orders.view']
has_permissions = {
    key: key in user_permissions 
    for key in permission_keys
}

# ❌ Bad: Individual checks
has_view = check_permission(user, 'users.view')
has_create = check_permission(user, 'users.create')
```

### 3. Use Database Indexes

```python
# ✅ Good: Indexed fields
Permission.objects.filter(key='users.view')  # Uses index

# ❌ Bad: Non-indexed queries
Permission.objects.filter(description__icontains='user')  # Full table scan
```

### 4. Monitor Performance

```python
# ✅ Good: Monitor and log
logger.info(f"Permission check: {latency}ms")

# ❌ Bad: No monitoring
# No visibility into performance issues
```

### 5. Optimize Hot Paths

```python
# ✅ Good: Optimize frequently called code
@lru_cache(maxsize=1000)
def get_permission_key(module, capability):
    return f"{module}.{capability}"

# ❌ Bad: No optimization
def get_permission_key(module, capability):
    return f"{module}.{capability}"  # Called thousands of times
```

## Summary

UPR is designed for performance:

- ✅ **O(1) permission checks** with caching
- ✅ **Scalable to thousands of permissions**
- ✅ **Efficient database queries** with proper indexing
- ✅ **Caching at multiple levels** for optimal performance
- ✅ **Batch operations** for registry sync
- ✅ **Monitoring and optimization** built-in

The system is designed to handle enterprise-scale permission systems while maintaining sub-millisecond response times for permission checks.
