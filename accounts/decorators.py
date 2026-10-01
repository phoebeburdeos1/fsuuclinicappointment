from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect

from .models import UserRole
from .utils import is_default_admin


def admin_only_required(view_func):
    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        if request.user.role != UserRole.ADMIN:
            raise PermissionDenied('You do not have permission to access this admin-only section.')
        return view_func(request, *args, **kwargs)

    return _wrapped


def admin_required(view_func):
    return admin_only_required(view_func)


def staff_or_admin_required(view_func):
    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        if request.user.role not in {UserRole.STAFF, UserRole.ADMIN}:
            messages.warning(request, 'Access Restricted: Staff and Admin only.')
            return redirect('patient_dashboard')
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
