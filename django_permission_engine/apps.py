"""
Django app configuration for Permission Engine
"""
from django.apps import AppConfig


class PermissionEngineConfig(AppConfig):
    """Django app configuration for Permission Engine"""

    default_auto_field = "django.db.models.BigAutoField"
    name = "django_permission_engine"
    verbose_name = "Permission Engine"

    def ready(self):
        """Called when Django starts"""
        from django.conf import settings

        # Get UPR config
        upr_config = getattr(settings, "UPR_CONFIG", {})
        validate_on_startup = upr_config.get("validate_on_startup", False)
        auto_sync = upr_config.get("auto_sync", False)

        # Initialize registry if configured
        if validate_on_startup or auto_sync:
            from .registry import get_registry
            registry = get_registry()

            # Validate
            if validate_on_startup:
                errors = registry.validate()
                if errors and registry.strict_mode:
                    from django.core.exceptions import ValidationError
                    raise ValidationError(f"Registry validation failed: {errors}")

            # Auto-sync if configured
            if auto_sync:
                registry.sync()
