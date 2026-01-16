"""
URL configuration for UPR
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import PermissionCatalogViewSet
from .permission_management import UserPermissionManagementViewSet

router = DefaultRouter()
router.register(r'permissions', PermissionCatalogViewSet, basename='permission-catalog')
router.register(r'permissions', UserPermissionManagementViewSet, basename='permission-management')

urlpatterns = [
    path('api/', include(router.urls)),
]
