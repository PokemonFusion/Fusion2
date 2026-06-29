import types

from utils.client_encoding import (
	build_one_time_utf8_warning,
	session_reports_utf8,
	session_utf8_status,
)


def test_webclient_counts_as_confirmed_utf8():
	session = types.SimpleNamespace(
		protocol_key="webclient/websocket",
		protocol_flags={"CLIENTNAME": "Evennia Webclient (websocket:Firefox)"},
	)

	assert session_reports_utf8(session) is True
	assert session_utf8_status(session) == "confirmed"


def test_mtts_utf8_counts_as_confirmed_utf8():
	session = types.SimpleNamespace(protocol_key="telnet", protocol_flags={"UTF-8": True})

	assert session_reports_utf8(session) is True
	assert session_utf8_status(session) == "confirmed"


def test_telnet_without_utf8_flag_warns_once():
	session = types.SimpleNamespace(
		protocol_key="telnet",
		protocol_flags={"ENCODING": "utf-8", "CLIENTNAME": "UNKNOWN"},
		ndb=types.SimpleNamespace(),
	)

	first = build_one_time_utf8_warning(session)
	second = build_one_time_utf8_warning(session)

	assert "did not report UTF-8 support" in first
	assert "+symboltest ui" in first
	assert "+uimode ascii" in first
	assert second == ""


def test_non_utf8_encoding_warning_names_encoding():
	session = types.SimpleNamespace(
		protocol_key="telnet",
		protocol_flags={"ENCODING": "latin-1"},
		ndb=types.SimpleNamespace(),
	)

	assert session_utf8_status(session) == "not_utf8"
	assert "latin-1" in build_one_time_utf8_warning(session)
