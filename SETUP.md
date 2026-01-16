# Setup Guide for Django Permission Engine

This guide explains how to set up and use Django Permission Engine in your Django project.

## Table of Contents

1. [Local Development Setup](#local-development-setup)
2. [Installation in Existing Project](#installation-in-existing-project)
3. [Basic Implementation Steps](#basic-implementation-steps)
4. [Complete Usage Guide](#complete-usage-guide)
5. [Managing User Permissions](#managing-user-permissions)
6. [Testing the Implementation](#testing-the-implementation)

---

## Local Development Setup

### Prerequisites

- Python 3.8 or higher
- Django 3.2 or higher
- Django REST Framework 3.12 or higher
- Virtual environment (recommended)

### Step 1: Clone/Setup the Project

```bash
# Navigate to your project directory
cd /media/sarthak/Projects/python_package/django_permission_engine

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On Linux/Mac:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# Install development dependencies
pip install -r requirements-dev.txt
```

### Step 2: Install Pre-commit Hooks (Optional but Recommended)

```bash
# Install pre-commit hooks
pre-commit install

# Test the hooks
pre-commit run --all-files
```

### Step 3: Run Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=django_permission_engine --cov-report=html

# Run specific test file
pytest tests/test_models.py -v
```

### Step 4: Create Migrations

```bash
# Create migrations
python manage.py makemigrations django_permission_engine

# Apply migrations
python manage.py migrate
```

---

## Installation in Existing Project

### Option 1: Install from Local Development (For Testing)

If you're developing the library and want to test it in your existing Django project:

```bash
# In your existing Django project directory
# Install the package in editable mode
pip install -e /path/to/django_permission_engine

# Or if you're in the library directory
pip install -e .
```

### Option 2: Install from PyPI (When Published)

```bash
pip install django-permission-engine
```

**Important:** This library uses flexible version requirements (minimum versions only) to prevent conflicts with your existing Django and DRF installations. It will work with any compatible version you already have installed and won't force upgrades.

### Step 1: Add to INSTALLED_APPS

In your Django project's `settings.py`:

```python
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third party apps
    'rest_framework',
    
    # Your apps
    'django_permission_engine',  # Add this
]
```

### Step 2: Configure UPR Settings

Add UPR configuration to your `settings.py`:

```python
# UPR Configuration
UPR_CONFIG = {
    'validate_on_startup': True,  # Validate permissions on startup
    'strict_mode': True,           # Fail on inconsistencies (production)
    'auto_sync': False,            # Don't auto-sync (use management command)
    'orphan_action': 'warn',       # How to handle orphaned permissions
}
```

### Step 3: Run Migrations

```bash
# Create migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate
```

### Step 4: Add URL Configuration (For Catalog API)

In your project's main `urls.py`:

```python
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('django_permission_engine.urls')),  # Add this
    # ... other URLs
]
```

---

## Basic Implementation Steps

### Step 1: Define Your Permissions

Create a file `upr_config.py` in your Django app (or project root):

```python
# myapp/upr_config.py
from django_permission_engine import module, action

# Register a module with CRUD permissions
@module('users', label='User Management')
class UsersModule:
    crud = ['view', 'create', 'update', 'delete']
    actions = ['reset_password', 'export_data']

# Register another module
@module('orders', label='Order Management')
class OrdersModule:
    crud = ['view', 'create', 'update', 'delete']
    actions = ['cancel', 'refund', 'ship']
```

**Important**: Make sure this file is imported when Django starts. You can:

1. Import it in your app's `apps.py`:
```python
# myapp/apps.py
from django.apps import AppConfig

class MyAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'myapp'
    
    def ready(self):
        import myapp.upr_config  # Import to register modules
```

2. Or import it in your app's `__init__.py`:
```python
# myapp/__init__.py
default_app_config = 'myapp.apps.MyAppConfig'
```

### Step 2: Sync Permissions to Database

```bash
# Sync permissions from code to database
python manage.py upr_sync

# Or with verbose output
python manage.py upr_sync --verbose

# Dry run to see what would change
python manage.py upr_sync --dry-run
```

### Step 3: Assign Permissions to Users

You have **two options** to assign permissions:

#### Option A: Using the Permission Management API (Recommended)

The library provides a complete REST API for managing user permissions. **All endpoints require admin authentication** (`is_staff=True`).

**1. Assign a single permission to a user:**
```bash
POST /api/permissions/users/{user_id}/assign/

# Request body:
{
    "permission_key": "users.view"
}
```

**Example:**
```bash
curl -X POST \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{"permission_key": "users.view"}' \
  http://localhost:8000/api/permissions/users/1/assign/
```

**2. Bulk assign permissions to multiple users:**
```bash
POST /api/permissions/bulk-assign/

# Request body:
{
    "permission_keys": ["users.view", "users.create", "users.update"],
    "user_ids": [1, 2, 3, 4, 5]
}
```

**Example:**
```bash
curl -X POST \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "permission_keys": ["users.view", "users.create"],
    "user_ids": [1, 2, 3]
  }' \
  http://localhost:8000/api/permissions/bulk-assign/
```

**3. Revoke a permission from a user:**
```bash
POST /api/permissions/users/{user_id}/revoke/

# Request body:
{
    "permission_key": "users.view"
}
```

**4. Get all permissions for a user:**
```bash
GET /api/permissions/users/{user_id}/
```

**5. Bulk revoke permissions:**
```bash
POST /api/permissions/bulk-revoke/

# Request body:
{
    "permission_keys": ["users.view", "users.create"],
    "user_ids": [1, 2, 3]
}
```

**Note:** All API endpoints require admin authentication. Make sure your admin user has `is_staff=True`.

**Full API Documentation:** See [Permission Management API](docs/permission-management-api.md) for complete details.

#### Option B: Programmatic Assignment (Python Code)

You can also assign permissions programmatically:

```python
from django_permission_engine.models import Permission, UserPermission
from django.contrib.auth import get_user_model

User = get_user_model()

# Get a user
user = User.objects.get(username='john')

# Get a permission
permission = Permission.objects.get(key='users.view')

# Assign permission
UserPermission.objects.get_or_create(
    user=user,
    permission=permission
)

# Or assign multiple permissions
permissions = Permission.objects.filter(module='users')
for perm in permissions:
    UserPermission.objects.get_or_create(user=user, permission=perm)
```

### Step 4: Use in ViewSets

```python
# myapp/views.py
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django_permission_engine.permissions import PermissionRequired

class UserViewSet(viewsets.ModelViewSet):
    permission_classes = [PermissionRequired]
    module = 'users'  # Required: Declare module
    queryset = User.objects.all()
    serializer_class = UserSerializer
    
    @action(detail=True, methods=['post'])
    def reset_password(self, request, pk=None):
        """
        Reset user password.
        Automatically requires 'users.reset_password' permission.
        """
        user = self.get_object()
        # ... reset password logic ...
        return Response({'status': 'password reset'})
    
    @action(detail=False, methods=['get'])
    def export_data(self, request):
        """
        Export user data.
        Automatically requires 'users.export_data' permission.
        """
        # ... export logic ...
        return Response({'data': ...})
```

---

## Complete Usage Guide

### Defining Permissions

#### Simple Module with CRUD

```python
from django_permission_engine import module

@module('users')
class UsersModule:
    crud = ['view', 'create', 'update', 'delete']
```

This creates:
- `users.view`
- `users.create`
- `users.update`
- `users.delete`

#### Module with Custom Actions

```python
from django_permission_engine import module, action

@module('users')
class UsersModule:
    crud = ['view', 'create', 'update', 'delete']
    actions = ['reset_password', 'export_data']
    
    @action('bulk_delete', label='Bulk Delete Users')
    def bulk_delete(self):
        """Bulk delete action"""
        pass
```

This creates all CRUD permissions plus:
- `users.reset_password`
- `users.export_data`
- `users.bulk_delete`

#### Hierarchical Modules

```python
@module('breakdown')
class BreakdownModule:
    crud = ['view', 'create', 'update', 'delete']

@module('breakdown.visit')
class BreakdownVisitModule:
    crud = ['view', 'create', 'update']
    actions = ['assign_engineer', 'close', 'reopen']
```

This creates:
- `breakdown.view`, `breakdown.create`, etc.
- `breakdown.visit.view`, `breakdown.visit.create`, etc.
- `breakdown.visit.assign_engineer`, `breakdown.visit.close`, etc.

### Using Permissions in ViewSets

#### Basic ViewSet

```python
from rest_framework import viewsets
from django_permission_engine.permissions import PermissionRequired

class UserViewSet(viewsets.ModelViewSet):
    permission_classes = [PermissionRequired]
    module = 'users'  # Required!
    queryset = User.objects.all()
    serializer_class = UserSerializer
```

**Automatic Permission Mapping:**
- `GET /api/users/` → requires `users.view`
- `GET /api/users/1/` → requires `users.view`
- `POST /api/users/` → requires `users.create`
- `PUT /api/users/1/` → requires `users.update`
- `PATCH /api/users/1/` → requires `users.update`
- `DELETE /api/users/1/` → requires `users.delete`

#### ViewSet with Custom Actions

```python
class UserViewSet(viewsets.ModelViewSet):
    permission_classes = [PermissionRequired]
    module = 'users'
    queryset = User.objects.all()
    serializer_class = UserSerializer
    
    @action(detail=True, methods=['post'])
    def reset_password(self, request, pk=None):
        # Automatically requires 'users.reset_password' permission
        user = self.get_object()
        # ... reset password logic ...
        return Response({'status': 'password reset'})
```

**Important**: The action name must match the permission capability name exactly.

#### Read-Only ViewSet

```python
from rest_framework import viewsets

class ReportViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [PermissionRequired]
    module = 'reports'
    queryset = Report.objects.all()
    serializer_class = ReportSerializer
```

Only requires `reports.view` permission.

---

## Managing User Permissions

This section explains how to assign, update, and revoke permissions for users. You have **two methods** available:

1. **Using the Permission Management API** (Recommended - Admin only)
2. **Programmatic Assignment** (Using Python code)

### Method 1: Using the Permission Management API (Recommended)

The library provides a complete REST API for managing user permissions. **All endpoints require admin authentication** (`is_staff=True`).

#### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/permissions/users/{user_id}/` | Get all permissions for a user |
| `POST` | `/api/permissions/users/{user_id}/assign/` | Assign a permission to a user |
| `POST` | `/api/permissions/users/{user_id}/revoke/` | Revoke a permission from a user |
| `POST` | `/api/permissions/bulk-assign/` | Bulk assign permissions to multiple users |
| `POST` | `/api/permissions/bulk-revoke/` | Bulk revoke permissions from multiple users |

#### 1. Assign Permission to User

Assign a single permission to a user:

```bash
POST /api/permissions/users/{user_id}/assign/

# Request body:
{
    "permission_key": "users.view"
}
```

**Example:**
```bash
curl -X POST \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{"permission_key": "users.view"}' \
  http://localhost:8000/api/permissions/users/1/assign/
```

**Response:**
```json
{
    "message": "Permission assigned successfully",
    "user_id": 1,
    "permission_key": "users.view",
    "created": true
}
```

#### 2. Bulk Assign Permissions

Assign multiple permissions to multiple users at once:

```bash
POST /api/permissions/bulk-assign/

# Request body:
{
    "permission_keys": ["users.view", "users.create", "users.update"],
    "user_ids": [1, 2, 3, 4, 5]
}
```

**Example:**
```bash
curl -X POST \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "permission_keys": ["users.view", "users.create"],
    "user_ids": [1, 2, 3]
  }' \
  http://localhost:8000/api/permissions/bulk-assign/
```

**Response:**
```json
{
    "message": "Permissions assigned successfully",
    "assignments_created": 6,
    "assignments_updated": 0,
    "total_users": 3,
    "total_permissions": 2
}
```

#### 3. Revoke Permission from User

Remove a permission from a user:

```bash
POST /api/permissions/users/{user_id}/revoke/

# Request body:
{
    "permission_key": "users.view"
}
```

**Example:**
```bash
curl -X POST \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{"permission_key": "users.view"}' \
  http://localhost:8000/api/permissions/users/1/revoke/
```

#### 4. Get User Permissions

View all permissions assigned to a user:

```bash
GET /api/permissions/users/{user_id}/
```

**Example:**
```bash
curl -X GET \
  -H "Authorization: Bearer <admin_token>" \
  http://localhost:8000/api/permissions/users/1/
```

**Response:**
```json
{
    "user_id": 1,
    "username": "john_doe",
    "permissions": [
        {
            "key": "users.view",
            "module": "users",
            "capability": "view",
            "label": "View Users",
            "granted_at": "2024-01-15T10:30:00Z",
            "granted_by": "admin"
        }
    ],
    "total": 1
}
```

#### 5. Bulk Revoke Permissions

Remove multiple permissions from multiple users:

```bash
POST /api/permissions/bulk-revoke/

# Request body:
{
    "permission_keys": ["users.view", "users.create"],
    "user_ids": [1, 2, 3]
}
```

**Example:**
```bash
curl -X POST \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "permission_keys": ["users.view", "users.create"],
    "user_ids": [1, 2, 3]
  }' \
  http://localhost:8000/api/permissions/bulk-revoke/
```

#### Important Notes

- **Admin Only**: All endpoints require admin authentication (`is_staff=True`)
- **Permission Keys**: Must exist in database (synced via `python manage.py upr_sync`)
- **Active Permissions**: Only active permissions can be assigned
- **Audit Trail**: All assignments track `granted_by` (who assigned the permission)
- **Idempotent**: Assigning an already-assigned permission updates the `granted_by` field

**Full API Documentation:** See [Permission Management API](docs/permission-management-api.md) for complete details with all request/response examples.

### Method 2: Programmatic Assignment (Python Code)

You can also assign permissions programmatically using Python:

#### Single Permission Assignment

```python
from django_permission_engine.models import Permission, UserPermission
from django.contrib.auth import get_user_model

User = get_user_model()

# Get user and permission
user = User.objects.get(username='john')
permission = Permission.objects.get(key='users.view')

# Assign permission
UserPermission.objects.get_or_create(
    user=user,
    permission=permission,
    defaults={'granted_by': request.user}  # Optional: track who granted it
)
```

#### Multiple Permissions Assignment

```python
# Assign all permissions for a module
user = User.objects.get(username='john')
permissions = Permission.objects.filter(module='users')

for perm in permissions:
    UserPermission.objects.get_or_create(
        user=user,
        permission=perm
    )
```

#### Bulk Assignment

```python
# Bulk assign permissions to a user
user = User.objects.get(username='john')
permissions = Permission.objects.filter(
    key__in=['users.view', 'users.create', 'users.update']
)

UserPermission.objects.bulk_create([
    UserPermission(user=user, permission=perm)
    for perm in permissions
], ignore_conflicts=True)
```

#### Remove Permission

```python
# Remove a specific permission
user = User.objects.get(username='john')
permission = Permission.objects.get(key='users.view')

UserPermission.objects.filter(
    user=user,
    permission=permission
).delete()
```

#### Remove All Permissions from User

```python
# Remove all permissions from a user
user = User.objects.get(username='john')
UserPermission.objects.filter(user=user).delete()
```

### Common Use Cases

#### Assign Role-Based Permissions

**Citizen Users:**
```bash
POST /api/permissions/bulk-assign/
{
    "permission_keys": ["complaints.view", "complaints.create"],
    "user_ids": [1, 2, 3, 4, 5]  # Citizen user IDs
}
```

**Department Users:**
```bash
POST /api/permissions/bulk-assign/
{
    "permission_keys": [
        "complaints.view",
        "complaints.update",
        "complaints.assign_to_department"
    ],
    "user_ids": [10, 11, 12, 13]  # Department user IDs
}
```

**Government Users:**
```bash
POST /api/permissions/bulk-assign/
{
    "permission_keys": [
        "complaints.view",
        "complaints.create",
        "complaints.update",
        "complaints.delete",
        "complaints.escalate"
    ],
    "user_ids": [20, 21, 22]  # Government user IDs
}
```

### Assigning Permissions

#### Programmatic Assignment

```python
from django_permission_engine.models import Permission, UserPermission
from django.contrib.auth import get_user_model

User = get_user_model()

# Single permission
user = User.objects.get(username='john')
permission = Permission.objects.get(key='users.view')
UserPermission.objects.get_or_create(user=user, permission=permission)

# Multiple permissions
permissions = Permission.objects.filter(module='users')
for perm in permissions:
    UserPermission.objects.get_or_create(user=user, permission=perm)
```

#### Bulk Assignment

```python
# Assign all permissions for a module
user = User.objects.get(username='john')
permissions = Permission.objects.filter(module='users')
UserPermission.objects.bulk_create([
    UserPermission(user=user, permission=perm)
    for perm in permissions
], ignore_conflicts=True)
```

### Using Permission Catalog API

#### Get Full Catalog

```bash
GET /api/permissions/catalog/
```

Response:
```json
{
  "modules": [
    {
      "key": "users",
      "label": "User Management",
      "permissions": [
        {
          "key": "users.view",
          "label": "View Users",
          "type": "crud",
          "is_active": true
        }
      ]
    }
  ],
  "total_permissions": 52,
  "total_modules": 8
}
```

#### Get Module Catalog

```bash
GET /api/permissions/catalog/users/
```

#### Filter Catalog

```bash
# Filter by module
GET /api/permissions/catalog/?module=users

# Filter by type
GET /api/permissions/catalog/?type=crud

# Active only
GET /api/permissions/catalog/?active_only=true

# Search
GET /api/permissions/catalog/?search=password
```

### Management Commands

#### Sync Permissions

```bash
# Sync permissions from code to database
python manage.py upr_sync

# Dry run (see what would change)
python manage.py upr_sync --dry-run

# Clean orphaned permissions
python manage.py upr_sync --clean-orphans

# Verbose output
python manage.py upr_sync --verbose
```

#### Validate Permissions

```bash
# Validate permission consistency
python manage.py upr_validate

# With verbose output
python manage.py upr_validate --verbose
```

#### List Permissions

```bash
# List all permissions
python manage.py upr_list

# Filter by module
python manage.py upr_list --module users

# Filter by type
python manage.py upr_list --type crud

# JSON format
python manage.py upr_list --format json

# Simple format (just keys)
python manage.py upr_list --format simple
```

---

## Testing the Implementation

### Quick Test

```bash
# 1. Define permissions in upr_config.py
# 2. Sync to database
python manage.py upr_sync

# 3. Verify permissions created
python manage.py upr_list

# 4. Assign permissions to a user
python manage.py shell
```

In Django shell:
```python
from django.contrib.auth import get_user_model
from django_permission_engine.models import Permission, UserPermission

User = get_user_model()
user = User.objects.get(username='your_username')
permission = Permission.objects.get(key='users.view')
UserPermission.objects.create(user=user, permission=permission)
```

### Test ViewSet Permissions

```python
# Test API endpoint
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

User = get_user_model()
client = APIClient()

# Create user and assign permission
user = User.objects.create_user('testuser', 'test@example.com', 'password')
# ... assign permission ...

# Authenticate
client.force_authenticate(user=user)

# Test endpoint
response = client.get('/api/users/')
print(response.status_code)  # Should be 200 if permission granted
```

### Test Catalog API

```bash
# Start server
python manage.py runserver

# Test endpoint (requires authentication)
curl -H "Authorization: Bearer <token>" http://localhost:8000/api/permissions/catalog/
```

---

## Common Issues and Solutions

### Issue: Migration Errors

**Solution:**
```bash
# Delete migrations and recreate
rm django_permission_engine/migrations/0001_initial.py
python manage.py makemigrations django_permission_engine
python manage.py migrate
```

### Issue: Import Errors

**Solution:**
- Make sure `django_permission_engine` is in `INSTALLED_APPS`
- Check that the package is installed: `pip list | grep django-permission-engine`
- Verify Python path includes the package

### Issue: Permission Not Found

**Solution:**
- Run `python manage.py upr_sync` to sync permissions
- Check that permissions are defined in `upr_config.py`
- Verify module is registered correctly
- Make sure `upr_config.py` is imported when Django starts

### Issue: ViewSet Permission Not Working

**Solution:**
- Check that `module` attribute is set on ViewSet
- Verify permission exists in database: `python manage.py upr_list`
- Check that user has permission assigned
- Verify action name matches permission capability name exactly

### Issue: Catalog API Returns 401

**Solution:**
- Catalog API requires authentication
- Make sure user is authenticated
- Or change permission class in `views.py` if needed

---

## Best Practices

### 1. Organize Permissions by Business Domain

```python
# ✅ Good: Business domain
@module('customer_orders')
class CustomerOrdersModule:
    crud = ['view', 'create']

# ❌ Bad: Technical structure
@module('api_v1_orders')
class APIOrdersModule:
    crud = ['view', 'create']
```

### 2. Use Consistent Naming

```python
# ✅ Good: Consistent
@module('users')
class UsersModule:
    actions = ['reset_password']

@action(detail=True, methods=['post'])
def reset_password(self, request, pk=None):
    # Action name matches permission
    ...

# ❌ Bad: Inconsistent
@module('users')
class UsersModule:
    actions = ['reset_password']

@action(detail=True, methods=['post'], name='reset-password')
def reset_password(self, request, pk=None):
    # Action name doesn't match permission!
    ...
```

### 3. Always Declare Module in ViewSets

```python
# ✅ Good
class UserViewSet(viewsets.ModelViewSet):
    module = 'users'

# ❌ Bad
class UserViewSet(viewsets.ModelViewSet):
    # No module = deny all requests
```

### 4. Sync Permissions Regularly

```bash
# After adding new permissions
python manage.py upr_sync

# Before deployment
python manage.py upr_validate
python manage.py upr_sync
```

### 5. Use Dry Run Before Sync

```bash
# Always check what will change
python manage.py upr_sync --dry-run

# Then sync
python manage.py upr_sync
```

---

## Next Steps

1. **Define Your Permissions** - Create `upr_config.py` with your modules
2. **Sync to Database** - Run `python manage.py upr_sync`
3. **Assign Permissions** - Create your permission assignment system
4. **Use in ViewSets** - Add `PermissionRequired` to your ViewSets
5. **Test** - Verify permissions work as expected

---

## Permission Management API

The library includes a complete API for managing user permissions (admin only).

### Quick Start

All endpoints are available at `/api/permissions/`:

- `GET /api/permissions/users/{user_id}/` - Get user permissions
- `POST /api/permissions/users/{user_id}/assign/` - Assign permission
- `POST /api/permissions/users/{user_id}/revoke/` - Revoke permission
- `POST /api/permissions/bulk-assign/` - Bulk assign permissions
- `POST /api/permissions/bulk-revoke/` - Bulk revoke permissions

**Full Documentation:** See [Permission Management API](docs/permission-management-api.md)

### Example: Assign Permissions to User

```bash
# Assign single permission
curl -X POST \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{"permission_key": "complaints.view"}' \
  http://localhost:8000/api/permissions/users/1/assign/

# Bulk assign to multiple users
curl -X POST \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "permission_keys": ["complaints.view", "complaints.create"],
    "user_ids": [1, 2, 3]
  }' \
  http://localhost:8000/api/permissions/bulk-assign/
```

**Note:** All endpoints require admin authentication (`is_staff=True`).

---

## Need Help?

- Check the [documentation](docs/README.md) for detailed concepts
- Review the [roadmap](roadmap/README.md) for implementation details
- Check examples in `docs_sphinx/examples.rst`
- See [Permission Management API](docs/permission-management-api.md) for permission assignment
