"""Helpers for interpreting client encoding capability flags."""

from __future__ import annotations

UTF8_WARNING_NDB_ATTR = "_fusion2_utf8_warning_shown"


def _truthy(value) -> bool:
	"""Return True for common boolean-ish values from protocol flags."""

	if isinstance(value, str):
		return value.strip().lower() in {"1", "true", "yes", "on", "utf-8", "utf8"}
	return bool(value)


def _encoding_is_utf8(value) -> bool:
	"""Return whether an encoding name is UTF-8."""

	return str(value or "").strip().lower().replace("_", "-") in {"utf-8", "utf8"}


def _session_flags(session) -> dict:
	"""Return protocol flags for a session-like object."""

	flags = getattr(session, "protocol_flags", None)
	return flags if isinstance(flags, dict) else {}


def session_is_webclient(session) -> bool:
	"""Return whether a session is from Evennia's browser webclient."""

	flags = _session_flags(session)
	protocol_key = str(getattr(session, "protocol_key", "") or "").lower()
	client_name = str(flags.get("CLIENTNAME", "") or "").lower()
	return (
		protocol_key in {"web", "websocket", "ajax"}
		or protocol_key.startswith("webclient")
		or "webclient" in client_name
	)


def session_reports_utf8(session) -> bool:
	"""Return whether the client positively reported UTF-8 support."""

	flags = _session_flags(session)
	return (
		session_is_webclient(session)
		or _truthy(flags.get("UTF-8"))
		or _truthy(flags.get("UTF8"))
	)


def session_encoding_name(session) -> str:
	"""Return the active server-side encoding name for a session."""

	flags = _session_flags(session)
	return str(flags.get("ENCODING", "utf-8") or "utf-8")


def session_utf8_status(session) -> str:
	"""Return ``confirmed``, ``not_utf8`` or ``unknown`` for a session."""

	if session_reports_utf8(session):
		return "confirmed"
	if not _encoding_is_utf8(session_encoding_name(session)):
		return "not_utf8"
	return "unknown"


def should_warn_about_utf8(session) -> bool:
	"""Return whether the session should receive the UTF-8 capability warning."""

	return session is not None and session_utf8_status(session) != "confirmed"


def mark_utf8_warning_shown(session) -> None:
	"""Mark the one-time UTF-8 warning as shown for this session."""

	ndb = getattr(session, "ndb", None)
	if ndb is not None:
		try:
			setattr(ndb, UTF8_WARNING_NDB_ATTR, True)
			return
		except Exception:
			pass
	try:
		setattr(session, UTF8_WARNING_NDB_ATTR, True)
	except Exception:
		pass


def utf8_warning_was_shown(session) -> bool:
	"""Return whether the one-time UTF-8 warning was already shown."""

	ndb = getattr(session, "ndb", None)
	if ndb is not None:
		try:
			return bool(getattr(ndb, UTF8_WARNING_NDB_ATTR, False))
		except Exception:
			pass
	return bool(getattr(session, UTF8_WARNING_NDB_ATTR, False))


def build_utf8_warning(session) -> str:
	"""Return an actionable warning for clients without confirmed UTF-8 support."""

	status = session_utf8_status(session)
	if status == "not_utf8":
		prefix = f"Your session encoding is {session_encoding_name(session)}, not confirmed UTF-8."
	else:
		prefix = "Your client did not report UTF-8 support."
	return (
		f"|yDisplay note:|n {prefix} If the logo, box art, gender symbols, or accented "
		"names look wrong, enable UTF-8/Unicode in your client or use the webclient. "
		"Run |w+symboltest ui|n to check. Use |w+uimode ascii|n for ASCII-safe display "
		"symbols, or |w+uimode unicode|n to force Unicode symbols."
	)


def build_one_time_utf8_warning(session) -> str:
	"""Return the warning once per session, or an empty string."""

	if not should_warn_about_utf8(session) or utf8_warning_was_shown(session):
		return ""
	mark_utf8_warning_shown(session)
	return build_utf8_warning(session)
