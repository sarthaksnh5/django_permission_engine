# Implementation Plan: Opt-In Permission Model

## Overview

This document outlines the implementation plan for the opt-in permission model feature. The goal is to allow actions that are not defined in the UPR registry to be automatically allowed (no permission check required).

## Current Behavior

Currently, the permission resolver:
1. Checks if ViewSet has a module
2. If no module → allows access
3. If module exists → constructs permission key and checks user permissions
4. If permission key doesn't exist in user's permissions → denies access

**Problem**: Even if an action is not defined in the UPR registry, the system still checks if the user has that permission, which will always fail.

## Desired Behavior

The new opt-in permission model:
1. Checks if ViewSet has a module
2. If no module → allows access (unchanged)
3. If module exists → constructs permission key
4. **NEW**: Check if permission exists in UPR registry
   - If NOT in registry → allows access (opt-in model)
   - If in registry → checks user permissions (existing behavior)

## Implementation Steps

### Step 1: Update PermissionResolver.resolve()

**File**: `django_permission_engine/permissions.py`

**Changes**:
- Add a method `permission_exists_in_registry()` to check if a permission key exists in the registry
- Modify `resolve()` to check registry before checking user permissions
- If permission doesn't exist in registry, return `True` (allow)

**Code Changes**:

```python
def permission_exists_in_registry(self, permission_key: str) -> bool:
    """Check if permission exists in UPR registry"""
    from django_permission_engine import get_registry
    registry = get_registry()
    return permission_key in registry.get_all_permission_keys()

def resolve(self, user, viewset, action: str, http_method: str) -> bool:
    # ... existing code ...
    
    # Construct permission key
    permission_key = self.construct_permission_key(module, capability)
    
    # NEW: Check if permission exists in registry
    if not self.permission_exists_in_registry(permission_key):
        return True  # Not in registry = allow (opt-in model)
    
    # Existing: Check permission
    return self.check_permission(user, permission_key)
```

### Step 2: Update PermissionRequired.has_permission()

**File**: `django_permission_engine/permissions.py`

**Changes**:
- The `has_permission()` method already calls `resolver.resolve()`, so it will automatically benefit from the opt-in model
- No changes needed (inherits behavior from resolver)

### Step 3: Add Registry Method (if needed)

**File**: `django_permission_engine/registry.py`

**Check**: Verify that `get_all_permission_keys()` method exists and returns a set of all permission keys.

**Current Implementation**:
```python
def get_all_permission_keys(self) -> Set[str]:
    """Get all permission keys"""
    return set(self._permissions.keys())
```

This already exists and is correct. No changes needed.

### Step 4: Testing

**Files to Update**:
- `tests/test_permissions.py` - Add tests for opt-in behavior
- `tests/test_integration.py` - Add integration tests

**Test Cases**:

1. **Test: Action not in registry is allowed**
   ```python
   def test_action_not_in_registry_allowed():
       # User has no permissions
       # Action 'xyz' is not in UPR config
       # Result: Should be allowed
   ```

2. **Test: Action in registry requires permission**
   ```python
   def test_action_in_registry_requires_permission():
       # User has no permissions
       # Action 'reset_password' is in UPR config
       # Result: Should be denied
   ```

3. **Test: Action in registry with permission granted**
   ```python
   def test_action_in_registry_with_permission():
       # User has 'users.reset_password' permission
       # Action 'reset_password' is in UPR config
       # Result: Should be allowed
   ```

4. **Test: CRUD action not in crud list**
   ```python
   def test_crud_action_not_in_crud_list():
       # Module has crud = ['view', 'create']
       # DELETE action (destroy) is not in crud list
       # Result: Should be allowed
   ```

## Files to Modify

1. ✅ `django_permission_engine/permissions.py`
   - Add `permission_exists_in_registry()` method
   - Update `resolve()` method

2. ✅ Documentation (already done):
   - `docs/opt-in-permissions.md` - New comprehensive guide
   - `README.md` - Updated features list
   - `SETUP.md` - Added opt-in explanation
   - `docs/runtime-resolution.md` - Updated flow
   - `docs/drf-integration.md` - Added opt-in section

3. ⏳ `tests/test_permissions.py` - Add test cases

4. ⏳ `tests/test_integration.py` - Add integration tests

## Implementation Checklist

- [x] Create comprehensive documentation (`docs/opt-in-permissions.md`)
- [x] Update README.md with opt-in feature
- [x] Update SETUP.md with opt-in explanation
- [x] Update runtime-resolution.md with new flow
- [x] Update drf-integration.md with opt-in section
- [ ] Implement `permission_exists_in_registry()` method
- [ ] Update `resolve()` method to check registry first
- [ ] Add unit tests for opt-in behavior
- [ ] Add integration tests
- [ ] Verify backward compatibility
- [ ] Update changelog

## Backward Compatibility

This change is **backward compatible**:
- Existing permissions continue to work as before
- New behavior only affects actions not in the registry
- No breaking changes to existing APIs

## Security Considerations

**Important Notes**:
1. Authentication is still required (unless using `AllowAny`)
2. Only actions NOT in the registry are allowed
3. All actions in the registry still require proper permissions
4. This is an opt-in model, not a security bypass

## Next Steps

1. Review this implementation plan
2. Implement the code changes
3. Add comprehensive tests
4. Verify all documentation is accurate
5. Test with real-world scenarios
