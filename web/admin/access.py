"""Access helpers for custom staff-only web admin pages."""

from __future__ import annotations

from functools import wraps
from urllib.parse import urlencode

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect

ACCOUNT_ROSTER_PERMISSIONS = ("Admin", "Admins", "Wizard", "Wizards")


def _is_authenticated(user) -> bool:
    """Return whether ``user`` is authenticated across Django/Evennia styles."""

    value = getattr(user, "is_authenticated", False)
    if callable(value):
        return bool(value())
    return bool(value)


def _perm_check(user, permission: str) -> bool:
    """Safely call an Evennia-style permission checker."""

    checker = getattr(user, "check_permstring", None)
    if callable(checker):
        try:
            if checker(permission):
                return True
        except Exception:
            pass

    permissions = getattr(user, "permissions", None)
    checker = getattr(permissions, "check", None)
    if callable(checker):
        try:
            return bool(checker(permission))
        except Exception:
            return False
    return False


def has_account_roster_access(user) -> bool:
    """Return whether ``user`` may view the account roster."""

    if not _is_authenticated(user):
        return False
    if getattr(user, "is_superuser", False):
        return True
    return any(_perm_check(user, permission) for permission in ACCOUNT_ROSTER_PERMISSIONS)


def account_roster_required(view_func):
    """Require an authenticated Admin/Wizard user for a view."""

    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        user = getattr(request, "user", None)
        if not _is_authenticated(user):
            path = request.get_full_path() if hasattr(request, "get_full_path") else getattr(request, "path", "")
            login_url = getattr(settings, "LOGIN_URL", "/accounts/login/")
            separator = "&" if "?" in login_url else "?"
            return HttpResponseRedirect(f"{login_url}{separator}{urlencode({'next': path})}")
        if not has_account_roster_access(user):
            raise PermissionDenied
        return view_func(request, *args, **kwargs)

    return _wrapped
