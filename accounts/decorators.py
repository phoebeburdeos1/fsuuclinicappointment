from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

from .models import UserRole
from .utils import is_default_admin


def admin_required(view_func):
    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        if not is_default_admin(request.user):
            raise PermissionDenied('You do not have permission to access the admin dashboard.')
        return view_func(request, *args, **kwargs)

    return _wrapped


def patient_required(view_func):
    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        if request.user.role != UserRole.PATIENT:
            raise PermissionDenied('This section is only available to patients.')
        return view_func(request, *args, **kwargs)

    return _wrapped
