"""
Django Permission Engine - Unified Permission Registry (UPR) for Django & DRF
"""
from .registry import (
    PermissionRegistry,
    PermissionDefinition,
    get_registry,
    registry,
    module,
    action,
)
from .permissions import (
    PermissionResolver,
    PermissionRequired,
)
from .helpers import UPRHelper

__version__ = "0.1.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"

default_app_config = "django_permission_engine.apps.PermissionEngineConfig"

# Lazy-load submodules to avoid AppRegistryNotReady when importing models
# Usage: from django_permission_engine import views, models, urls, helpers, serializers
_SUBMODULES = ("views", "models", "urls", "helpers", "serializers")


def __getattr__(name):
    if name in _SUBMODULES:
        import importlib
        return importlib.import_module(f".{name}", __name__)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "PermissionRegistry",
    "PermissionDefinition",
    "get_registry",
    "registry",
    "module",
    "action",
    "PermissionResolver",
    "PermissionRequired",
    "UPRHelper",
    "views",
    "models",
    "urls",
    "helpers",
    "serializers",
]
