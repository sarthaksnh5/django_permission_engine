Examples
========

Basic Module Definition
------------------------

.. code-block:: python

    from django_permission_engine import module, action

    @module('users', label='User Management')
    class UsersModule:
        crud = ['view', 'create', 'update', 'delete']
        actions = ['reset_password', 'export_data']

Hierarchical Modules
--------------------

.. code-block:: python

    @module('breakdown')
    class BreakdownModule:
        crud = ['view', 'create', 'update', 'delete']

    @module('breakdown.visit')
    class BreakdownVisitModule:
        crud = ['view', 'create', 'update']
        actions = ['assign_engineer', 'close']

Using in ViewSets
-----------------

.. code-block:: python

    from rest_framework import viewsets
    from django_permission_engine.permissions import PermissionRequired

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

Programmatic Registration
--------------------------

.. code-block:: python

    from django_permission_engine import get_registry

    registry = get_registry()
    registry.register_module('users', crud=['view', 'create'])
    registry.sync()

Assigning Permissions
---------------------

.. code-block:: python

    from django_permission_engine.models import Permission, UserPermission

    user = User.objects.get(username='john')
    permission = Permission.objects.get(key='users.view')
    UserPermission.objects.create(user=user, permission=permission)
