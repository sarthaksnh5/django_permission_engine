# Use Cases

## Who This Library Is For

### Ideal Users

#### 1. Medium to Large Django + DRF Applications

**Characteristics**:
- Multiple modules/domains
- Complex permission requirements
- Need for fine-grained control
- API-first architecture

**Benefits**:
- Scalable permission system
- DRF-native integration
- Frontend-ready catalog
- Maintainable structure

#### 2. API-First Systems

**Characteristics**:
- RESTful APIs
- Frontend/backend separation
- Multiple client applications
- API documentation needs

**Benefits**:
- Permission catalog API
- Consistent permission model
- Frontend integration
- API documentation

#### 3. Multi-Role Organizations

**Characteristics**:
- Multiple user roles
- Complex permission matrices
- Role-based access control
- Permission management UI needs

**Benefits**:
- Hierarchical permission structure
- Role assignment support
- Permission management foundation
- Scalable to many roles

#### 4. Teams with Frontend Permission Management Needs

**Characteristics**:
- Frontend permission checks
- Role editors in UI
- Feature toggles based on permissions
- Permission-aware UI components

**Benefits**:
- Permission catalog API
- Frontend-friendly format
- Self-describing permissions
- Easy integration

### Not Ideal For

#### 1. Very Small Projects

**Characteristics**:
- Simple permission needs
- Few permissions (< 10)
- Basic Django model permissions sufficient

**Why Not Ideal**:
- Overhead of registry system
- More complexity than needed
- Standard Django permissions sufficient

#### 2. Apps Using Only Django Model Permissions

**Characteristics**:
- Only need model-level permissions
- No custom actions
- No fine-grained control needed

**Why Not Ideal**:
- Django's built-in permissions sufficient
- No need for custom permission system
- Additional complexity not justified

## Common Use Cases

### Use Case 1: E-Commerce Platform

**Requirements**:
- User management (view, create, update, delete)
- Order management (view, create, cancel, refund)
- Inventory management (view, adjust, transfer)
- Reporting (view, export)

**UPR Solution**:
```python
@registry.module('users')
class UsersModule:
    crud = ['view', 'create', 'update', 'delete']

@registry.module('orders')
class OrdersModule:
    crud = ['view', 'create', 'update', 'delete']
    actions = ['cancel', 'refund', 'ship']

@registry.module('inventory')
class InventoryModule:
    crud = ['view', 'update']
    actions = ['adjust', 'transfer']

@registry.module('reports')
class ReportsModule:
    crud = ['view']
    actions = ['export']
```

**Benefits**:
- Clear permission structure
- Easy to add new modules
- Frontend can build role editor
- Scalable as platform grows

### Use Case 2: Healthcare Management System

**Requirements**:
- Patient management
- Appointment scheduling
- Medical records access
- Billing operations
- Reporting and analytics

**UPR Solution**:
```python
@registry.module('patients')
class PatientsModule:
    crud = ['view', 'create', 'update', 'delete']
    actions = ['merge_records', 'export_data']

@registry.module('appointments')
class AppointmentsModule:
    crud = ['view', 'create', 'update', 'delete']
    actions = ['reschedule', 'cancel', 'confirm']

@registry.module('medical_records')
class MedicalRecordsModule:
    crud = ['view', 'create', 'update']
    actions = ['share', 'export', 'print']

@registry.module('billing')
class BillingModule:
    crud = ['view', 'create', 'update']
    actions = ['process_payment', 'refund', 'generate_invoice']
```

**Benefits**:
- HIPAA-compliant permission structure
- Fine-grained access control
- Audit trail foundation
- Role-based access for different staff types

### Use Case 3: Project Management Platform

**Requirements**:
- Project management
- Task assignment
- Team collaboration
- Time tracking
- Reporting

**UPR Solution**:
```python
@registry.module('projects')
class ProjectsModule:
    crud = ['view', 'create', 'update', 'delete']
    actions = ['archive', 'restore', 'duplicate']

@registry.module('tasks')
class TasksModule:
    crud = ['view', 'create', 'update', 'delete']
    actions = ['assign', 'reassign', 'complete', 'reopen']

@registry.module('time_tracking')
class TimeTrackingModule:
    crud = ['view', 'create', 'update', 'delete']
    actions = ['approve', 'reject', 'export']

@registry.module('reports')
class ReportsModule:
    crud = ['view']
    actions = ['generate', 'export', 'schedule']
```

**Benefits**:
- Flexible permission model
- Easy to add new project types
- Team-based permissions
- Integration with reporting

### Use Case 4: Content Management System

**Requirements**:
- Content creation and editing
- Media management
- User management
- Publishing workflow
- Analytics

**UPR Solution**:
```python
@registry.module('content')
class ContentModule:
    crud = ['view', 'create', 'update', 'delete']
    actions = ['publish', 'unpublish', 'schedule', 'duplicate']

@registry.module('media')
class MediaModule:
    crud = ['view', 'create', 'update', 'delete']
    actions = ['upload', 'replace', 'delete_permanently']

@registry.module('users')
class UsersModule:
    crud = ['view', 'create', 'update', 'delete']
    actions = ['activate', 'deactivate', 'reset_password']

@registry.module('analytics')
class AnalyticsModule:
    crud = ['view']
    actions = ['export', 'schedule_report']
```

**Benefits**:
- Editorial workflow support
- Role-based content access
- Publishing controls
- Analytics access management

## Decision Matrix

### When to Use UPR

✅ **Use UPR if**:
- You have 20+ permissions
- You need custom action permissions
- You have multiple modules/domains
- You need frontend permission management
- You want to prevent permission drift
- You need scalable permission system
- You have complex permission requirements

❌ **Don't use UPR if**:
- You have < 10 permissions
- Django model permissions are sufficient
- You don't need custom actions
- You have simple permission needs
- You don't need frontend integration
- Overhead is not justified

## Migration from Other Systems

### From Django Model Permissions

**Current State**:
```python
# Django model permissions
class User(models.Model):
    class Meta:
        permissions = [
            ('view_user', 'Can view user'),
            ('change_user', 'Can change user'),
        ]
```

**Migration to UPR**:
```python
# UPR permissions
@registry.module('users')
class UsersModule:
    crud = ['view', 'update']  # Maps to Django permissions
```

**Benefits**:
- More consistent naming
- DRF action awareness
- Frontend catalog
- Better organization

### From Custom Permission System

**Current State**:
```python
# Custom permissions scattered in code
if user.has_perm('can_view_users'):
    ...

if user.has_perm('can_reset_password'):
    ...
```

**Migration to UPR**:
```python
# UPR centralized permissions
@registry.module('users')
class UsersModule:
    crud = ['view']
    actions = ['reset_password']

# Usage
if check_permission(user, 'users.view'):
    ...
```

**Benefits**:
- Single source of truth
- No drift
- Better organization
- Easier maintenance

## Summary

UPR is ideal for:

- ✅ **Medium to large applications** with complex permission needs
- ✅ **API-first systems** requiring frontend integration
- ✅ **Multi-role organizations** with complex permission matrices
- ✅ **Teams needing** permission management UIs

UPR is not ideal for:

- ❌ **Very small projects** with simple needs
- ❌ **Apps using only** Django model permissions
- ❌ **Simple permission requirements** that don't justify the overhead

The library provides the most value when you need a scalable, maintainable, and frontend-friendly permission system that grows with your application.
