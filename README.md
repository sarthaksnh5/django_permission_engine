# Django Permission Engine

Unified Permission Registry (UPR) for Django & DRF

## Overview

Django Permission Engine provides a single-source, action-aware, declarative permission system for Django and Django REST Framework. It eliminates permission drift and provides a maintainable foundation for complex permission requirements.

## Features

- 🎯 **Single Source of Truth** - Define permissions once, everything else is derived
- 🔑 **Permission Keys** - Simple, immutable, string-based permission identifiers
- 🎬 **Action-Aware** - DRF actions automatically map to permissions
- 📊 **Frontend-Ready** - Permission catalog API for frontend consumption
- 🚫 **Drift Prevention** - Startup validation ensures code and database never drift
- ⚡ **Performance** - O(1) permission checks with optional caching
- ✅ **Opt-In Model** - Only actions defined in UPR config require permissions; others are allowed

## Installation

```bash
pip install django-permission-engine
```

**Note:** This library uses flexible version requirements (minimum versions only) to avoid conflicts with your existing Django and DRF installations. It will work with any compatible version you already have installed.

## Quick Start

### 1. Add to INSTALLED_APPS

```python
INSTALLED_APPS = [
    # ... other apps
    'rest_framework',
    'django_permission_engine',
]
```

### 2. Configure

```python
UPR_CONFIG = {
    'validate_on_startup': True,
    'strict_mode': True,
    'auto_sync': False,
}
```

### 3. Define Permissions

```python
# upr_config.py
from django_permission_engine import module, action

@module('users', label='User Management')
class UsersModule:
    crud = ['view', 'create', 'update', 'delete']
    actions = ['reset_password']
```

### 4. Sync to Database

```bash
python manage.py upr_sync
```

### 5. Assign Permissions to Users

Use the Permission Management API (admin only):

```bash
# Assign permission to user
POST /api/permissions/users/1/assign/
{
    "permission_key": "users.view"
}

# Bulk assign to multiple users
POST /api/permissions/bulk-assign/
{
    "permission_keys": ["users.view", "users.create"],
    "user_ids": [1, 2, 3]
}
```

Or programmatically:

```python
from django_permission_engine.models import Permission, UserPermission

user = User.objects.get(username='john')
permission = Permission.objects.get(key='users.view')
UserPermission.objects.get_or_create(user=user, permission=permission)
```

### 6. Use in ViewSets

```python
from rest_framework import viewsets
from django_permission_engine.permissions import PermissionRequired

class UserViewSet(viewsets.ModelViewSet):
    permission_classes = [PermissionRequired]
    module = 'users'
    queryset = User.objects.all()
    serializer_class = UserSerializer
```

## Documentation

Full documentation is available in the `docs/` folder:

- [Architecture](docs/architecture.md)
- [Core Concepts](docs/core-concepts.md)
- [Permission Definition](docs/permission-definition.md)
- [DRF Integration](docs/drf-integration.md)
- [Opt-In Permissions](docs/opt-in-permissions.md) - Understanding the opt-in permission model
- [API Reference](docs/catalog-api.md)

## Requirements

- Python 3.8+
- Django 3.2+
- Django REST Framework 3.12+

## License

MIT License
