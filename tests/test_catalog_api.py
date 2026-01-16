"""
Tests for Permission Catalog API
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from django_permission_engine.models import Permission

User = get_user_model()


@pytest.mark.django_db
class TestPermissionCatalogAPI:
    """Test Permission Catalog API"""

    @pytest.fixture
    def client(self):
        """Create API client"""
        return APIClient()

    @pytest.fixture
    def user(self):
        """Create test user"""
        return User.objects.create_user('testuser', 'test@example.com', 'password')

    @pytest.fixture
    def permissions(self):
        """Create test permissions"""
        permissions = []
        for action in ['view', 'create', 'update', 'delete']:
            perm = Permission.objects.create(
                key=f'users.{action}',
                module='users',
                capability=action,
                label=f'{action.title()} Users',
            )
            permissions.append(perm)

        perm = Permission.objects.create(
            key='users.reset_password',
            module='users',
            capability='reset_password',
            label='Reset Password',
        )
        permissions.append(perm)

        return permissions

    def test_catalog_endpoint(self, client, user, permissions):
        """Test catalog endpoint"""
        client.force_authenticate(user=user)
        response = client.get('/api/permissions/catalog/')

        assert response.status_code == 200
        data = response.json()
        assert 'modules' in data
        assert 'total_permissions' in data
        assert 'total_modules' in data
        assert len(data['modules']) > 0

    def test_module_catalog_endpoint(self, client, user, permissions):
        """Test module catalog endpoint"""
        client.force_authenticate(user=user)
        response = client.get('/api/permissions/catalog/users/')

        assert response.status_code == 200
        data = response.json()
        assert data['key'] == 'users'
        assert 'permissions' in data
        assert len(data['permissions']) == 5

    def test_catalog_filter_by_module(self, client, user, permissions):
        """Test filtering by module"""
        # Create another module
        Permission.objects.create(
            key='orders.view',
            module='orders',
            capability='view',
            label='View Orders',
        )

        client.force_authenticate(user=user)
        response = client.get('/api/permissions/catalog/?module=users')

        assert response.status_code == 200
        data = response.json()
        assert all(
            m['key'] == 'users' or m['key'].startswith('users.')
            for m in data['modules']
        )

    def test_catalog_filter_by_type(self, client, user, permissions):
        """Test filtering by type"""
        client.force_authenticate(user=user)
        response = client.get('/api/permissions/catalog/?type=crud')

        assert response.status_code == 200
        data = response.json()
        for module in data['modules']:
            for perm in module['permissions']:
                assert perm['type'] == 'crud'

    def test_catalog_search(self, client, user, permissions):
        """Test search functionality"""
        client.force_authenticate(user=user)
        response = client.get('/api/permissions/catalog/?search=reset')

        assert response.status_code == 200
        data = response.json()
        found = False
        for module in data['modules']:
            for perm in module['permissions']:
                if 'reset' in perm['key'].lower() or 'reset' in perm['label'].lower():
                    found = True
        assert found

    def test_catalog_unauthenticated(self, client):
        """Test catalog requires authentication"""
        response = client.get('/api/permissions/catalog/')
        assert response.status_code == 401

    def test_catalog_structure(self, client, user, permissions):
        """Test catalog response structure"""
        client.force_authenticate(user=user)
        response = client.get('/api/permissions/catalog/')

        assert response.status_code == 200
        data = response.json()

        # Check structure
        assert 'modules' in data
        assert isinstance(data['modules'], list)

        if data['modules']:
            module = data['modules'][0]
            assert 'key' in module
            assert 'label' in module
            assert 'permissions' in module
            assert isinstance(module['permissions'], list)

            if module['permissions']:
                perm = module['permissions'][0]
                assert 'key' in perm
                assert 'module' in perm
                assert 'capability' in perm
                assert 'label' in perm
                assert 'type' in perm
                assert 'is_active' in perm
                assert 'is_deprecated' in perm
