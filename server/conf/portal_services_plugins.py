"""
Start plugin services

This plugin module can define user-created services for the Portal to
start.

This module must handle all imports and setups required to start
twisted services (see examples in evennia.server.portal.portal). It
must also contain a function start_plugin_services(application).
Evennia will call this function with the main Portal application (so
your services can be added to it). The function should not return
anything. Plugin services are started last in the Portal startup
process.

"""

import re


_HTTP_REGEX = re.compile(
	b"(GET|HEAD|POST|PUT|DELETE|TRACE|OPTIONS|CONNECT|PATCH) (.*? HTTP/[0-9]\\.[0-9])",
	re.I,
)


def _patch_telnet_http_regex():
	"""Keep Evennia 6.0.0's telnet HTTP guard compatible with byte input."""
	from evennia.server.portal import telnet

	telnet._HTTP_REGEX = _HTTP_REGEX


def start_plugin_services(portal):
	"""
	This hook is called by Evennia, last in the Portal startup process.

	portal - a reference to the main portal application.
	"""
	_patch_telnet_http_regex()
