from rest_framework.permissions import BasePermission


def is_analyst(user):
    return user.is_authenticated and (
        user.is_staff or user.groups.filter(name="Analyst").exists()
    )


class IsAnalyst(BasePermission):
    message = "An analyst account is required to access this resource."

    def has_permission(self, request, view):
        return is_analyst(request.user)
