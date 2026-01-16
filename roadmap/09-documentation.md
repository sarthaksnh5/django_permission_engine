# Phase 9: Documentation

## Overview

This phase covers setting up documentation generation and ensuring all code is well-documented.

## Step 1: Set Up Sphinx

### docs/conf.py

```python
"""
Sphinx configuration for UPR documentation
"""
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.abspath('..'))

# Project information
project = 'Django Permission Engine'
copyright = '2024, Your Name'
author = 'Your Name'
release = '0.1.0'

# Extensions
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.viewcode',
    'sphinx.ext.napoleon',
    'sphinx.ext.intersphinx',
]

# Templates
templates_path = ['_templates']

# Exclude patterns
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# HTML theme
html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']

# Intersphinx mapping
intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'django': ('https://docs.djangoproject.com/en/stable/', 'https://docs.djangoproject.com/en/stable/_objects/'),
    'rest_framework': ('https://www.django-rest-framework.org/', None),
}
```

### docs/index.rst

```rst
Django Permission Engine Documentation
======================================

Welcome to the Django Permission Engine documentation.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   installation
   quickstart
   api
   examples

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
```

## Step 2: Add Docstrings to Code

### Example: django_permission_engine/registry.py

```python
class PermissionRegistry:
    """
    Permission Registry
    
    Manages permission definitions and synchronizes with database.
    
    Example:
        >>> registry = PermissionRegistry()
        >>> registry.register_module('users', crud=['view', 'create'])
        >>> registry.sync()
    
    Args:
        validate_on_startup: Validate permissions on application startup
        strict_mode: Fail on inconsistencies
        auto_sync: Automatically sync on startup
        orphan_action: How to handle orphaned permissions ('warn', 'error', 'delete')
    """
    
    def register_module(self, module_name: str, crud: List[str] = None, ...):
        """
        Register a module with its permissions.
        
        Args:
            module_name: Name of the module (e.g., 'users')
            crud: List of CRUD capabilities (e.g., ['view', 'create'])
            actions: List of custom actions (e.g., ['reset_password'])
            label: Human-readable module label
            description: Module description
        
        Raises:
            ValueError: If module is already registered
            ValidationError: If CRUD capabilities are invalid
        
        Example:
            >>> registry.register_module('users', crud=['view', 'create'])
        """
        ...
```

## Step 3: Create API Documentation

### docs/api.rst

```rst
API Reference
=============

Registry
--------

.. automodule:: django_permission_engine.registry
   :members:
   :undoc-members:
   :show-inheritance:

Models
------

.. automodule:: django_permission_engine.models
   :members:
   :undoc-members:
   :show-inheritance:

Permissions
-----------

.. automodule:: django_permission_engine.permissions
   :members:
   :undoc-members:
   :show-inheritance:

Views
-----

.. automodule:: django_permission_engine.views
   :members:
   :undoc-members:
   :show-inheritance:
```

## Step 4: Build Documentation

```bash
# Install Sphinx
pip install sphinx sphinx-rtd-theme

# Build documentation
cd docs
make html

# View documentation
open _build/html/index.html
```

## Step 5: Add Type Hints

### Example: django_permission_engine/permissions.py

```python
from typing import Optional, Set
from django.contrib.auth import get_user_model

User = get_user_model()


class PermissionResolver:
    def resolve(
        self,
        user: User,
        viewset,
        action: str,
        http_method: str,
    ) -> bool:
        """
        Resolve if user has permission for action.
        
        Args:
            user: Authenticated user
            viewset: DRF ViewSet instance
            action: DRF action name
            http_method: HTTP method (GET, POST, etc.)
        
        Returns:
            True if user has permission, False otherwise
        """
        ...
```

## Step 6: Create README Examples

### Update README.md

```markdown
# Django Permission Engine

## Quick Start

### 1. Install

```bash
pip install django-permission-engine
```

### 2. Define Permissions

```python
# upr_config.py
from django_permission_engine import module, action

@module('users', label='User Management')
class UsersModule:
    crud = ['view', 'create', 'update', 'delete']
    actions = ['reset_password']
```

### 3. Sync to Database

```bash
python manage.py upr_sync
```

### 4. Use in ViewSets

```python
from django_permission_engine.permissions import PermissionRequired

class UserViewSet(viewsets.ModelViewSet):
    permission_classes = [PermissionRequired]
    module = 'users'
    ...
```

## Documentation

Full documentation available at [link]
```

## Step 7: Create Changelog

### CHANGELOG.md

```markdown
# Changelog

All notable changes to this project will be documented in this file.

## [0.1.0] - 2024-01-15

### Added
- Initial release
- Permission registry engine
- DRF integration
- Permission catalog API
- Management commands
```

## Checklist

- [ ] Sphinx configured
- [ ] Docstrings added to all public methods
- [ ] Type hints added
- [ ] API documentation generated
- [ ] README updated with examples
- [ ] Changelog created
- [ ] Documentation built successfully

## Next Steps

Once documentation is complete, proceed to **[10-packaging-publishing.md](10-packaging-publishing.md)** to package and publish to PyPI.
