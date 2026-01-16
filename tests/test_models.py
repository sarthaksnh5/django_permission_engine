"""
Tests for UPR models
"""
import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from django_permission_engine.models import Permission, Module, UserPermission
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
class TestPermission:
    """Test Permission model"""

    def test_create_permission(self):
        """Test creating a permission"""
        permission = Permission.objects.create(
            key="users.view",
            module="users",
            capability="view",
            label="View Users",
        )
        assert permission.key == "users.view"
        assert permission.module == "users"
        assert permission.capability == "view"
        assert permission.is_active is True
        assert permission.is_deprecated is False

    def test_permission_key_immutable(self):
        """Test that permission keys cannot be changed"""
        permission = Permission.objects.create(
            key="users.view",
            module="users",
            capability="view",
            label="View Users",
        )

        permission.key = "users.read"
        with pytest.raises(ValidationError):
            permission.save()

    def test_permission_key_validation(self):
        """Test permission key format validation"""
        # Valid key
        permission = Permission(
            key="users.view",
            module="users",
            capability="view",
            label="View Users",
        )
        permission.full_clean()  # Should not raise

        # Invalid key - no dot
        permission.key = "usersview"
        with pytest.raises(ValidationError):
            permission.full_clean()

        # Invalid key - uppercase
        permission.key = "Users.View"
        with pytest.raises(ValidationError):
            permission.full_clean()

        # Invalid key - special characters
        permission.key = "users.view!"
        with pytest.raises(ValidationError):
            permission.full_clean()

    def test_permission_key_unique(self):
        """Test that permission keys must be unique"""
        Permission.objects.create(
            key="users.view",
            module="users",
            capability="view",
            label="View Users",
        )

        with pytest.raises(IntegrityError):
            Permission.objects.create(
                key="users.view",
                module="users",
                capability="view",
                label="View Users",
            )

    def test_auto_populate_module_capability(self):
        """Test that module and capability are auto-populated from key"""
        permission = Permission(
            key="users.view",
            label="View Users",
        )
        permission.save()

        assert permission.module == "users"
        assert permission.capability == "view"

    def test_permission_manager_active(self):
        """Test active() manager method"""
        Permission.objects.create(
            key="users.view",
            module="users",
            capability="view",
            label="View Users",
            is_active=True,
        )
        Permission.objects.create(
            key="users.create",
            module="users",
            capability="create",
            label="Create Users",
            is_active=False,
        )

        active = Permission.objects.active()
        assert active.count() == 1
        assert active.first().key == "users.view"

    def test_permission_manager_for_module(self):
        """Test for_module() manager method"""
        Permission.objects.create(
            key="users.view",
            module="users",
            capability="view",
            label="View Users",
        )
        Permission.objects.create(
            key="orders.view",
            module="orders",
            capability="view",
            label="View Orders",
        )

        users_perms = Permission.objects.for_module("users")
        assert users_perms.count() == 1
        assert users_perms.first().key == "users.view"


@pytest.mark.django_db
class TestModule:
    """Test Module model"""

    def test_create_module(self):
        """Test creating a module"""
        module = Module.objects.create(
            key="users",
            label="User Management",
        )
        assert module.key == "users"
        assert module.label == "User Management"
        assert module.parent is None

    def test_hierarchical_modules(self):
        """Test hierarchical module structure"""
        parent = Module.objects.create(
            key="breakdown",
            label="Breakdown Management",
        )
        child = Module.objects.create(
            key="breakdown.visit",
            label="Visit Management",
            parent=parent,
        )

        assert child.parent == parent
        assert parent.submodules.count() == 1
        assert parent.submodules.first() == child

    def test_module_key_validation(self):
        """Test module key format validation"""
        # Valid key
        module = Module(key="users", label="Users")
        module.full_clean()  # Should not raise

        # Invalid key - uppercase
        module.key = "Users"
        with pytest.raises(ValidationError):
            module.full_clean()


@pytest.mark.django_db
class TestUserPermission:
    """Test UserPermission model"""

    def test_create_user_permission(self):
        """Test creating a user permission"""
        user = User.objects.create_user("testuser", "test@example.com", "password")
        permission = Permission.objects.create(
            key="users.view",
            module="users",
            capability="view",
            label="View Users",
        )

        user_permission = UserPermission.objects.create(
            user=user,
            permission=permission,
        )

        assert user_permission.user == user
        assert user_permission.permission == permission

    def test_user_permission_unique(self):
        """Test that user-permission pairs must be unique"""
        user = User.objects.create_user("testuser", "test@example.com", "password")
        permission = Permission.objects.create(
            key="users.view",
            module="users",
            capability="view",
            label="View Users",
        )

        UserPermission.objects.create(user=user, permission=permission)

        with pytest.raises(IntegrityError):
            UserPermission.objects.create(user=user, permission=permission)
