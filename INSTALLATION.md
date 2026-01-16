# Installation Guide

## Safe Installation (No Version Conflicts)

This library is designed to work with your existing Django and DRF installations without forcing version upgrades.

### Version Requirements

The library uses **flexible minimum version requirements only** (no strict upper bounds):

- **Django**: `>=3.2` (works with Django 3.2, 4.0, 4.1, 4.2, and future versions)
- **Django REST Framework**: `>=3.12` (works with DRF 3.12, 3.13, 3.14, and future versions)

### Installation Methods

#### Standard Installation

```bash
pip install django-permission-engine
```

This will:
- ✅ Install the library
- ✅ Check that you have compatible versions (Django >=3.2, DRF >=3.12)
- ✅ **Won't upgrade** your existing Django/DRF if they meet minimum requirements
- ✅ **Won't downgrade** your existing Django/DRF

#### If You Have Version Conflicts

If pip tries to upgrade your packages (which shouldn't happen with this library), you can:

**Option 1: Install without dependency checks (not recommended)**
```bash
pip install django-permission-engine --no-deps
# Then manually ensure you have Django>=3.2 and djangorestframework>=3.12
```

**Option 2: Use a virtual environment (recommended)**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install django-permission-engine
```

**Option 3: Check your current versions first**
```bash
# Check your current versions
python -c "import django; print(django.get_version())"
python -c "import rest_framework; print(rest_framework.VERSION)"

# If Django >= 3.2 and DRF >= 3.12, installation is safe
pip install django-permission-engine
```

### Compatibility Matrix

| Django Version | DRF Version | Compatible |
|----------------|-------------|------------|
| 3.2.x          | 3.12.x      | ✅ Yes     |
| 3.2.x          | 3.13.x      | ✅ Yes     |
| 4.0.x          | 3.12.x      | ✅ Yes     |
| 4.1.x          | 3.13.x      | ✅ Yes     |
| 4.2.x          | 3.14.x      | ✅ Yes     |
| 5.0.x          | 4.0.x       | ✅ Yes     |

### Troubleshooting

#### Issue: pip wants to upgrade Django/DRF

**Solution:** This shouldn't happen, but if it does:
1. Check your current versions meet minimum requirements
2. Use `pip install --no-deps` and manually verify compatibility
3. Consider using a virtual environment

#### Issue: Import errors after installation

**Solution:**
```bash
# Verify installation
pip show django-permission-engine

# Verify Django and DRF are installed
python -c "import django; import rest_framework; print('OK')"

# Reinstall if needed
pip install --force-reinstall django-permission-engine
```

### Development Installation

For development, install in editable mode:

```bash
git clone https://github.com/yourusername/django-permission-engine.git
cd django-permission-engine
pip install -e .
```

This installs the package in "editable" mode, so changes to the source code are immediately available.

### Why Flexible Versions?

We use flexible version requirements (minimum only) because:

1. **No Breaking Changes**: We don't force upgrades that might break your existing project
2. **Compatibility**: Works with a wide range of Django/DRF versions
3. **Safety**: Your existing dependencies remain unchanged
4. **Future-Proof**: Works with future Django/DRF versions automatically

### Testing Compatibility

After installation, verify everything works:

```bash
python manage.py shell
```

```python
# Test imports
from django_permission_engine import registry, module, action
from django_permission_engine.models import Permission
from django_permission_engine.permissions import PermissionRequired

# All imports should work without errors
print("✅ Installation successful!")
```
