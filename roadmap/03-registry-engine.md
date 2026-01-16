# Phase 3: Registry Engine

## Overview

This phase covers implementing the permission registry engine that synchronizes permission definitions with the database.

## Step 1: Create Registry Base Class

### django_permission_engine/registry.py

```python
"""
Permission Registry Engine

Handles registration and synchronization of permissions.
"""
from typing import Dict, List, Optional, Set
from django.core.cache import cache
from django.db import transaction
from django.core.exceptions import ValidationError

from .models import Permission


class PermissionDefinition:
    """Represents a permission definition"""
    
    def __init__(
        self,
        key: str,
        module: str,
        capability: str,
        label: str,
        description: str = "",
        type: str = "action",  # "crud" or "action"
    ):
        self.key = key
        self.module = module
        self.capability = capability
        self.label = label
        self.description = description
        self.type = type
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "key": self.key,
            "module": self.module,
            "capability": self.capability,
            "label": self.label,
            "description": self.description,
            "type": self.type,
        }


class PermissionRegistry:
    """
    Permission Registry
    
    Manages permission definitions and synchronizes with database.
    """
    
    STANDARD_CRUD = ["view", "create", "update", "delete"]
    
    def __init__(
        self,
        validate_on_startup: bool = True,
        strict_mode: bool = True,
        auto_sync: bool = False,
        orphan_action: str = "warn",  # "warn", "error", or "delete"
    ):
        self.validate_on_startup = validate_on_startup
        self.strict_mode = strict_mode
        self.auto_sync = auto_sync
        self.orphan_action = orphan_action
        
        self._modules: Dict[str, "ModuleDefinition"] = {}
        self._permissions: Dict[str, PermissionDefinition] = {}
        self._registered_viewsets: List = []
    
    def register_module(
        self,
        module_name: str,
        crud: Optional[List[str]] = None,
        actions: Optional[List[str]] = None,
        label: Optional[str] = None,
        description: Optional[str] = None,
    ):
        """Register a module with its permissions"""
        if module_name in self._modules:
            raise ValueError(f"Module '{module_name}' is already registered")
        
        module_def = ModuleDefinition(
            name=module_name,
            crud=crud or [],
            actions=actions or [],
            label=label,
            description=description,
        )
        
        self._modules[module_name] = module_def
        
        # Generate permissions
        self._generate_module_permissions(module_def)
    
    def _generate_module_permissions(self, module_def: "ModuleDefinition"):
        """Generate permissions for a module"""
        # Generate CRUD permissions
        for capability in module_def.crud:
            if capability not in self.STANDARD_CRUD:
                raise ValidationError(
                    f"Invalid CRUD capability: {capability}. "
                    f"Valid options: {self.STANDARD_CRUD}"
                )
            
            key = f"{module_def.name}.{capability}"
            label = self._generate_crud_label(capability, module_def.name)
            
            perm_def = PermissionDefinition(
                key=key,
                module=module_def.name,
                capability=capability,
                label=label,
                type="crud",
            )
            self._permissions[key] = perm_def
        
        # Generate action permissions
        for action in module_def.actions:
            key = f"{module_def.name}.{action}"
            label = self._generate_action_label(action, module_def.name)
            
            perm_def = PermissionDefinition(
                key=key,
                module=module_def.name,
                capability=action,
                label=label,
                type="action",
            )
            self._permissions[key] = perm_def
    
    def _generate_crud_label(self, capability: str, module: str) -> str:
        """Generate label for CRUD permission"""
        labels = {
            "view": f"View {module.title()}",
            "create": f"Create {module.title()}",
            "update": f"Update {module.title()}",
            "delete": f"Delete {module.title()}",
        }
        return labels.get(capability, capability)
    
    def _generate_action_label(self, action: str, module: str) -> str:
        """Generate label for action permission"""
        # Convert snake_case to Title Case
        label = action.replace("_", " ").title()
        return f"{label} {module.title()}"
    
    def get_all_permissions(self) -> Dict[str, PermissionDefinition]:
        """Get all registered permissions"""
        return self._permissions.copy()
    
    def get_all_permission_keys(self) -> Set[str]:
        """Get all permission keys"""
        return set(self._permissions.keys())
    
    def get_module_permissions(self, module: str) -> List[PermissionDefinition]:
        """Get permissions for a module"""
        return [
            perm for perm in self._permissions.values()
            if perm.module == module
        ]
    
    def validate(self) -> List[str]:
        """Validate registry consistency"""
        errors = []
        
        # Validate permission keys
        for key, perm_def in self._permissions.items():
            if "." not in key:
                errors.append(f"Invalid permission key format: {key}")
            
            if key != f"{perm_def.module}.{perm_def.capability}":
                errors.append(
                    f"Permission key '{key}' does not match "
                    f"module.capability '{perm_def.module}.{perm_def.capability}'"
                )
        
        # Check for duplicates
        if len(self._permissions) != len(set(self._permissions.keys())):
            errors.append("Duplicate permission keys found")
        
        return errors
    
    @transaction.atomic
    def sync(self, dry_run: bool = False) -> Dict:
        """Synchronize permissions with database"""
        # Collect definitions
        definitions = self.get_all_permissions()
        
        # Load database state
        db_permissions = {
            p.key: p for p in Permission.objects.all()
        }
        
        # Plan changes
        plan = self._plan_sync(definitions, db_permissions)
        
        if dry_run:
            return plan
        
        # Execute changes
        result = self._execute_sync(plan)
        
        # Invalidate cache
        cache.delete("permission_catalog")
        
        return result
    
    def _plan_sync(
        self,
        definitions: Dict[str, PermissionDefinition],
        db_permissions: Dict[str, Permission],
    ) -> Dict:
        """Plan synchronization changes"""
        plan = {
            "create": [],
            "update": [],
            "orphaned": [],
        }
        
        # Find new permissions
        for key, definition in definitions.items():
            if key not in db_permissions:
                plan["create"].append(definition)
            else:
                # Check if metadata changed
                existing = db_permissions[key]
                if self._metadata_changed(existing, definition):
                    plan["update"].append(definition)
        
        # Find orphaned permissions
        for key, permission in db_permissions.items():
            if key not in definitions:
                plan["orphaned"].append(permission)
        
        return plan
    
    def _metadata_changed(
        self,
        existing: Permission,
        definition: PermissionDefinition,
    ) -> bool:
        """Check if permission metadata changed"""
        return (
            existing.label != definition.label
            or existing.description != definition.description
            or existing.is_active is False
            or existing.is_deprecated != (definition.type == "deprecated")
        )
    
    def _execute_sync(self, plan: Dict) -> Dict:
        """Execute synchronization plan"""
        created = []
        updated = []
        orphaned = []
        
        # Create new permissions
        for definition in plan["create"]:
            permission = Permission.objects.create(
                key=definition.key,
                module=definition.module,
                capability=definition.capability,
                label=definition.label,
                description=definition.description,
                is_active=True,
            )
            created.append(permission.key)
        
        # Update existing permissions
        for definition in plan["update"]:
            Permission.objects.filter(key=definition.key).update(
                label=definition.label,
                description=definition.description,
                is_active=True,
            )
            updated.append(definition.key)
        
        # Handle orphaned permissions
        for permission in plan["orphaned"]:
            if self.orphan_action == "delete":
                permission.delete()
                orphaned.append(permission.key)
            elif self.orphan_action == "error":
                raise ValidationError(
                    f"Orphaned permission found: {permission.key}"
                )
            elif self.orphan_action == "warn":
                orphaned.append(permission.key)
        
        return {
            "created": created,
            "updated": updated,
            "orphaned": orphaned,
        }


class ModuleDefinition:
    """Represents a module definition"""
    
    def __init__(
        self,
        name: str,
        crud: List[str],
        actions: List[str],
        label: Optional[str] = None,
        description: Optional[str] = None,
    ):
        self.name = name
        self.crud = crud
        self.actions = actions
        self.label = label or name.title()
        self.description = description or ""
```

## Step 2: Create Registry Instance

### django_permission_engine/__init__.py

```python
"""
Django Permission Engine - Unified Permission Registry (UPR) for Django & DRF
"""
from django.conf import settings

__version__ = "0.1.0"

# Create default registry instance
_default_registry = None


def get_registry():
    """Get or create default registry instance"""
    global _default_registry
    
    if _default_registry is None:
        from .registry import PermissionRegistry
        
        config = getattr(settings, "UPR_CONFIG", {})
        _default_registry = PermissionRegistry(**config)
    
    return _default_registry


# Export registry
registry = get_registry()
```

## Step 3: Write Registry Tests

### tests/test_registry.py

```python
"""
Tests for Permission Registry
"""
import pytest
from django.core.exceptions import ValidationError

from django_permission_engine.registry import (
    PermissionRegistry,
    PermissionDefinition,
)
from django_permission_engine.models import Permission


@pytest.mark.django_db
class TestPermissionRegistry:
    """Test Permission Registry"""
    
    def test_register_module(self):
        """Test registering a module"""
        registry = PermissionRegistry()
        registry.register_module(
            "users",
            crud=["view", "create", "update", "delete"],
        )
        
        assert "users" in registry._modules
        assert len(registry.get_all_permissions()) == 4
    
    def test_register_module_with_actions(self):
        """Test registering module with custom actions"""
        registry = PermissionRegistry()
        registry.register_module(
            "users",
            crud=["view"],
            actions=["reset_password", "export_data"],
        )
        
        permissions = registry.get_all_permissions()
        assert len(permissions) == 3
        assert "users.view" in permissions
        assert "users.reset_password" in permissions
        assert "users.export_data" in permissions
    
    def test_invalid_crud_capability(self):
        """Test invalid CRUD capability"""
        registry = PermissionRegistry()
        
        with pytest.raises(ValidationError):
            registry.register_module(
                "users",
                crud=["invalid"],
            )
    
    def test_duplicate_module(self):
        """Test registering duplicate module"""
        registry = PermissionRegistry()
        registry.register_module("users")
        
        with pytest.raises(ValueError):
            registry.register_module("users")
    
    def test_sync_create_permissions(self):
        """Test syncing creates new permissions"""
        registry = PermissionRegistry()
        registry.register_module(
            "users",
            crud=["view", "create"],
        )
        
        result = registry.sync()
        
        assert len(result["created"]) == 2
        assert Permission.objects.count() == 2
        assert Permission.objects.filter(key="users.view").exists()
        assert Permission.objects.filter(key="users.create").exists()
    
    def test_sync_update_permissions(self):
        """Test syncing updates existing permissions"""
        # Create existing permission
        Permission.objects.create(
            key="users.view",
            module="users",
            capability="view",
            label="Old Label",
        )
        
        registry = PermissionRegistry()
        registry.register_module(
            "users",
            crud=["view"],
        )
        
        result = registry.sync()
        
        assert len(result["updated"]) == 1
        permission = Permission.objects.get(key="users.view")
        assert permission.label == "View Users"
    
    def test_sync_orphaned_permissions(self):
        """Test syncing detects orphaned permissions"""
        # Create orphaned permission
        Permission.objects.create(
            key="users.old_action",
            module="users",
            capability="old_action",
            label="Old Action",
        )
        
        registry = PermissionRegistry(orphan_action="warn")
        registry.register_module("users", crud=["view"])
        
        result = registry.sync()
        
        assert len(result["orphaned"]) == 1
        assert "users.old_action" in result["orphaned"]
    
    def test_sync_dry_run(self):
        """Test sync dry run"""
        registry = PermissionRegistry()
        registry.register_module("users", crud=["view"])
        
        plan = registry.sync(dry_run=True)
        
        assert len(plan["create"]) == 1
        assert Permission.objects.count() == 0  # No changes made
    
    def test_validate(self):
        """Test registry validation"""
        registry = PermissionRegistry()
        registry.register_module("users", crud=["view"])
        
        errors = registry.validate()
        assert len(errors) == 0
    
    def test_get_module_permissions(self):
        """Test getting module permissions"""
        registry = PermissionRegistry()
        registry.register_module("users", crud=["view", "create"])
        registry.register_module("orders", crud=["view"])
        
        users_perms = registry.get_module_permissions("users")
        assert len(users_perms) == 2
        
        orders_perms = registry.get_module_permissions("orders")
        assert len(orders_perms) == 1
```

## Step 4: Initialize Registry on Startup

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
        
        # Initialize registry if configured
        if getattr(settings, "UPR_VALIDATE_ON_STARTUP", False):
            from .registry import get_registry
            registry = get_registry()
            
            # Validate
            errors = registry.validate()
            if errors and registry.strict_mode:
                raise ValidationError(f"Registry validation failed: {errors}")
            
            # Auto-sync if configured
            if getattr(settings, "UPR_AUTO_SYNC", False):
                registry.sync()
```

## Step 5: Test Registry Integration

### Create Test App

```python
# tests/test_app/__init__.py
# Empty file

# tests/test_app/upr_config.py
from django_permission_engine import registry

# Register test modules
registry.register_module(
    "users",
    crud=["view", "create", "update", "delete"],
    actions=["reset_password"],
)

registry.register_module(
    "orders",
    crud=["view", "create", "update", "delete"],
    actions=["cancel", "refund"],
)
```

### Test Integration

```python
# tests/test_registry_integration.py
import pytest
from django_permission_engine import registry
from django_permission_engine.models import Permission


@pytest.mark.django_db
def test_registry_integration():
    """Test registry integration with test app"""
    # Import test app config to register modules
    import tests.test_app.upr_config  # noqa
    
    # Sync permissions
    result = registry.sync()
    
    # Verify permissions created
    assert Permission.objects.count() >= 6  # At least users + orders permissions
    
    # Verify specific permissions
    assert Permission.objects.filter(key="users.view").exists()
    assert Permission.objects.filter(key="users.reset_password").exists()
    assert Permission.objects.filter(key="orders.cancel").exists()
```

## Checklist

- [ ] Registry base class created
- [ ] Module registration implemented
- [ ] Permission generation implemented
- [ ] Sync functionality implemented
- [ ] Validation implemented
- [ ] Registry tests written and passing
- [ ] Registry initialization on startup
- [ ] Integration tests passing

## Next Steps

Once registry engine is complete, proceed to **[04-permission-definition.md](04-permission-definition.md)** to implement the permission definition decorators.
