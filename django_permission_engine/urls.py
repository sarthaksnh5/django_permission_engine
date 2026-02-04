"""
URL configuration for UPR
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import PermissionCatalogViewSet
from .permission_management import UserPermissionManagementViewSet
from .group_management import GroupManagementViewSet

router = DefaultRouter()
router.register(r'permissions', PermissionCatalogViewSet, basename='permission-catalog')
router.register(r'permissions', UserPermissionManagementViewSet, basename='permission-management')

# Groups: ModelViewSet under /api/permissions/groups/ and /api/permissions/groups/{id}/
router_groups = DefaultRouter()
router_groups.register(r'groups', GroupManagementViewSet, basename='permission-group')

urlpatterns = [
    path('api/', include(router.urls)),
    path('api/permissions/', include(router_groups.urls)),
]
