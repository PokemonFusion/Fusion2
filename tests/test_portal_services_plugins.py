import os
import re

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from evennia.server.portal import telnet

from server.conf import portal_services_plugins


def test_portal_plugin_patches_telnet_http_regex_to_bytes(monkeypatch):
	monkeypatch.setattr(
		telnet,
		"_HTTP_REGEX",
		re.compile(
			r"(GET|HEAD|POST|PUT|DELETE|TRACE|OPTIONS|CONNECT|PATCH) (.*? HTTP/[0-9]\.[0-9])",
			re.I,
		),
	)

	portal_services_plugins.start_plugin_services(None)

	assert isinstance(telnet._HTTP_REGEX.pattern, bytes)
	assert telnet._HTTP_REGEX.match(b"GET / HTTP/1.1")
