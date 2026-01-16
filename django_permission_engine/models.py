"""
Database models for UPR
"""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from django.utils.translation import gettext_lazy as _
import re


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

    objects = PermissionManager()

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


class UserPermission(models.Model):
    """
    Model for assigning permissions to users.

    This is optional - applications can use their own assignment models.
    
    Uses settings.AUTH_USER_MODEL to support custom user models.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="upr_permissions",
    )
    permission = models.ForeignKey(
        Permission,
        on_delete=models.CASCADE,
        related_name="user_assignments",
    )
    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="upr_granted_permissions",
    )
    granted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "upr_user_permissions"
        unique_together = ["user", "permission"]
        verbose_name = "User Permission"
        verbose_name_plural = "User Permissions"

    def __str__(self):
        # Use getattr to safely access username attribute
        username = getattr(self.user, 'username', str(self.user))
        return f"{username} - {self.permission.key}"


# Signal handlers for cache invalidation
@receiver([post_save, post_delete], sender=UserPermission)
def invalidate_user_permission_cache(sender, instance, **kwargs):
    """Invalidate user permission cache when permissions change"""
    cache_key = f'user_permissions:{instance.user.id}'
    cache.delete(cache_key)


@receiver([post_save, post_delete], sender=Permission)
def invalidate_permission_cache(sender, instance, **kwargs):
    """Invalidate permission catalog cache when permissions change"""
    cache.delete('permission_catalog')
