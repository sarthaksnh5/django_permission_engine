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
