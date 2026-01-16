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

__version__ = "0.1.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"

default_app_config = "django_permission_engine.apps.PermissionEngineConfig"

__all__ = [
    "PermissionRegistry",
    "PermissionDefinition",
    "get_registry",
    "registry",
    "module",
    "action",
    "PermissionResolver",
    "PermissionRequired",
]
