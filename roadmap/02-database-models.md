# Phase 2: Database Models

## Overview

This phase covers implementing the database models for permissions and modules.

## Step 1: Create Permission Model

### django_permission_engine/models.py

```python
"""
Database models for UPR
"""
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _
import re


class Permission(models.Model):
    """
    Core permission model.
    
    Represents a single permission with key, module, and capability.
    Permission keys are immutable once created.
    """
    
    key = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
        help_text="Permission key in format: module.capability",
    )
    module = models.CharField(
        max_length=100,
        db_index=True,
        help_text="Module name this permission belongs to",
    )
    capability = models.CharField(
        max_length=100,
        help_text="Capability/action name",
    )
    label = models.CharField(
        max_length=255,
        help_text="Human-readable permission name",
    )
    description = models.TextField(
        blank=True,
        help_text="Detailed permission description",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this permission is active",
    )
    is_deprecated = models.BooleanField(
        default=False,
        help_text="Whether this permission is deprecated",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this permission was created",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When this permission was last updated",
    )
    
    class Meta:
        db_table = "upr_permissions"
        verbose_name = "Permission"
        verbose_name_plural = "Permissions"
        indexes = [
            models.Index(fields=["module"]),
            models.Index(fields=["key"]),
            models.Index(fields=["module", "capability"]),
        ]
        ordering = ["module", "capability"]
    
    def __str__(self):
        return self.key
    
    def clean(self):
        """Validate permission key format"""
        if not self.key:
            raise ValidationError("Permission key is required")
        
        # Validate format: module.capability
        if "." not in self.key:
            raise ValidationError(
                "Permission key must be in format: module.capability"
            )
        
        module, capability = self.key.split(".", 1)
        
        # Validate module matches
        if self.module and self.module != module:
            raise ValidationError(
                f"Module '{self.module}' does not match key prefix '{module}'"
            )
        
        # Validate capability matches
        if self.capability and self.capability != capability:
            raise ValidationError(
                f"Capability '{self.capability}' does not match key suffix '{capability}'"
            )
        
        # Validate key format (lowercase, alphanumeric, underscores, dots)
        if not re.match(r"^[a-z0-9_]+(\.[a-z0-9_]+)+$", self.key):
            raise ValidationError(
                "Permission key must contain only lowercase letters, "
                "numbers, underscores, and dots"
            )
    
    def save(self, *args, **kwargs):
        """Override save to validate and prevent key changes"""
        # If updating existing permission
        if self.pk:
            try:
                original = Permission.objects.get(pk=self.pk)
                # Prevent key changes (immutable)
                if self.key != original.key:
                    raise ValidationError(
                        "Permission keys are immutable and cannot be changed"
                    )
            except Permission.DoesNotExist:
                pass
        
        # Auto-populate module and capability from key
        if self.key and "." in self.key:
            module, capability = self.key.split(".", 1)
            if not self.module:
                self.module = module
            if not self.capability:
                self.capability = capability
        
        # Validate before saving
        self.full_clean()
        super().save(*args, **kwargs)


class Module(models.Model):
    """
    Optional module model for hierarchical organization.
    
    This is optional - modules can also be represented as strings.
    """
    
    key = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
        help_text="Module key (e.g., 'users', 'breakdown.visit')",
    )
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="submodules",
        help_text="Parent module for hierarchical structure",
    )
    label = models.CharField(
        max_length=255,
        help_text="Human-readable module name",
    )
    description = models.TextField(
        blank=True,
        help_text="Module description",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
    )
    updated_at = models.DateTimeField(
        auto_now=True,
    )
    
    class Meta:
        db_table = "upr_modules"
        verbose_name = "Module"
        verbose_name_plural = "Modules"
        ordering = ["key"]
    
    def __str__(self):
        return self.key
    
    def clean(self):
        """Validate module key format"""
        if not self.key:
            raise ValidationError("Module key is required")
        
        # Validate format (lowercase, alphanumeric, underscores, dots)
        if not re.match(r"^[a-z0-9_]+(\.[a-z0-9_]+)*$", self.key):
            raise ValidationError(
                "Module key must contain only lowercase letters, "
                "numbers, underscores, and dots"
            )
```

## Step 2: Create Model Managers

### Add to models.py

```python
class PermissionQuerySet(models.QuerySet):
    """Custom queryset for Permission model"""
    
    def active(self):
        """Return only active permissions"""
        return self.filter(is_active=True)
    
    def deprecated(self):
        """Return only deprecated permissions"""
        return self.filter(is_deprecated=True)
    
    def for_module(self, module):
        """Return permissions for a specific module"""
        return self.filter(module=module)
    
    def for_capability(self, capability):
        """Return permissions for a specific capability"""
        return self.filter(capability=capability)


class PermissionManager(models.Manager):
    """Custom manager for Permission model"""
    
    def get_queryset(self):
        return PermissionQuerySet(self.model, using=self._db)
    
    def active(self):
        return self.get_queryset().active()
    
    def deprecated(self):
        return self.get_queryset().deprecated()
    
    def for_module(self, module):
        return self.get_queryset().for_module(module)
    
    def for_capability(self, capability):
        return self.get_queryset().for_capability(capability)


# Add manager to Permission model
class Permission(models.Model):
    # ... existing fields ...
    
    objects = PermissionManager()
    
    # ... rest of model ...
```

## Step 3: Create Initial Migration

```bash
# Create migrations directory if it doesn't exist
mkdir -p django_permission_engine/migrations

# Create initial migration
python manage.py makemigrations django_permission_engine

# Review the migration file
# It should be in: django_permission_engine/migrations/0001_initial.py
```

### Expected Migration Structure

The migration should create:
- `upr_permissions` table with all Permission fields
- `upr_modules` table with all Module fields
- Appropriate indexes
- Foreign key constraints

## Step 4: Write Model Tests

### tests/test_models.py

```python
"""
Tests for UPR models
"""
import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from django_permission_engine.models import Permission, Module


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
```

## Step 5: Run Tests

```bash
# Run model tests
pytest tests/test_models.py -v

# Run with coverage
pytest tests/test_models.py --cov=django_permission_engine.models --cov-report=html
```

## Step 6: Create Admin Interface (Optional)

### django_permission_engine/admin.py

```python
"""
Admin interface for UPR models
"""
from django.contrib import admin
from django.utils.html import format_html

from .models import Permission, Module


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    """Admin interface for Permission model"""
    
    list_display = [
        "key",
        "module",
        "capability",
        "label",
        "is_active",
        "is_deprecated",
        "created_at",
    ]
    list_filter = [
        "module",
        "is_active",
        "is_deprecated",
        "created_at",
    ]
    search_fields = [
        "key",
        "module",
        "capability",
        "label",
        "description",
    ]
    readonly_fields = [
        "key",
        "created_at",
        "updated_at",
    ]
    fieldsets = (
        (
            "Permission Information",
            {
                "fields": ("key", "module", "capability", "label", "description")
            },
        ),
        (
            "Status",
            {
                "fields": ("is_active", "is_deprecated")
            },
        ),
        (
            "Timestamps",
            {
                "fields": ("created_at", "updated_at")
            },
        ),
    )
    
    def get_readonly_fields(self, request, obj=None):
        """Make key readonly when editing existing permission"""
        if obj:  # Editing existing
            return self.readonly_fields + ["key"]
        return self.readonly_fields


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    """Admin interface for Module model"""
    
    list_display = [
        "key",
        "label",
        "parent",
        "created_at",
    ]
    list_filter = [
        "parent",
        "created_at",
    ]
    search_fields = [
        "key",
        "label",
        "description",
    ]
    readonly_fields = [
        "created_at",
        "updated_at",
    ]
```

## Step 7: Register Models in Admin

### Update django_permission_engine/apps.py

```python
from django.apps import AppConfig


class PermissionEngineConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "django_permission_engine"
    verbose_name = "Permission Engine"
    
    def ready(self):
        # Import admin to register models
        from . import admin  # noqa
```

## Step 8: Test Database Operations

### Create Test Script

```python
# tests/test_db_operations.py
"""
Test database operations
"""
import pytest
from django_permission_engine.models import Permission, Module


@pytest.mark.django_db
def test_create_permissions():
    """Test creating multiple permissions"""
    permissions = [
        Permission.objects.create(
            key=f"users.{action}",
            module="users",
            capability=action,
            label=f"{action.title()} Users",
        )
        for action in ["view", "create", "update", "delete"]
    ]
    
    assert Permission.objects.count() == 4
    assert Permission.objects.for_module("users").count() == 4


@pytest.mark.django_db
def test_permission_queries():
    """Test permission queries"""
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
    
    # Query by module
    users_perms = Permission.objects.for_module("users")
    assert users_perms.count() == 1
    
    # Query by capability
    view_perms = Permission.objects.for_capability("view")
    assert view_perms.count() == 2
    
    # Query active
    Permission.objects.create(
        key="users.create",
        module="users",
        capability="create",
        label="Create Users",
        is_active=False,
    )
    active_perms = Permission.objects.active()
    assert active_perms.count() == 2
```

## Checklist

- [ ] Permission model created with all fields
- [ ] Module model created (optional)
- [ ] Model validation implemented
- [ ] Custom managers and querysets created
- [ ] Initial migration created
- [ ] Model tests written and passing
- [ ] Admin interface created (optional)
- [ ] Database operations tested

## Next Steps

Once models are complete, proceed to **[03-registry-engine.md](03-registry-engine.md)** to implement the registry engine.
