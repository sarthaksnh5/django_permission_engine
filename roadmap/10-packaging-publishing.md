# Phase 10: Packaging & Publishing

## Overview

This phase covers packaging the library and publishing it to PyPI.

## Step 1: Finalize setup.py

### Ensure setup.py is complete

```python
# setup.py
from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

setup(
    name="django-permission-engine",
    version="0.1.0",
    description="Unified Permission Registry (UPR) for Django & DRF",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Your Name",
    author_email="your.email@example.com",
    url="https://github.com/yourusername/django-permission-engine",
    license="MIT",
    packages=find_packages(exclude=["tests", "tests.*"]),
    include_package_data=True,
    install_requires=[
        "Django>=3.2,<5.0",
        "djangorestframework>=3.12,<4.0",
    ],
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Framework :: Django",
        "Framework :: Django :: 3.2",
        "Framework :: Django :: 4.0",
        "Framework :: Django :: 4.1",
        "Framework :: Django :: 4.2",
    ],
    keywords="django permissions drf rest-framework",
    project_urls={
        "Documentation": "https://django-permission-engine.readthedocs.io/",
        "Source": "https://github.com/yourusername/django-permission-engine",
        "Tracker": "https://github.com/yourusername/django-permission-engine/issues",
    },
)
```

## Step 2: Create MANIFEST.in

### MANIFEST.in

```python
include README.md
include LICENSE
include CHANGELOG.md
include pyproject.toml
recursive-include django_permission_engine *.py
recursive-exclude * __pycache__
recursive-exclude * *.py[co]
```

## Step 3: Build Distribution

```bash
# Install build tools
pip install --upgrade build twine

# Clean previous builds
rm -rf build/ dist/ *.egg-info

# Build source distribution
python -m build

# Verify build
ls -la dist/
# Should see:
# - django-permission-engine-0.1.0.tar.gz
# - django_permission_engine-0.1.0-py3-none-any.whl
```

## Step 4: Test Installation Locally

```bash
# Install from local build
pip install dist/django-permission-engine-0.1.0.tar.gz

# Or install in editable mode for testing
pip install -e .

# Test import
python -c "import django_permission_engine; print('OK')"
```

## Step 5: Create Test PyPI Account

1. Go to https://test.pypi.org/
2. Create account
3. Get API token

## Step 6: Upload to Test PyPI

```bash
# Upload to Test PyPI
twine upload --repository testpypi dist/*

# Test install from Test PyPI
pip install --index-url https://test.pypi.org/simple/ django-permission-engine
```

## Step 7: Create PyPI Account

1. Go to https://pypi.org/
2. Create account
3. Enable two-factor authentication
4. Get API token

## Step 8: Upload to PyPI

```bash
# Upload to PyPI
twine upload dist/*

# Or use API token
twine upload dist/* --username __token__ --password pypi-xxxxx
```

## Step 9: Verify Publication

```bash
# Install from PyPI
pip install django-permission-engine

# Verify version
pip show django-permission-engine

# Test import
python -c "import django_permission_engine; print(django_permission_engine.__version__)"
```

## Step 10: Create GitHub Release

### Create release on GitHub

1. Go to repository
2. Click "Releases"
3. Click "Create a new release"
4. Tag: v0.1.0
5. Title: v0.1.0 - Initial Release
6. Description: (from CHANGELOG)
7. Publish release

## Step 11: Set Up Automated Publishing

### .github/workflows/publish.yml

```yaml
name: Publish to PyPI

on:
  release:
    types: [created]

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.9'
    
    - name: Install dependencies
      run: |
        pip install --upgrade pip
        pip install build twine
    
    - name: Build package
      run: python -m build
    
    - name: Publish to PyPI
      env:
        TWINE_USERNAME: __token__
        TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
      run: twine upload dist/*
```

## Step 12: Version Management

### Update version in multiple places

1. `django_permission_engine/__init__.py`:
   ```python
   __version__ = "0.1.0"
   ```

2. `setup.py`:
   ```python
   version="0.1.0",
   ```

3. `pyproject.toml` (if using):
   ```toml
   [tool.poetry]
   version = "0.1.0"
   ```

## Step 13: Post-Release Tasks

1. **Update Documentation**
   - Update version in docs
   - Add release notes

2. **Announce Release**
   - Update README
   - Post on social media
   - Update project website

3. **Monitor**
   - Check PyPI download stats
   - Monitor GitHub issues
   - Respond to feedback

## Checklist

- [ ] setup.py finalized
- [ ] MANIFEST.in created
- [ ] Package built successfully
- [ ] Local installation tested
- [ ] Test PyPI upload successful
- [ ] Test PyPI installation verified
- [ ] PyPI account created
- [ ] PyPI upload successful
- [ ] PyPI installation verified
- [ ] GitHub release created
- [ ] Automated publishing configured
- [ ] Version updated in all files
- [ ] Post-release tasks completed

## Common Issues

### Issue: Package name already taken

**Solution**: Choose a different name or add suffix (e.g., `django-permission-engine-upr`)

### Issue: Upload fails with 403

**Solution**: 
- Check API token is correct
- Ensure package name matches exactly
- Verify account has permission

### Issue: Import errors after installation

**Solution**:
- Check `__init__.py` exports correctly
- Verify package structure
- Test in clean virtual environment

## Next Steps

After publishing:

1. **Monitor Usage**: Track downloads and issues
2. **Gather Feedback**: Listen to user feedback
3. **Plan Next Version**: Based on feedback and roadmap
4. **Maintain**: Fix bugs, add features, update documentation

## Summary

You've successfully:
- ✅ Built the library
- ✅ Tested thoroughly
- ✅ Documented completely
- ✅ Published to PyPI
- ✅ Set up automated publishing

Congratulations! Your library is now available for others to use.
