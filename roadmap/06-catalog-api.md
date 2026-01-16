# Phase 6: Permission Catalog API

## Overview

This phase covers implementing the permission catalog API for frontend consumption.

## Step 1: Create Catalog ViewSet

### django_permission_engine/views.py

```python
"""
Permission Catalog API views
"""
from typing import Dict, List
from django.core.cache import cache
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import Permission


class PermissionCatalogViewSet(viewsets.ViewSet):
    """
    Permission Catalog API
    
    Provides hierarchical permission catalog for frontend consumption.
    """
    permission_classes = [IsAuthenticated]  # Or IsAdminUser for stricter access
    
    @action(detail=False, methods=['get'])
    def catalog(self, request):
        """
        Get full permission catalog.
        
        Returns hierarchical structure organized by modules.
        """
        catalog = self._build_catalog()
        return Response(catalog)
    
    @action(detail=False, methods=['get'], url_path='catalog/(?P<module>[^/.]+)')
    def module_catalog(self, request, module=None):
        """
        Get catalog for specific module.
        
        Args:
            module: Module name (e.g., 'users', 'breakdown.visit')
        """
        module_data = self._get_module_data(module)
        if not module_data:
            return Response(
                {'error': f'Module not found: {module}'},
                status=404
            )
        return Response(module_data)
    
    def _build_catalog(self) -> Dict:
        """Build full permission catalog"""
        # Check cache
        cache_key = 'permission_catalog'
        catalog = cache.get(cache_key)
        
        if catalog is None:
            # Build catalog from database
            modules = self._get_modules()
            catalog = {
                'modules': [self._serialize_module(m) for m in modules],
                'total_permissions': Permission.objects.count(),
                'total_modules': len(modules),
            }
            # Cache for 1 hour
            cache.set(cache_key, catalog, timeout=3600)
        
        return catalog
    
    def _get_modules(self) -> List[str]:
        """Get list of all modules"""
        return list(
            Permission.objects
            .values_list('module', flat=True)
            .distinct()
            .order_by('module')
        )
    
    def _serialize_module(self, module_key: str) -> Dict:
        """Serialize module with its permissions"""
        permissions = Permission.objects.filter(module=module_key).order_by('capability')
        
        # Check for submodules
        submodules = self._get_submodules(module_key)
        
        return {
            'key': module_key,
            'label': self._get_module_label(module_key),
            'description': self._get_module_description(module_key),
            'permissions': [self._serialize_permission(p) for p in permissions],
            'submodules': [self._serialize_module(sm) for sm in submodules],
        }
    
    def _get_submodules(self, parent_module: str) -> List[str]:
        """Get submodules for a parent module"""
        prefix = f"{parent_module}."
        return list(
            Permission.objects
            .filter(module__startswith=prefix)
            .values_list('module', flat=True)
            .distinct()
            .order_by('module')
        )
    
    def _serialize_permission(self, permission: Permission) -> Dict:
        """Serialize permission object"""
        return {
            'key': permission.key,
            'module': permission.module,
            'capability': permission.capability,
            'label': permission.label,
            'description': permission.description,
            'type': self._get_permission_type(permission.capability),
            'is_active': permission.is_active,
            'is_deprecated': permission.is_deprecated,
        }
    
    def _get_permission_type(self, capability: str) -> str:
        """Determine permission type (crud or action)"""
        crud_capabilities = ['view', 'create', 'update', 'delete']
        return 'crud' if capability in crud_capabilities else 'action'
    
    def _get_module_label(self, module_key: str) -> str:
        """Get module label (from registry or generate)"""
        # Try to get from registry
        try:
            from . import get_registry
            registry = get_registry()
            if module_key in registry._modules:
                return registry._modules[module_key].label
        except Exception:
            pass
        
        # Generate from key
        return module_key.replace('_', ' ').title()
    
    def _get_module_description(self, module_key: str) -> str:
        """Get module description (from registry)"""
        try:
            from . import get_registry
            registry = get_registry()
            if module_key in registry._modules:
                return registry._modules[module_key].description
        except Exception:
            pass
        
        return ''
    
    def _get_module_data(self, module_key: str) -> Dict:
        """Get data for specific module"""
        if not Permission.objects.filter(module=module_key).exists():
            return None
        
        return self._serialize_module(module_key)
```

## Step 2: Create URL Configuration

### django_permission_engine/urls.py

```python
"""
URL configuration for UPR
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import PermissionCatalogViewSet

router = DefaultRouter()
router.register(r'permissions', PermissionCatalogViewSet, basename='permission-catalog')

urlpatterns = [
    path('api/', include(router.urls)),
]
```

## Step 3: Update Main URLs

### Update project urls.py

```python
# In your Django project's urls.py
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('django_permission_engine.urls')),
    # ... other URLs
]
```

## Step 4: Add Filtering Support

### Update views.py

```python
class PermissionCatalogViewSet(viewsets.ViewSet):
    # ... existing code ...
    
    @action(detail=False, methods=['get'])
    def catalog(self, request):
        """Get full permission catalog with optional filtering"""
        # Get filter parameters
        module_filter = request.query_params.get('module')
        type_filter = request.query_params.get('type')  # 'crud' or 'action'
        active_only = request.query_params.get('active_only', 'false').lower() == 'true'
        search = request.query_params.get('search')
        
        # Build catalog
        catalog = self._build_catalog()
        
        # Apply filters
        if module_filter:
            catalog['modules'] = [
                m for m in catalog['modules']
                if m['key'] == module_filter or m['key'].startswith(f"{module_filter}.")
            ]
        
        if type_filter:
            for module in catalog['modules']:
                module['permissions'] = [
                    p for p in module['permissions']
                    if p['type'] == type_filter
                ]
        
        if active_only:
            for module in catalog['modules']:
                module['permissions'] = [
                    p for p in module['permissions']
                    if p['is_active'] and not p['is_deprecated']
                ]
        
        if search:
            search_lower = search.lower()
            for module in catalog['modules']:
                module['permissions'] = [
                    p for p in module['permissions']
                    if (
                        search_lower in p['key'].lower() or
                        search_lower in p['label'].lower() or
                        search_lower in (p.get('description', '') or '').lower()
                    )
                ]
                # Remove modules with no matching permissions
            catalog['modules'] = [
                m for m in catalog['modules']
                if m['permissions'] or any(
                    sm['permissions'] for sm in m.get('submodules', [])
                )
            ]
        
        return Response(catalog)
```

## Step 5: Write Catalog API Tests

### tests/test_catalog_api.py

```python
"""
Tests for Permission Catalog API
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from django_permission_engine.models import Permission

User = get_user_model()


@pytest.mark.django_db
class TestPermissionCatalogAPI:
    """Test Permission Catalog API"""
    
    @pytest.fixture
    def client(self):
        """Create API client"""
        return APIClient()
    
    @pytest.fixture
    def user(self):
        """Create test user"""
        return User.objects.create_user('testuser', 'test@example.com', 'password')
    
    @pytest.fixture
    def permissions(self):
        """Create test permissions"""
        permissions = []
        for action in ['view', 'create', 'update', 'delete']:
            perm = Permission.objects.create(
                key=f'users.{action}',
                module='users',
                capability=action,
                label=f'{action.title()} Users',
            )
            permissions.append(perm)
        
        perm = Permission.objects.create(
            key='users.reset_password',
            module='users',
            capability='reset_password',
            label='Reset Password',
        )
        permissions.append(perm)
        
        return permissions
    
    def test_catalog_endpoint(self, client, user, permissions):
        """Test catalog endpoint"""
        client.force_authenticate(user=user)
        response = client.get('/api/permissions/catalog/')
        
        assert response.status_code == 200
        data = response.json()
        assert 'modules' in data
        assert 'total_permissions' in data
        assert 'total_modules' in data
        assert len(data['modules']) > 0
    
    def test_module_catalog_endpoint(self, client, user, permissions):
        """Test module catalog endpoint"""
        client.force_authenticate(user=user)
        response = client.get('/api/permissions/catalog/users/')
        
        assert response.status_code == 200
        data = response.json()
        assert data['key'] == 'users'
        assert 'permissions' in data
        assert len(data['permissions']) == 5
    
    def test_catalog_filter_by_module(self, client, user, permissions):
        """Test filtering by module"""
        client.force_authenticate(user=user)
        response = client.get('/api/permissions/catalog/?module=users')
        
        assert response.status_code == 200
        data = response.json()
        assert all(m['key'] == 'users' or m['key'].startswith('users.') for m in data['modules'])
    
    def test_catalog_filter_by_type(self, client, user, permissions):
        """Test filtering by type"""
        client.force_authenticate(user=user)
        response = client.get('/api/permissions/catalog/?type=crud')
        
        assert response.status_code == 200
        data = response.json()
        for module in data['modules']:
            for perm in module['permissions']:
                assert perm['type'] == 'crud'
    
    def test_catalog_search(self, client, user, permissions):
        """Test search functionality"""
        client.force_authenticate(user=user)
        response = client.get('/api/permissions/catalog/?search=reset')
        
        assert response.status_code == 200
        data = response.json()
        found = False
        for module in data['modules']:
            for perm in module['permissions']:
                if 'reset' in perm['key'].lower() or 'reset' in perm['label'].lower():
                    found = True
        assert found
    
    def test_catalog_unauthenticated(self, client):
        """Test catalog requires authentication"""
        response = client.get('/api/permissions/catalog/')
        assert response.status_code == 401
```

## Step 6: Add Cache Invalidation

### django_permission_engine/models.py (add signal)

```python
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache


@receiver([post_save, post_delete], sender=Permission)
def invalidate_permission_cache(sender, instance, **kwargs):
    """Invalidate permission catalog cache when permissions change"""
    cache.delete('permission_catalog')
```

## Step 7: Create API Documentation

### Add to views.py docstrings

```python
class PermissionCatalogViewSet(viewsets.ViewSet):
    """
    Permission Catalog API
    
    Provides hierarchical permission catalog for frontend consumption.
    
    Endpoints:
    - GET /api/permissions/catalog/ - Full catalog
    - GET /api/permissions/catalog/{module}/ - Module-specific catalog
    
    Query Parameters:
    - module: Filter by module name
    - type: Filter by type ('crud' or 'action')
    - active_only: Return only active permissions (true/false)
    - search: Search in keys, labels, descriptions
    """
```

## Checklist

- [ ] PermissionCatalogViewSet created
- [ ] URL configuration added
- [ ] Filtering support implemented
- [ ] Cache implemented
- [ ] Catalog API tests written
- [ ] Cache invalidation implemented
- [ ] API documentation added

## Next Steps

Once catalog API is complete, proceed to **[07-management-commands.md](07-management-commands.md)** to implement Django management commands.
