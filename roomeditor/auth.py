"""Shared authorization helpers for browser-based builder tools."""

from __future__ import annotations

from functools import wraps
from urllib.parse import urlencode

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect


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


def has_builder_access(user) -> bool:
	"""Return ``True`` when a user may use builder website tools."""

	if not _is_authenticated(user):
		return False
	if getattr(user, "is_superuser", False):
		return True
	return _perm_check(user, "Builder") or _perm_check(user, "Builders")


def builder_required(view_func):
	"""Require an authenticated Builder/Builders user for a view."""

	@wraps(view_func)
	def _wrapped(request, *args, **kwargs):
		user = getattr(request, "user", None)
		if not _is_authenticated(user):
			path = request.get_full_path() if hasattr(request, "get_full_path") else getattr(request, "path", "")
			login_url = getattr(settings, "LOGIN_URL", "/accounts/login/")
			separator = "&" if "?" in login_url else "?"
			return HttpResponseRedirect(f"{login_url}{separator}{urlencode({'next': path})}")
		if not has_builder_access(user):
			raise PermissionDenied
		return view_func(request, *args, **kwargs)

	return _wrapped
