Quick Start
============

This guide will help you get started with Django Permission Engine.

Step 1: Install
---------------

.. code-block:: bash

    pip install django-permission-engine

Step 2: Add to INSTALLED_APPS
-----------------------------

Add to your Django project's ``settings.py``:

.. code-block:: python

    INSTALLED_APPS = [
        # ... other apps
        'rest_framework',
        'django_permission_engine',
    ]

Step 3: Configure
-----------------

Add UPR configuration to ``settings.py``:

.. code-block:: python

    UPR_CONFIG = {
        'validate_on_startup': True,
        'strict_mode': True,
        'auto_sync': False,
        'orphan_action': 'warn',
    }

Step 4: Run Migrations
---------------------

.. code-block:: bash

    python manage.py migrate

Step 5: Define Permissions
---------------------------

Create ``upr_config.py`` in your app:

.. code-block:: python

    from django_permission_engine import module, action

    @module('users', label='User Management')
    class UsersModule:
        crud = ['view', 'create', 'update', 'delete']
        actions = ['reset_password']

Step 6: Sync Permissions
------------------------

.. code-block:: bash

    python manage.py upr_sync

Step 7: Use in ViewSets
-----------------------

.. code-block:: python

    from rest_framework import viewsets
    from django_permission_engine.permissions import PermissionRequired

    class UserViewSet(viewsets.ModelViewSet):
        permission_classes = [PermissionRequired]
        module = 'users'
        queryset = User.objects.all()
        serializer_class = UserSerializer

That's it! Your permissions are now enforced automatically.
