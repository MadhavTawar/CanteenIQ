from rest_framework.permissions import SAFE_METHODS, BasePermission

from .models import Profile


def _role(user):
    try:
        return user.profile.role
    except Profile.DoesNotExist:
        return None


class IsStaffRole(BasePermission):
    """Full access for canteen staff; read-only (or nothing, depending
    on the view) for everyone else."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and _role(request.user) == Profile.Role.STAFF)


class IsStaffOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return True
        return _role(request.user) == Profile.Role.STAFF


class IsOwnerOrStaff(BasePermission):
    """For order objects: students can only see/act on their own orders;
    staff can see/act on all of them."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if _role(request.user) == Profile.Role.STAFF:
            return True
        return obj.student_id == request.user.id
