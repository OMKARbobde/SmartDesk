from rest_framework.permissions import BasePermission


class HasSmartDeskRole(BasePermission):
    allowed_roles = frozenset()

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.role in self.allowed_roles)


class IsAdmin(HasSmartDeskRole):
    allowed_roles = frozenset({"ADMIN"})


class IsAdminOrAgent(HasSmartDeskRole):
    allowed_roles = frozenset({"ADMIN", "AGENT"})


class IsSmartDeskUser(HasSmartDeskRole):
    allowed_roles = frozenset({"ADMIN", "AGENT", "EMPLOYEE"})
