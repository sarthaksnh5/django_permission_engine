# Permission Catalog API

## Overview

The Permission Catalog API provides a frontend-ready, hierarchical representation of all permissions in your system. It's designed to be consumed by admin UIs, role editors, feature toggles, and auditing tools.

## Purpose

The catalog API:
- Exposes permissions in a structured, hierarchical format
- Provides metadata for each permission
- Enables frontend permission management
- Supports permission discovery and documentation
- Maintains consistency with backend permission logic

## Characteristics

### Read-Only
- The API is read-only
- No mutations through the API
- All changes go through the registry

### Declarative
- Reflects permission definitions exactly
- No computed or derived permissions
- Matches code definitions

### Hierarchical
- Organized by modules
- Supports nested module structures
- Easy to navigate

### Language-Agnostic
- JSON format
- No framework-specific concepts
- Works with any frontend

### Self-Describing
- Includes labels and descriptions
- Provides metadata
- Clear structure

## API Endpoints

### Get Full Catalog

```
GET /api/permissions/catalog/
```

Returns the complete permission catalog organized by modules.

### Get Module Permissions

```
GET /api/permissions/catalog/{module}/
```

Returns permissions for a specific module.

### Get Permission Details

```
GET /api/permissions/{permission_key}/
```

Returns detailed information about a specific permission.

## Response Format

### Full Catalog Response

```json
{
  "modules": [
    {
      "key": "users",
      "label": "User Management",
      "description": "Manage application users",
      "permissions": [
        {
          "key": "users.view",
          "label": "View Users",
          "description": "View and list users",
          "capability": "view",
          "type": "crud",
          "is_active": true,
          "is_deprecated": false
        },
        {
          "key": "users.create",
          "label": "Create Users",
          "description": "Create new users",
          "capability": "create",
          "type": "crud",
          "is_active": true,
          "is_deprecated": false
        },
        {
          "key": "users.reset_password",
          "label": "Reset Password",
          "description": "Reset user passwords",
          "capability": "reset_password",
          "type": "action",
          "is_active": true,
          "is_deprecated": false
        }
      ],
      "submodules": []
    },
    {
      "key": "orders",
      "label": "Order Management",
      "permissions": [...],
      "submodules": []
    }
  ],
  "total_permissions": 52,
  "total_modules": 8
}
```

### Module Response

```json
{
  "key": "users",
  "label": "User Management",
  "description": "Manage application users",
  "permissions": [
    {
      "key": "users.view",
      "label": "View Users",
      "capability": "view",
      "type": "crud"
    },
    ...
  ],
  "submodules": []
}
```

### Permission Details Response

```json
{
  "key": "users.reset_password",
  "module": "users",
  "capability": "reset_password",
  "label": "Reset Password",
  "description": "Allows resetting user passwords",
  "type": "action",
  "is_active": true,
  "is_deprecated": false,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-20T14:45:00Z"
}
```

## Response Fields

### Module Fields

**`key`** (string, required)
- Module identifier
- Example: `"users"`, `"breakdown.visit"`

**`label`** (string, required)
- Human-readable module name
- Example: `"User Management"`

**`description`** (string, optional)
- Module description
- Example: `"Manage application users"`

**`permissions`** (array, required)
- List of permissions in this module
- See Permission Fields below

**`submodules`** (array, optional)
- Nested modules (for hierarchical structures)
- Same structure as modules

### Permission Fields

**`key`** (string, required)
- Permission identifier
- Format: `<module>.<capability>`
- Example: `"users.view"`

**`module`** (string, required)
- Module this permission belongs to
- Example: `"users"`

**`capability`** (string, required)
- The action or operation
- Example: `"view"`, `"reset_password"`

**`label`** (string, required)
- Human-readable permission name
- Example: `"View Users"`

**`description`** (string, optional)
- Detailed permission description
- Example: `"View and list users"`

**`type`** (string, required)
- Permission type: `"crud"` or `"action"`
- Indicates if it's a standard CRUD or custom action

**`is_active`** (boolean, required)
- Whether permission is active
- Inactive permissions should not be assigned

**`is_deprecated`** (boolean, required)
- Whether permission is deprecated
- Deprecated permissions are still valid but not recommended

**`created_at`** (string, optional)
- ISO 8601 timestamp of creation
- Only in detailed responses

**`updated_at`** (string, optional)
- ISO 8601 timestamp of last update
- Only in detailed responses

## Hierarchical Structure

### Flat Modules

```json
{
  "modules": [
    {
      "key": "users",
      "permissions": [...]
    },
    {
      "key": "orders",
      "permissions": [...]
    }
  ]
}
```

### Nested Modules

```json
{
  "modules": [
    {
      "key": "breakdown",
      "permissions": [
        {
          "key": "breakdown.view",
          ...
        }
      ],
      "submodules": [
        {
          "key": "breakdown.visit",
          "permissions": [
            {
              "key": "breakdown.visit.view",
              ...
            },
            {
              "key": "breakdown.visit.assign_engineer",
              ...
            }
          ]
        }
      ]
    }
  ]
}
```

## Filtering and Querying

### Filter by Module

```
GET /api/permissions/catalog/?module=users
```

Returns only permissions for the specified module.

### Filter by Type

```
GET /api/permissions/catalog/?type=crud
GET /api/permissions/catalog/?type=action
```

Returns only CRUD or action permissions.

### Filter Active Only

```
GET /api/permissions/catalog/?active_only=true
```

Returns only active (non-deprecated) permissions.

### Search

```
GET /api/permissions/catalog/?search=password
```

Searches in permission keys, labels, and descriptions.

## Caching

### Response Caching

Catalog responses are cached for performance:

```python
from django.core.cache import cache

def get_catalog():
    cache_key = 'permission_catalog'
    catalog = cache.get(cache_key)
    if catalog is None:
        catalog = build_catalog()
        cache.set(cache_key, catalog, timeout=3600)  # 1 hour
    return catalog
```

### Cache Invalidation

Cache is invalidated when permissions change:

```python
@receiver(post_save, sender=Permission)
def invalidate_catalog_cache(sender, instance, **kwargs):
    cache.delete('permission_catalog')
```

## Implementation

### ViewSet Implementation

```python
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

class PermissionCatalogViewSet(viewsets.ViewSet):
    permission_classes = []  # Public or authenticated
    
    @action(detail=False, methods=['get'])
    def catalog(self, request):
        """Get full permission catalog"""
        catalog = self.build_catalog()
        return Response(catalog)
    
    @action(detail=False, methods=['get'], url_path='catalog/(?P<module>[^/.]+)')
    def module_catalog(self, request, module=None):
        """Get catalog for specific module"""
        module_data = self.get_module_data(module)
        return Response(module_data)
    
    def build_catalog(self):
        # Build hierarchical catalog from database
        modules = self.get_modules()
        return {
            'modules': [self.serialize_module(m) for m in modules],
            'total_permissions': Permission.objects.count(),
            'total_modules': len(modules)
        }
    
    def serialize_module(self, module):
        permissions = Permission.objects.filter(module=module.key)
        return {
            'key': module.key,
            'label': module.label,
            'description': module.description,
            'permissions': [self.serialize_permission(p) for p in permissions],
            'submodules': [self.serialize_module(sm) for sm in module.submodules]
        }
    
    def serialize_permission(self, permission):
        return {
            'key': permission.key,
            'module': permission.module,
            'capability': permission.capability,
            'label': permission.label,
            'description': permission.description,
            'type': 'crud' if permission.capability in ['view', 'create', 'update', 'delete'] else 'action',
            'is_active': permission.is_active,
            'is_deprecated': permission.is_deprecated
        }
```

## Frontend Usage

### Permission List Component

```javascript
// React example
function PermissionList() {
  const [catalog, setCatalog] = useState(null);
  
  useEffect(() => {
    fetch('/api/permissions/catalog/')
      .then(res => res.json())
      .then(data => setCatalog(data));
  }, []);
  
  return (
    <div>
      {catalog?.modules.map(module => (
        <ModuleSection key={module.key} module={module} />
      ))}
    </div>
  );
}
```

### Role Editor

```javascript
function RoleEditor({ role }) {
  const [catalog, setCatalog] = useState(null);
  const [selectedPermissions, setSelectedPermissions] = useState([]);
  
  useEffect(() => {
    fetch('/api/permissions/catalog/')
      .then(res => res.json())
      .then(data => setCatalog(data));
  }, []);
  
  const togglePermission = (permissionKey) => {
    // Toggle permission selection
    setSelectedPermissions(prev => 
      prev.includes(permissionKey)
        ? prev.filter(k => k !== permissionKey)
        : [...prev, permissionKey]
    );
  };
  
  return (
    <div>
      {catalog?.modules.map(module => (
        <ModulePermissions
          key={module.key}
          module={module}
          selected={selectedPermissions}
          onToggle={togglePermission}
        />
      ))}
    </div>
  );
}
```

### Feature Toggle

```javascript
function FeatureToggle({ permissionKey, children }) {
  const [hasPermission, setHasPermission] = useState(false);
  const userPermissions = useUserPermissions(); // From auth context
  
  useEffect(() => {
    setHasPermission(userPermissions.includes(permissionKey));
  }, [permissionKey, userPermissions]);
  
  if (!hasPermission) return null;
  return children;
}

// Usage
<FeatureToggle permissionKey="users.export_data">
  <ExportButton />
</FeatureToggle>
```

## Security Considerations

### Authentication

Catalog API should require authentication:

```python
class PermissionCatalogViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    # Or more restrictive:
    # permission_classes = [IsAdminUser]
```

### Rate Limiting

Apply rate limiting to prevent abuse:

```python
from rest_framework.throttling import UserRateThrottle

class CatalogThrottle(UserRateThrottle):
    rate = '100/hour'

class PermissionCatalogViewSet(viewsets.ViewSet):
    throttle_classes = [CatalogThrottle]
```

### Data Filtering

Filter sensitive information:

```python
def serialize_permission(self, permission):
    data = {
        'key': permission.key,
        'label': permission.label,
        # ... other fields
    }
    
    # Don't expose internal metadata to non-admins
    if not request.user.is_staff:
        data.pop('internal_notes', None)
    
    return data
```

## Best Practices

### 1. Cache Responses

```python
# ✅ Good: Cache catalog
@cached_property
def catalog(self):
    return self.build_catalog()

# ❌ Bad: Rebuild every request
def catalog(self):
    return self.build_catalog()  # Expensive!
```

### 2. Paginate Large Catalogs

```python
# For very large permission sets
class PermissionCatalogViewSet(viewsets.ViewSet):
    pagination_class = PageNumberPagination
    
    @action(detail=False, methods=['get'])
    def catalog(self, request):
        queryset = Permission.objects.all()
        page = self.paginate_queryset(queryset)
        return self.get_paginated_response(page)
```

### 3. Provide Filtering

```python
# ✅ Good: Allow filtering
GET /api/permissions/catalog/?module=users&type=action

# ❌ Bad: Always return everything
GET /api/permissions/catalog/  # Returns 1000+ permissions
```

### 4. Version API Responses

```python
# For future compatibility
class PermissionCatalogViewSet(viewsets.ViewSet):
    def catalog(self, request):
        version = request.query_params.get('version', '1')
        if version == '2':
            return self.build_catalog_v2()
        return self.build_catalog_v1()
```

### 5. Document API

```python
class PermissionCatalogViewSet(viewsets.ViewSet):
    """
    Permission Catalog API
    
    Provides hierarchical permission catalog for frontend consumption.
    
    Endpoints:
    - GET /catalog/ - Full catalog
    - GET /catalog/{module}/ - Module-specific catalog
    - GET /{permission_key}/ - Permission details
    """
    ...
```

## Testing

### API Tests

```python
def test_catalog_endpoint():
    response = client.get('/api/permissions/catalog/')
    assert response.status_code == 200
    assert 'modules' in response.data
    assert len(response.data['modules']) > 0

def test_module_catalog():
    response = client.get('/api/permissions/catalog/users/')
    assert response.status_code == 200
    assert response.data['key'] == 'users'
    assert 'permissions' in response.data

def test_permission_details():
    response = client.get('/api/permissions/users.view/')
    assert response.status_code == 200
    assert response.data['key'] == 'users.view'
```

### Frontend Integration Tests

```javascript
test('loads permission catalog', async () => {
  const { getByText } = render(<PermissionList />);
  
  await waitFor(() => {
    expect(getByText('User Management')).toBeInTheDocument();
    expect(getByText('users.view')).toBeInTheDocument();
  });
});
```
