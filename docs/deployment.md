# Deployment & Lifecycle

## Overview

This document covers the deployment process, lifecycle management, and operational considerations for UPR.

## Typical Lifecycle

### 1. Define Permissions

```python
# upr_config.py
from upr import PermissionRegistry

registry = PermissionRegistry()

@registry.module('users')
class UsersModule:
    crud = ['view', 'create', 'update', 'delete']
    actions = ['reset_password']
```

### 2. Run Registry Sync

```bash
# Development
python manage.py upr_sync

# Production (as part of deployment)
python manage.py upr_sync --no-input
```

### 3. Assign Permissions

```python
# Through your application's permission management
user.assign_permission('users.view')
user.assign_permission('users.create')
```

### 4. Deploy Safely

```bash
# Deploy application
# Permissions are already synced
# Application starts with validated permissions
```

## Deployment Process

### Pre-Deployment

1. **Review Permission Changes**
   ```bash
   # Check what will change
   python manage.py upr_sync --dry-run
   ```

2. **Validate Permissions**
   ```bash
   # Ensure consistency
   python manage.py upr_validate
   ```

3. **Test Locally**
   ```bash
   # Test sync process
   python manage.py upr_sync
   python manage.py test
   ```

### Deployment Steps

1. **Backup Database**
   ```bash
   python manage.py dumpdata upr > backup.json
   ```

2. **Deploy Code**
   ```bash
   # Deploy new code with permission definitions
   git pull
   pip install -r requirements.txt
   ```

3. **Run Migrations**
   ```bash
   python manage.py migrate
   ```

4. **Sync Permissions**
   ```bash
   python manage.py upr_sync
   ```

5. **Validate**
   ```bash
   python manage.py upr_validate
   ```

6. **Restart Application**
   ```bash
   # Application validates on startup
   systemctl restart your-app
   ```

### Post-Deployment

1. **Verify Permissions**
   ```bash
   # Check permission catalog
   curl https://your-app.com/api/permissions/catalog/
   ```

2. **Monitor Logs**
   ```bash
   # Check for permission-related errors
   tail -f /var/log/app.log | grep -i permission
   ```

3. **Check Health**
   ```bash
   # Verify application health
   curl https://your-app.com/health/
   ```

## Failure Modes

### App Refuses to Start

**Cause**: Registry validation fails

**Error**:
```
ValidationError: Permission 'users.new_action' is defined in code but not in database.
Run 'python manage.py upr_sync' to synchronize.
```

**Solution**:
1. Run `python manage.py upr_sync`
2. Fix any validation errors
3. Restart application

### Orphaned Permissions

**Cause**: Permissions in database but not in code

**Warning**:
```
Warning: Orphaned permission found: users.old_action
```

**Solution**:
1. Check if permission should be removed
2. If yes, remove assignments first
3. Remove from code
4. Run `python manage.py upr_sync --clean-orphans`

### Missing Permissions

**Cause**: Permissions in code but not in database

**Error**:
```
Error: Permission 'users.new_action' is defined in code but not in database.
```

**Solution**:
1. Run `python manage.py upr_sync`
2. Verify permissions created
3. Check database

## Configuration

### Development Configuration

```python
# settings.py (Development)
UPR_CONFIG = {
    'validate_on_startup': True,
    'strict_mode': False,  # Lenient in development
    'auto_sync': False,
    'orphan_action': 'warn',
}
```

### Production Configuration

```python
# settings.py (Production)
UPR_CONFIG = {
    'validate_on_startup': True,
    'strict_mode': True,  # Strict in production
    'auto_sync': False,  # Manual sync via command
    'orphan_action': 'error',  # Error on orphans
    'fail_on_breaking_changes': True,
}
```

### Staging Configuration

```python
# settings.py (Staging)
UPR_CONFIG = {
    'validate_on_startup': True,
    'strict_mode': True,
    'auto_sync': False,
    'orphan_action': 'warn',  # Warn but don't fail
}
```

## CI/CD Integration

### GitHub Actions

```yaml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      
      - name: Validate Permissions
        run: |
          python manage.py upr_validate
      
      - name: Sync Permissions (Dry Run)
        run: |
          python manage.py upr_sync --dry-run
      
      - name: Deploy
        run: |
          # Your deployment steps
          python manage.py migrate
          python manage.py upr_sync
          systemctl restart your-app
```

### GitLab CI

```yaml
deploy:
  stage: deploy
  script:
    - pip install -r requirements.txt
    - python manage.py upr_validate
    - python manage.py migrate
    - python manage.py upr_sync
    - systemctl restart your-app
  only:
    - main
```

## Monitoring

### Health Checks

```python
# health_check.py
def check_permission_health():
    """Check permission system health"""
    try:
        # Validate permissions
        registry.validate()
        
        # Check for orphaned permissions
        orphaned = Permission.objects.filter(
            key__not_in=registry.get_all_keys()
        )
        
        if orphaned.exists():
            return {
                'status': 'warning',
                'orphaned_count': orphaned.count()
            }
        
        return {'status': 'healthy'}
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }
```

### Metrics

```python
# metrics.py
def get_permission_metrics():
    """Get permission system metrics"""
    return {
        'total_permissions': Permission.objects.count(),
        'active_permissions': Permission.objects.filter(is_active=True).count(),
        'deprecated_permissions': Permission.objects.filter(is_deprecated=True).count(),
        'orphaned_permissions': get_orphaned_count(),
        'permission_assignments': UserPermission.objects.count(),
    }
```

### Logging

```python
# logging.py
import logging

logger = logging.getLogger('upr')

# Log permission sync
logger.info("Starting permission sync")
logger.info(f"Created {created_count} permissions")
logger.info(f"Updated {updated_count} permissions")
logger.warning(f"Found {orphaned_count} orphaned permissions")

# Log permission checks
logger.debug(f"Permission check: {user} -> {permission_key} = {result}")
logger.warning(f"Permission denied: {user} -> {permission_key}")
```

## Rollback Strategy

### Code Rollback

```bash
# Rollback code
git revert <commit>
git push

# Permissions remain in database
# Old code works with existing permissions
```

### Permission Rollback

```bash
# If permission sync causes issues
# Restore from backup
python manage.py loaddata backup.json

# Or manually revert specific permissions
python manage.py shell
>>> from upr.models import Permission
>>> Permission.objects.filter(key='users.new_action').delete()
```

## Best Practices

### 1. Always Backup Before Sync

```bash
# ✅ Good: Backup first
python manage.py dumpdata upr > backup.json
python manage.py upr_sync

# ❌ Bad: No backup
python manage.py upr_sync  # Risky!
```

### 2. Test in Staging First

```bash
# ✅ Good: Test in staging
# Deploy to staging
python manage.py upr_sync
# Test thoroughly
# Then deploy to production

# ❌ Bad: Deploy directly to production
# No testing!
```

### 3. Use Dry Run

```bash
# ✅ Good: Check changes first
python manage.py upr_sync --dry-run

# ❌ Bad: Sync without checking
python manage.py upr_sync  # Surprises!
```

### 4. Monitor After Deployment

```bash
# ✅ Good: Monitor after deployment
tail -f /var/log/app.log
curl https://app.com/api/permissions/catalog/

# ❌ Bad: Deploy and forget
# Issues go undetected
```

### 5. Document Changes

```markdown
# ✅ Good: Document permission changes
## Deployment Notes - v1.1

### Permission Changes
- Added: users.update
- Deprecated: users.old_action
- Migration: Run `python manage.py migrate_permissions`

# ❌ Bad: No documentation
# Changes unclear
```

## Troubleshooting

### Permission Sync Fails

**Problem**: Sync command fails

**Solution**:
1. Check error message
2. Fix permission definitions
3. Run validation: `python manage.py upr_validate`
4. Retry sync

### Application Won't Start

**Problem**: App refuses to start after deployment

**Solution**:
1. Check startup logs
2. Run `python manage.py upr_validate`
3. Fix validation errors
4. Run `python manage.py upr_sync`
5. Restart application

### Permissions Missing After Deployment

**Problem**: Permissions not in database after sync

**Solution**:
1. Check sync output
2. Verify database connection
3. Check for errors in logs
4. Manually verify permissions in database

## Summary

Deployment process:

- ✅ **Pre-deployment validation** - Catch issues early
- ✅ **Backup before sync** - Safe rollback
- ✅ **Staged deployment** - Test in staging first
- ✅ **Post-deployment verification** - Ensure success
- ✅ **Monitoring and logging** - Visibility into system
- ✅ **Rollback strategy** - Safe recovery

The system is designed for safe, reliable deployments with clear failure modes and recovery procedures.
