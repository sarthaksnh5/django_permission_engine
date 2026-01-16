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

    def test_get_all_permission_keys(self):
        """Test getting all permission keys"""
        registry = PermissionRegistry()
        registry.register_module("users", crud=["view", "create"])

        keys = registry.get_all_permission_keys()
        assert "users.view" in keys
        assert "users.create" in keys
        assert len(keys) == 2


@pytest.mark.django_db
class TestPermissionDefinition:
    """Test PermissionDefinition class"""

    def test_permission_definition_creation(self):
        """Test creating a permission definition"""
        perm_def = PermissionDefinition(
            key="users.view",
            module="users",
            capability="view",
            label="View Users",
            description="View user list",
            type="crud",
        )

        assert perm_def.key == "users.view"
        assert perm_def.module == "users"
        assert perm_def.capability == "view"
        assert perm_def.label == "View Users"
        assert perm_def.type == "crud"

    def test_permission_definition_to_dict(self):
        """Test converting permission definition to dict"""
        perm_def = PermissionDefinition(
            key="users.view",
            module="users",
            capability="view",
            label="View Users",
        )

        result = perm_def.to_dict()
        assert result["key"] == "users.view"
        assert result["module"] == "users"
        assert result["capability"] == "view"
        assert result["label"] == "View Users"


@pytest.mark.django_db
class TestGetRegistry:
    """Test get_registry function"""

    def test_get_registry_returns_singleton(self):
        """Test that get_registry returns the same instance"""
        from django_permission_engine.registry import get_registry

        registry1 = get_registry()
        registry2 = get_registry()

        assert registry1 is registry2

    def test_get_registry_with_config(self):
        """Test get_registry uses settings configuration"""
        from django.conf import settings
        from django_permission_engine.registry import get_registry

        # Set config
        settings.UPR_CONFIG = {
            "strict_mode": False,
            "orphan_action": "delete",
        }

        # Clear registry to force recreation
        from django_permission_engine.registry import _default_registry
        import django_permission_engine.registry
        django_permission_engine.registry._default_registry = None

        registry = get_registry()
        assert registry.strict_mode is False
        assert registry.orphan_action == "delete"
