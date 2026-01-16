# Permission Management API

This document describes the API endpoints for managing user permissions. All endpoints require **admin authentication** (user must be a staff/admin user).

## Base URL

All endpoints are prefixed with `/api/permissions/`

## Authentication

All endpoints require:
- User must be authenticated
- User must be a staff/admin user (`IsAdminUser` permission class)

## Endpoints

### 1. Get User Permissions

Get all permissions assigned to a specific user.

**Endpoint:** `GET /api/permissions/users/{user_id}/`

**Authentication:** Admin only

**Response:**
```json
{
    "user_id": 1,
    "username": "john_doe",
    "permissions": [
        {
            "key": "complaints.view",
            "module": "complaints",
            "capability": "view",
            "label": "View Complaints",
            "granted_at": "2024-01-15T10:30:00Z",
            "granted_by": "admin"
        },
        {
            "key": "complaints.create",
            "module": "complaints",
            "capability": "create",
            "label": "Create Complaints",
            "granted_at": "2024-01-15T10:30:00Z",
            "granted_by": "admin"
        }
    ],
    "total": 2
}
```

**Example:**
```bash
curl -X GET \
  -H "Authorization: Bearer <admin_token>" \
  http://localhost:8000/api/permissions/users/1/
```

---

### 2. Assign Permission to User

Assign a single permission to a user.

**Endpoint:** `POST /api/permissions/users/{user_id}/assign/`

**Authentication:** Admin only

**Request Body:**
```json
{
    "permission_key": "complaints.view"
}
```

**Response:**
```json
{
    "message": "Permission assigned successfully",
    "user_id": 1,
    "permission_key": "complaints.view",
    "created": true
}
```

**Example:**
```bash
curl -X POST \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{"permission_key": "complaints.view"}' \
  http://localhost:8000/api/permissions/users/1/assign/
```

**Status Codes:**
- `201 Created` - Permission assigned (new assignment)
- `200 OK` - Permission already existed, updated granted_by
- `400 Bad Request` - Missing permission_key
- `404 Not Found` - User or permission not found

---

### 3. Revoke Permission from User

Remove a permission from a user.

**Endpoint:** `POST /api/permissions/users/{user_id}/revoke/`

**Authentication:** Admin only

**Request Body:**
```json
{
    "permission_key": "complaints.view"
}
```

**Response:**
```json
{
    "message": "Permission revoked successfully",
    "user_id": 1,
    "permission_key": "complaints.view"
}
```

**Example:**
```bash
curl -X POST \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{"permission_key": "complaints.view"}' \
  http://localhost:8000/api/permissions/users/1/revoke/
```

**Status Codes:**
- `200 OK` - Permission revoked successfully
- `400 Bad Request` - Missing permission_key
- `404 Not Found` - User, permission, or assignment not found

---

### 4. Bulk Assign Permissions

Assign multiple permissions to multiple users at once.

**Endpoint:** `POST /api/permissions/bulk-assign/`

**Authentication:** Admin only

**Request Body:**
```json
{
    "permission_keys": ["complaints.view", "complaints.create", "complaints.update"],
    "user_ids": [1, 2, 3, 4]
}
```

**Response:**
```json
{
    "message": "Permissions assigned successfully",
    "assignments_created": 8,
    "assignments_updated": 4,
    "total_users": 4,
    "total_permissions": 3
}
```

**Example:**
```bash
curl -X POST \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "permission_keys": ["complaints.view", "complaints.create"],
    "user_ids": [1, 2, 3]
  }' \
  http://localhost:8000/api/permissions/bulk-assign/
```

**Status Codes:**
- `201 Created` - Permissions assigned successfully
- `400 Bad Request` - Missing permission_keys or user_ids
- `404 Not Found` - Some users or permissions not found

---

### 5. Bulk Revoke Permissions

Remove multiple permissions from multiple users at once.

**Endpoint:** `POST /api/permissions/bulk-revoke/`

**Authentication:** Admin only

**Request Body:**
```json
{
    "permission_keys": ["complaints.view", "complaints.create"],
    "user_ids": [1, 2, 3]
}
```

**Response:**
```json
{
    "message": "Permissions revoked successfully",
    "revoked_count": 6,
    "total_users": 3,
    "total_permissions": 2
}
```

**Example:**
```bash
curl -X POST \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "permission_keys": ["complaints.view", "complaints.create"],
    "user_ids": [1, 2, 3]
  }' \
  http://localhost:8000/api/permissions/bulk-revoke/
```

**Status Codes:**
- `200 OK` - Permissions revoked successfully
- `400 Bad Request` - Missing permission_keys or user_ids
- `404 Not Found` - Some users or permissions not found

---

## Use Cases

### Assign Role-Based Permissions

Assign permissions based on user type:

**Citizen Users:**
```bash
POST /api/permissions/bulk-assign/
{
    "permission_keys": ["complaints.view", "complaints.create"],
    "user_ids": [1, 2, 3]  # Citizen user IDs
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
    "user_ids": [10, 11, 12]  # Department user IDs
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

### Check User Permissions

Before assigning, check what permissions a user already has:

```bash
GET /api/permissions/users/1/
```

### Remove All Permissions from User

To remove all permissions from a user, first get their permissions, then bulk revoke:

```bash
# 1. Get user permissions
GET /api/permissions/users/1/

# 2. Extract permission keys and bulk revoke
POST /api/permissions/bulk-revoke/
{
    "permission_keys": ["complaints.view", "complaints.create", ...],
    "user_ids": [1]
}
```

---

## Error Responses

All endpoints return errors in the following format:

```json
{
    "error": "Error message here"
}
```

**Common Error Codes:**
- `400 Bad Request` - Invalid request data
- `401 Unauthorized` - Not authenticated
- `403 Forbidden` - Not an admin user
- `404 Not Found` - Resource not found

---

## Integration with Your Project

### Step 1: Add to URLs

The URLs are already included in the library. Make sure your project's `urls.py` includes:

```python
urlpatterns = [
    path('', include('django_permission_engine.urls')),
    # ... other URLs
]
```

### Step 2: Ensure Admin Users

Make sure your admin users have `is_staff=True`:

```python
user.is_staff = True
user.save()
```

### Step 3: Test the API

```bash
# Get admin token (using your authentication method)
# Then test endpoints
curl -X GET \
  -H "Authorization: Bearer <admin_token>" \
  http://localhost:8000/api/permissions/users/1/
```

---

## Security Notes

1. **Admin Only**: All endpoints require admin authentication
2. **No Public Access**: Regular authenticated users cannot access these endpoints
3. **Audit Trail**: All assignments track `granted_by` (the admin who assigned)
4. **Active Permissions Only**: Only active permissions can be assigned
5. **Validation**: All user IDs and permission keys are validated before assignment

---

## Complete Example Workflow

### Scenario: Assign Complaint Permissions to Different User Types

```bash
# 1. Assign to Citizen Users
POST /api/permissions/bulk-assign/
{
    "permission_keys": ["complaints.view", "complaints.create"],
    "user_ids": [1, 2, 3, 4, 5]
}

# 2. Assign to Department Users
POST /api/permissions/bulk-assign/
{
    "permission_keys": [
        "complaints.view",
        "complaints.update",
        "complaints.assign_to_department"
    ],
    "user_ids": [10, 11, 12, 13]
}

# 3. Assign to Government Users (all permissions)
POST /api/permissions/bulk-assign/
{
    "permission_keys": [
        "complaints.view",
        "complaints.create",
        "complaints.update",
        "complaints.delete",
        "complaints.escalate",
        "complaints.close"
    ],
    "user_ids": [20, 21, 22]
}

# 4. Verify assignments
GET /api/permissions/users/1/
GET /api/permissions/users/10/
GET /api/permissions/users/20/
```

---

## Notes

- All permission keys must exist in the database (synced via `python manage.py upr_sync`)
- Only active permissions can be assigned
- Assigning an already-assigned permission updates the `granted_by` field
- Revoking a non-existent assignment returns 404
- Bulk operations are atomic (all or nothing)
