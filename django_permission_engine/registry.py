"""
Permission Registry Engine

Handles registration and synchronization of permissions.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Set
from django.core.cache import cache
from django.db import transaction
from django.core.exceptions import ValidationError


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

        self._modules: Dict[str, ModuleDefinition] = {}
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

    def _generate_module_permissions(self, module_def: ModuleDefinition):
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
        from .models import Permission
        
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
        existing,  # Permission model instance
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
        from .models import Permission
        
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


# Global registry instance
_default_registry = None


def get_registry() -> PermissionRegistry:
    """Get or create default registry instance"""
    global _default_registry

    if _default_registry is None:
        from django.conf import settings
        config = getattr(settings, "UPR_CONFIG", {})
        _default_registry = PermissionRegistry(**config)

    return _default_registry


# Create default registry instance
registry = get_registry()


# Decorator functions for declarative permission definitions

def module(
    name: str,
    label: Optional[str] = None,
    description: Optional[str] = None,
):
    """
    Decorator to register a module class as a permission module.

    Usage:
        @module('users')
        class UsersModule:
            crud = ['view', 'create', 'update', 'delete']
            actions = ['reset_password']
    """
    def decorator(cls):
        registry = get_registry()

        # Extract CRUD and actions from class
        crud = getattr(cls, 'crud', [])
        actions = getattr(cls, 'actions', [])

        # Collect actions from methods decorated with @action
        for attr_name in dir(cls):
            attr = getattr(cls, attr_name)
            if hasattr(attr, '_upr_action_name'):
                action_name = attr._upr_action_name
                if action_name not in actions:
                    actions.append(action_name)

        # Remove duplicates
        actions = list(set(actions))

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
        @module('users')
        class UsersModule:
            crud = ['view']

            @action('reset_password', label='Reset Password')
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
