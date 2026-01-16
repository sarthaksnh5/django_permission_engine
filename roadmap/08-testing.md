# Phase 8: Testing

## Overview

This phase covers setting up comprehensive testing for the library.

## Step 1: Configure pytest

### pytest.ini (already in pyproject.toml)

Ensure pytest configuration is correct:

```ini
[pytest]
DJANGO_SETTINGS_MODULE = tests.settings
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    -v
    --tb=short
    --strict-markers
    --cov=django_permission_engine
    --cov-report=html
    --cov-report=term-missing
testpaths = tests
markers =
    django_db: marks tests as requiring database access
    slow: marks tests as slow running
```

## Step 2: Create Test Fixtures

### tests/conftest.py

```python
"""
Pytest configuration and fixtures
"""
import pytest
from django.contrib.auth import get_user_model
from django_permission_engine.models import Permission, UserPermission

User = get_user_model()


@pytest.fixture
def user():
    """Create a test user"""
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123'
    )


@pytest.fixture
def admin_user():
    """Create an admin user"""
    return User.objects.create_superuser(
        username='admin',
        email='admin@example.com',
        password='adminpass123'
    )


@pytest.fixture
def permission():
    """Create a test permission"""
    return Permission.objects.create(
        key='users.view',
        module='users',
        capability='view',
        label='View Users',
    )


@pytest.fixture
def user_with_permission(user, permission):
    """Create user with permission"""
    UserPermission.objects.create(user=user, permission=permission)
    return user


@pytest.fixture
def registry():
    """Get registry instance"""
    from django_permission_engine import get_registry
    return get_registry()
```

## Step 3: Create Test Factories

### tests/factories.py

```python
"""
Test factories for creating test data
"""
import factory
from django.contrib.auth import get_user_model
from django_permission_engine.models import Permission, UserPermission

User = get_user_model()


class UserFactory(factory.django.DjangoModelFactory):
    """Factory for User model"""
    class Meta:
        model = User
    
    username = factory.Sequence(lambda n: f'user{n}')
    email = factory.LazyAttribute(lambda obj: f'{obj.username}@example.com')
    password = factory.PostGenerationMethodCall('set_password', 'password123')


class PermissionFactory(factory.django.DjangoModelFactory):
    """Factory for Permission model"""
    class Meta:
        model = Permission
    
    key = factory.Sequence(lambda n: f'test.permission{n}')
    module = 'test'
    capability = factory.Sequence(lambda n: f'action{n}')
    label = factory.LazyAttribute(lambda obj: f'{obj.capability.title()} Test')
    is_active = True
    is_deprecated = False


class UserPermissionFactory(factory.django.DjangoModelFactory):
    """Factory for UserPermission model"""
    class Meta:
        model = UserPermission
    
    user = factory.SubFactory(UserFactory)
    permission = factory.SubFactory(PermissionFactory)
```

## Step 4: Write Integration Tests

### tests/test_integration.py

```python
"""
Integration tests for UPR
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from django_permission_engine import registry, module
from django_permission_engine.models import Permission, UserPermission
from django_permission_engine.permissions import PermissionRequired

User = get_user_model()


@pytest.mark.django_db
class TestIntegration:
    """Integration tests"""
    
    def test_full_workflow(self):
        """Test complete workflow: define -> sync -> assign -> check"""
        # 1. Define permissions
        @module('users')
        class UsersModule:
            crud = ['view', 'create']
            actions = ['reset_password']
        
        # 2. Sync to database
        result = registry.sync()
        assert len(result['created']) == 3
        
        # 3. Create user and assign permission
        user = User.objects.create_user('testuser', 'test@example.com', 'password')
        permission = Permission.objects.get(key='users.view')
        UserPermission.objects.create(user=user, permission=permission)
        
        # 4. Check permission
        from django_permission_engine.permissions import PermissionResolver
        resolver = PermissionResolver()
        
        class MockViewSet:
            module = 'users'
        
        has_permission = resolver.resolve(user, MockViewSet(), 'list', 'GET')
        assert has_permission is True
    
    def test_drf_integration(self):
        """Test DRF integration"""
        # Setup
        @module('users')
        class UsersModule:
            crud = ['view']
        
        registry.sync()
        
        user = User.objects.create_user('testuser', 'test@example.com', 'password')
        permission = Permission.objects.get(key='users.view')
        UserPermission.objects.create(user=user, permission=permission)
        
        # Test DRF permission class
        from django_permission_engine.permissions import PermissionRequired
        
        class MockViewSet:
            module = 'users'
            action = 'list'
        
        class MockRequest:
            user = user
            method = 'GET'
        
        perm_class = PermissionRequired()
        result = perm_class.has_permission(MockRequest(), MockViewSet())
        assert result is True
```

## Step 5: Create Test Coverage Report

### .coveragerc

```ini
[run]
source = django_permission_engine
omit = 
    */tests/*
    */migrations/*
    */venv/*
    */__pycache__/*

[report]
exclude_lines =
    pragma: no cover
    def __repr__
    raise AssertionError
    raise NotImplementedError
    if __name__ == .__main__.:
    if TYPE_CHECKING:
```

## Step 6: Run Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=django_permission_engine --cov-report=html

# Run specific test file
pytest tests/test_models.py

# Run specific test
pytest tests/test_models.py::TestPermission::test_create_permission

# Run with verbose output
pytest -v

# Run with output
pytest -s

# Run only fast tests (exclude slow)
pytest -m "not slow"
```

## Step 7: Set Up CI Testing

### .github/workflows/test.yml

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.8, 3.9, "3.10", "3.11"]
        django-version: ["3.2", "4.0", "4.1", "4.2"]
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v2
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        pip install --upgrade pip
        pip install Django==${{ matrix.django-version }}
        pip install -r requirements.txt
        pip install -r requirements-dev.txt
    
    - name: Run tests
      run: |
        pytest --cov=django_permission_engine --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v2
      with:
        file: ./coverage.xml
```

## Step 8: Test Performance

### tests/test_performance.py

```python
"""
Performance tests
"""
import pytest
import time
from django.contrib.auth import get_user_model
from django.core.cache import cache

from django_permission_engine.models import Permission, UserPermission
from django_permission_engine.permissions import PermissionResolver

User = get_user_model()


@pytest.mark.django_db
class TestPerformance:
    """Performance tests"""
    
    def test_permission_check_performance(self):
        """Test permission check is fast"""
        # Create user with many permissions
        user = User.objects.create_user('testuser', 'test@example.com', 'password')
        permissions = [
            Permission.objects.create(
                key=f'test.permission{i}',
                module='test',
                capability=f'action{i}',
                label=f'Permission {i}',
            )
            for i in range(100)
        ]
        for perm in permissions:
            UserPermission.objects.create(user=user, permission=perm)
        
        resolver = PermissionResolver()
        
        # Clear cache
        cache.clear()
        
        # First check (loads from DB)
        start = time.time()
        result = resolver.check_permission(user, 'test.permission50')
        elapsed = time.time() - start
        
        assert result is True
        assert elapsed < 0.1  # Should be fast even on first load
        
        # Second check (from cache)
        start = time.time()
        result = resolver.check_permission(user, 'test.permission50')
        elapsed = time.time() - start
        
        assert result is True
        assert elapsed < 0.001  # Should be very fast from cache
```

## Checklist

- [ ] pytest configured
- [ ] Test fixtures created
- [ ] Test factories created
- [ ] Unit tests written
- [ ] Integration tests written
- [ ] Performance tests written
- [ ] Coverage report configured
- [ ] CI/CD testing set up
- [ ] All tests passing
- [ ] Coverage > 80%

## Next Steps

Once testing is complete, proceed to **[09-documentation.md](09-documentation.md)** to set up documentation.
