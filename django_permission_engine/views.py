"""
Permission Catalog API views
"""
from typing import Dict, List
from django.core.cache import cache
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated


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
    permission_classes = [IsAuthenticated]  # Or IsAdminUser for stricter access

    @action(detail=False, methods=['get'])
    def catalog(self, request, *args, **kwargs):
        """
        Get full permission catalog.

        Returns hierarchical structure organized by modules.
        """
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

    @action(detail=False, methods=['get'], url_path='catalog/(?P<module>[^/.]+)')
    def module_catalog(self, request, module=None, *args, **kwargs):
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
        from .models import Permission
        
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
        from .models import Permission
        return list(
            Permission.objects
            .values_list('module', flat=True)
            .distinct()
            .order_by('module')
        )

    def _serialize_module(self, module_key: str) -> Dict:
        """Serialize module with its permissions"""
        from .models import Permission
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
        from .models import Permission
        prefix = f"{parent_module}."
        return list(
            Permission.objects
            .filter(module__startswith=prefix)
            .values_list('module', flat=True)
            .distinct()
            .order_by('module')
        )

    def _serialize_permission(self, permission) -> Dict:
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
            from .registry import get_registry
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
            from .registry import get_registry
            registry = get_registry()
            if module_key in registry._modules:
                return registry._modules[module_key].description
        except Exception:
            pass

        return ''

    def _get_module_data(self, module_key: str) -> Dict:
        """Get data for specific module"""
        from .models import Permission
        if not Permission.objects.filter(module=module_key).exists():
            return None

        return self._serialize_module(module_key)
