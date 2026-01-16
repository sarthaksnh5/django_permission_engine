from .models import UserPermission, Permission


class UPRHelper:

    def __init__(self, user):
        self.user = user

    def get_user_permissions(self):
        return self.user.upr_permissions.all()

    def serialize_user_permissions(self):
        user_permissions = self.get_user_permissions()
        permissions_data = [
            {
                'key': up.permission.key,
                'module': up.permission.module,
                'capability': up.permission.capability,
                'label': up.permission.label,
                'granted_at': up.granted_at,
                'granted_by': up.granted_by.username if up.granted_by else None,
            }
            for up in user_permissions
        ]

        return permissions_data

    def add_permission(self, permission_keys = []):

        # delete all existing permissions
        self.user.upr_permissions.all().delete()

        # add new permissions
        permissions = Permission.objects.filter(key__in=permission_keys)
        add = []

        add.extend(UserPermission(user=self.user, permission=perm) for perm in permissions)

        UserPermission.objects.bulk_create(add, ignore_conflicts=True)

        return True
    