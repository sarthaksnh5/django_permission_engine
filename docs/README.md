# Unified Permission Registry (UPR) for Django & DRF

## Overview

**UPR** is a single-source, action-aware, declarative permission system for Django and Django REST Framework (DRF). It provides a unified approach to managing permissions that scales from small applications to enterprise-level systems with hundreds or thousands of permissions.

## What Problem Does This Library Solve?

Modern Django + DRF applications need:

- **Permissions beyond Django's model permissions** - Standard model permissions are too coarse-grained
- **Fine-grained control** over:
  - Modules
  - CRUD operations
  - Custom DRF actions
- **A single permission system** that:
  - Is API-aware
  - Is frontend-friendly
  - Is scalable to hundreds/thousands of permissions
  - Does not drift between DB, API, and code

UPR provides a **single-source, action-aware, declarative permission system** that eliminates permission drift and provides a maintainable foundation for complex permission requirements.

## Core Philosophy

This library is built on **four non-negotiable principles**:

1. **Single Source of Truth** - Permissions are defined once, everything else is derived
2. **Keys, Not Rows** - Permission checks operate on permission keys, database rows are an implementation detail
3. **Action Awareness** - DRF actions are first-class permission targets, CRUD ≠ enough
4. **Declarative, Not Imperative** - Permissions are described, not hand-wired, the system infers behavior automatically

## What the Library Is (and Is Not)

### ✅ The library IS

- A **permission registry**
- A **permission synchronization engine**
- A **DRF-aware permission resolver**
- A **permission catalog API**
- A **foundation for RBAC and UI permission editors**

### ❌ The library IS NOT

- A UI/admin panel (intentionally excluded)
- A role management system (optional extension)
- An auth system (relies on Django auth)
- An object-level permission engine

## Quick Start

```python
# 1. Define your permissions
from upr import PermissionRegistry

registry = PermissionRegistry()

@registry.module('users')
class UsersModule:
    crud = ['view', 'create', 'update', 'delete']
    actions = ['reset_password', 'export_data']

# 2. Sync to database
python manage.py upr_sync

# 3. Use in your ViewSets
from upr.permissions import PermissionRequired

class UserViewSet(viewsets.ModelViewSet):
    permission_classes = [PermissionRequired]
    module = 'users'
    
    @action(detail=True, methods=['post'])
    def reset_password(self, request, pk=None):
        # Automatically requires 'users.reset_password' permission
        ...
```

## Documentation Structure

### Core Concepts

- **[Architecture](architecture.md)** - High-level system architecture and layers
- **[Core Concepts](core-concepts.md)** - Permission keys, modules, capabilities, and domain model
- **[Permission Definition](permission-definition.md)** - How to define permissions declaratively

### Core Components

- **[Registry Engine](registry-engine.md)** - Permission registration and synchronization
- **[Runtime Resolution](runtime-resolution.md)** - How permissions are checked at runtime
- **[DRF Integration](drf-integration.md)** - Integration with Django REST Framework
- **[Persistence](persistence.md)** - Database models and storage

### Advanced Topics

- **[CRUD Normalization](crud-normalization.md)** - How CRUD permissions are standardized
- **[Action Coupling](action-coupling.md)** - DRF action to permission mapping
- **[Drift Prevention](drift-prevention.md)** - Preventing permission inconsistencies

### APIs and Interfaces

- **[Permission Catalog API](catalog-api.md)** - Frontend-ready permission catalog

### Operations

- **[Performance & Scalability](performance.md)** - Performance characteristics and optimization
- **[Security Model](security.md)** - Security guarantees and best practices
- **[Versioning & Compatibility](versioning.md)** - Handling permission changes over time
- **[Deployment & Lifecycle](deployment.md)** - Deployment strategies and lifecycle management

### Usage Guides

- **[Roles & Users](roles-users.md)** - Managing permission assignments
- **[Use Cases](use-cases.md)** - Who this library is for and when to use it

## Key Features

### 🎯 Single Source of Truth

Define permissions once in code. The registry ensures database, API, and frontend stay in sync.

### 🔑 Permission Keys

Simple, immutable, string-based permission identifiers:
```
users.view
users.create
users.reset_password
breakdown.visit.assign_engineer
```

### 🎬 Action-Aware

DRF actions automatically map to permissions. No manual wiring required.

### 📊 Frontend-Ready

Permission catalog API provides hierarchical, self-describing permission data for frontend consumption.

### 🚫 Drift Prevention

Startup validation ensures code and database never drift apart.

### ⚡ Performance

O(1) permission checks with optional caching. Scales to thousands of permissions.

## Installation

```bash
pip install django-permission-engine
```

## Requirements

- Django 3.2+
- Django REST Framework 3.12+
- Python 3.8+

## License

[Your License Here]

## Contributing

[Contributing Guidelines]

## Support

[Support Information]
