# Phase 4: Permission Definition Layer

## Overview

This phase covers implementing the declarative permission definition layer with decorators and class-based definitions.

## Step 1: Create Module Decorator

### django_permission_engine/registry.py (add to existing file)

```python
"""
Module decorator for declarative permission definitions
"""
from functools import wraps
from typing import Callable, Optional, List


def module(
    name: str,
    label: Optional[str] = None,
    description: Optional[str] = None,
):
    """
    Decorator to register a module class as a permission module.
    
    Usage:
        @registry.module('users')
        class UsersModule:
            crud = ['view', 'create', 'update', 'delete']
            actions = ['reset_password']
    """
    def decorator(cls):
        from . import get_registry
        registry = get_registry()
        
        # Extract CRUD and actions from class
        crud = getattr(cls, 'crud', [])
        actions = getattr(cls, 'actions', [])
        
        # Register module
        registry.register_module(
            module_name=name,
            crud=crud,
            actions=actions,
            label=label or getattr(cls, 'label', None),
            description=description or getattr(cls, 'description', None),
        )
        
        # Store module class for reference
        cls._upr_module_name = name
        cls._upr_registry = registry
        
        return cls
    
    return decorator


def action(
    name: str,
    label: Optional[str] = None,
    description: Optional[str] = None,
    deprecated: bool = False,
):
    """
    Decorator to register a custom action permission.
    
    Usage:
        @registry.module('users')
        class UsersModule:
            crud = ['view']
            
            @registry.action('reset_password', label='Reset Password')
            def reset_password(self):
                pass
    """
    def decorator(func):
        # Store action metadata
        func._upr_action_name = name
        func._upr_action_label = label
        func._upr_action_description = description
        func._upr_action_deprecated = deprecated
        
        return func
    
    return decorator
```

## Step 2: Enhance Registry to Handle Decorators

### Update django_permission_engine/registry.py

```python
class PermissionRegistry:
    # ... existing code ...
    
    def register_module_class(self, module_class):
        """Register a module from a class definition"""
        module_name = getattr(module_class, '_upr_module_name', None)
        if not module_name:
            raise ValueError("Module class must be decorated with @module")
        
        # Extract CRUD
        crud = getattr(module_class, 'crud', [])
        
        # Extract actions from methods decorated with @action
        actions = []
        for attr_name in dir(module_class):
            attr = getattr(module_class, attr_name)
            if hasattr(attr, '_upr_action_name'):
                action_name = attr._upr_action_name
                actions.append(action_name)
        
        # Also check for actions list attribute
        actions_list = getattr(module_class, 'actions', [])
        actions.extend(actions_list)
        
        # Remove duplicates
        actions = list(set(actions))
        
        # Register module
        self.register_module(
            module_name=module_name,
            crud=crud,
            actions=actions,
            label=getattr(module_class, 'label', None),
            description=getattr(module_class, 'description', None),
        )
```

## Step 3: Create Registry Helper Functions

### django_permission_engine/registry.py (add)

```python
# Global registry instance
_default_registry = None


def get_registry() -> PermissionRegistry:
    """Get or create default registry instance"""
    global _default_registry
    
    if _default_registry is None:
        from django.conf import settings
        config = getattr(settings, 'UPR_CONFIG', {})
        _default_registry = PermissionRegistry(**config)
    
    return _default_registry


# Create module and action decorators that use default registry
def module(name: str, label: Optional[str] = None, description: Optional[str] = None):
    """Module decorator using default registry"""
    registry = get_registry()
    return registry.module(name, label, description)


def action(name: str, label: Optional[str] = None, description: Optional[str] = None, deprecated: bool = False):
    """Action decorator using default registry"""
    registry = get_registry()
    return registry.action(name, label, description, deprecated)
```

## Step 4: Update __init__.py to Export Decorators

### django_permission_engine/__init__.py

```python
"""
Django Permission Engine - Unified Permission Registry (UPR) for Django & DRF
"""
from .registry import (
    PermissionRegistry,
    PermissionDefinition,
    get_registry,
    module,
    action,
)

__version__ = "0.1.0"
__all__ = [
    "PermissionRegistry",
    "PermissionDefinition",
    "get_registry",
    "registry",
    "module",
    "action",
]

# Create default registry instance
registry = get_registry()
```

## Step 5: Write Definition Tests

### tests/test_permission_definition.py

```python
"""
Tests for permission definition layer
"""
import pytest
from django_permission_engine import registry, module, action
from django_permission_engine.models import Permission


@pytest.mark.django_db
class TestModuleDecorator:
    """Test @module decorator"""
    
    def test_module_decorator_simple(self):
        """Test simple module definition"""
        @module('users')
        class UsersModule:
            crud = ['view', 'create', 'update', 'delete']
        
        # Check module registered
        assert 'users' in registry._modules
        permissions = registry.get_all_permissions()
        assert 'users.view' in permissions
        assert 'users.create' in permissions
        assert 'users.update' in permissions
        assert 'users.delete' in permissions
    
    def test_module_decorator_with_actions(self):
        """Test module with actions list"""
        @module('users')
        class UsersModule:
            crud = ['view']
            actions = ['reset_password', 'export_data']
        
        permissions = registry.get_all_permissions()
        assert 'users.view' in permissions
        assert 'users.reset_password' in permissions
        assert 'users.export_data' in permissions
    
    def test_module_decorator_with_metadata(self):
        """Test module with label and description"""
        @module('users', label='User Management', description='Manage users')
        class UsersModule:
            crud = ['view']
        
        module_def = registry._modules['users']
        assert module_def.label == 'User Management'
        assert module_def.description == 'Manage users'
    
    def test_module_decorator_class_metadata(self):
        """Test module using class attributes"""
        @module('users')
        class UsersModule:
            label = 'User Management'
            description = 'Manage users'
            crud = ['view']
        
        module_def = registry._modules['users']
        assert module_def.label == 'User Management'
        assert module_def.description == 'Manage users'


@pytest.mark.django_db
class TestActionDecorator:
    """Test @action decorator"""
    
    def test_action_decorator(self):
        """Test action decorator"""
        @module('users')
        class UsersModule:
            crud = ['view']
            
            @action('reset_password', label='Reset Password')
            def reset_password(self):
                pass
        
        permissions = registry.get_all_permissions()
        assert 'users.reset_password' in permissions
        
        perm_def = permissions['users.reset_password']
        assert perm_def.label == 'Reset Password'
    
    def test_action_decorator_multiple(self):
        """Test multiple action decorators"""
        @module('users')
        class UsersModule:
            crud = ['view']
            
            @action('reset_password')
            def reset_password(self):
                pass
            
            @action('export_data')
            def export_data(self):
                pass
        
        permissions = registry.get_all_permissions()
        assert 'users.reset_password' in permissions
        assert 'users.export_data' in permissions
    
    def test_action_decorator_with_description(self):
        """Test action with description"""
        @module('users')
        class UsersModule:
            crud = ['view']
            
            @action(
                'reset_password',
                label='Reset Password',
                description='Allows resetting user passwords'
            )
            def reset_password(self):
                pass
        
        permissions = registry.get_all_permissions()
        perm_def = permissions['users.reset_password']
        assert perm_def.description == 'Allows resetting user passwords'
    
    def test_action_decorator_deprecated(self):
        """Test deprecated action"""
        @module('users')
        class UsersModule:
            crud = ['view']
            
            @action('old_action', deprecated=True)
            def old_action(self):
                pass
        
        permissions = registry.get_all_permissions()
        assert 'users.old_action' in permissions


@pytest.mark.django_db
class TestDefinitionIntegration:
    """Test integration of definition layer"""
    
    def test_full_module_definition(self):
        """Test complete module definition"""
        @module('orders', label='Order Management')
        class OrdersModule:
            crud = ['view', 'create', 'update', 'delete']
            actions = ['cancel', 'refund']
            
            @action('ship', label='Ship Order')
            def ship(self):
                pass
        
        # Sync to database
        result = registry.sync()
        
        # Verify permissions created
        assert Permission.objects.filter(module='orders').count() == 7
        assert Permission.objects.filter(key='orders.view').exists()
        assert Permission.objects.filter(key='orders.cancel').exists()
        assert Permission.objects.filter(key='orders.ship').exists()
    
    def test_hierarchical_modules(self):
        """Test hierarchical module structure"""
        @module('breakdown')
        class BreakdownModule:
            crud = ['view', 'create', 'update', 'delete']
        
        @module('breakdown.visit')
        class BreakdownVisitModule:
            crud = ['view', 'create', 'update']
            actions = ['assign_engineer', 'close']
        
        # Sync
        registry.sync()
        
        # Verify permissions
        assert Permission.objects.filter(module='breakdown').count() == 4
        assert Permission.objects.filter(module='breakdown.visit').count() == 5
        assert Permission.objects.filter(key='breakdown.visit.assign_engineer').exists()
```

## Step 6: Create Example Usage File

### examples/basic_usage.py

```python
"""
Example: Basic permission definition usage
"""
from django_permission_engine import module, action


@module('users', label='User Management')
class UsersModule:
    """User management module"""
    crud = ['view', 'create', 'update', 'delete']
    actions = ['reset_password', 'export_data']
    
    @action('bulk_delete', label='Bulk Delete Users')
    def bulk_delete(self):
        """Bulk delete action"""
        pass


@module('orders', label='Order Management')
class OrdersModule:
    """Order management module"""
    crud = ['view', 'create', 'update', 'delete']
    actions = ['cancel', 'refund', 'ship']
    
    @action('refund', label='Refund Order', description='Process order refund')
    def refund(self):
        """Refund action"""
        pass


@module('reports', label='Reports')
class ReportsModule:
    """Reports module - read-only"""
    crud = ['view']  # Read-only
    actions = ['export', 'schedule']
```

## Step 7: Create Auto-Discovery Mechanism

### django_permission_engine/registry.py (add)

```python
class PermissionRegistry:
    # ... existing code ...
    
    def discover_modules(self, app_name: str = None):
        """
        Auto-discover and register modules from upr_config modules.
        
        Looks for upr_config.py in installed apps and imports it.
        """
        from django.apps import apps
        
        apps_to_check = [apps.get_app_config(app_name)] if app_name else apps.get_app_configs()
        
        for app_config in apps_to_check:
            try:
                # Try to import upr_config from app
                config_module = f"{app_config.name}.upr_config"
                __import__(config_module)
            except ImportError:
                # App doesn't have upr_config, skip
                continue
```

## Step 8: Update App Config for Auto-Discovery

### django_permission_engine/apps.py

```python
from django.apps import AppConfig


class PermissionEngineConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "django_permission_engine"
    verbose_name = "Permission Engine"
    
    def ready(self):
        """Called when Django starts"""
        from django.conf import settings
        from .registry import get_registry
        
        registry = get_registry()
        
        # Auto-discover modules if configured
        if getattr(settings, "UPR_AUTO_DISCOVER", True):
            registry.discover_modules()
        
        # Validate if configured
        if getattr(settings, "UPR_VALIDATE_ON_STARTUP", False):
            errors = registry.validate()
            if errors and registry.strict_mode:
                from django.core.exceptions import ValidationError
                raise ValidationError(f"Registry validation failed: {errors}")
        
        # Auto-sync if configured
        if getattr(settings, "UPR_AUTO_SYNC", False):
            registry.sync()
```

## Checklist

- [ ] Module decorator implemented
- [ ] Action decorator implemented
- [ ] Registry integration with decorators
- [ ] Definition tests written and passing
- [ ] Example usage file created
- [ ] Auto-discovery mechanism implemented
- [ ] App config updated for auto-discovery

## Next Steps

Once permission definition layer is complete, proceed to **[05-runtime-resolution.md](05-runtime-resolution.md)** to implement runtime permission checking.
