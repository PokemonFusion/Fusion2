"""Real Twisted/Evennia byte-stream checks without starting portal services."""

import os
import re
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")

from django.conf import settings
from evennia.server.portal import telnet as upstream
from evennia.utils.utils import class_from_module
from twisted.internet.testing import StringTransport

from server.conf.telnet import FusionTelnetProtocol


class TelnetProtocolCases(unittest.TestCase):
    """Exercise real Telnet framing with the deployed text-regex defect present."""

    def setUp(self):
        """Attach an in-memory wire and capture data delivered to the game."""
        self.reset_protocol()
        guard = patch.object(upstream, "_HTTP_REGEX", re.compile(r"GET .* HTTP/1.1"))
        guard.start()
        self.addCleanup(guard.stop)

    def reset_protocol(self):
        """Create a fresh transport for another independent input scenario."""
        self.protocol = FusionTelnetProtocol()
        self.protocol.transport = StringTransport()
        self.protocol.protocol_flags = {}
        self.protocol.line_buffer = b""
        self.received = []
        self.protocol.data_in = lambda **data: self.received.append(data["text"])

    def test_settings_select_project_protocol(self):
        """Portal factories and SSL's subclass resolve the project setting."""
        self.assertIs(class_from_module(settings.TELNET_PROTOCOL_CLASS), FusionTelnetProtocol)
        self.assertIsInstance(self.protocol, upstream.TelnetProtocol)

    def test_multiple_game_commands_in_one_packet(self):
        """The former string/bytes crash also affected ordinary batched commands."""
        self.protocol.dataReceived(b"+party\r\n+heal\r\n")
        self.assertEqual(self.received, [b"+party\n", b"+heal\n"])
        self.assertFalse(self.protocol.transport.disconnecting)

    def test_fragmented_unicode_command(self):
        """Incomplete lines and UTF-8 bytes survive packet boundaries unchanged."""
        command = "nickname Éclair Jr.".encode("utf-8")
        split = command.index(b"\xc3") + 1
        self.protocol.dataReceived(command[:split])
        self.assertEqual(self.received, [])
        self.protocol.dataReceived(command[split:] + b"\n")
        self.assertEqual(self.received, [command + b"\n"])
        self.assertEqual(self.protocol.line_buffer, b"")

    def test_http_methods_are_rejected_without_forwarding_credentials(self):
        """HTTP traffic closes only its own transport and never becomes commands."""
        for method in (b"GET", b"HEAD", b"POST", b"PUT", b"DELETE", b"TRACE", b"OPTIONS", b"CONNECT", b"PATCH"):
            with self.subTest(method=method):
                self.reset_protocol()
                self.protocol.dataReceived(method + b" / HTTP/1.1\r\nAuthorization: private\r\n\r\n")
                self.assertTrue(self.protocol.transport.disconnecting)
                self.assertIn(b"Telnet port", self.protocol.transport.value())
                self.assertEqual(self.received, [])

    def test_fragmented_http_request_is_rejected(self):
        """The first line's buffered prefix participates in the HTTP check."""
        self.protocol.dataReceived(b"GE")
        self.protocol.dataReceived(b"T / HTTP/1.")
        self.assertFalse(self.protocol.transport.disconnecting)
        self.protocol.dataReceived(b"1\r\nHost: localhost\r\n\r\n")
        self.assertTrue(self.protocol.transport.disconnecting)
        self.assertEqual(self.received, [])

    def test_telnet_nop_negotiation_is_preserved(self):
        """Telnet control bytes still go through Twisted before line routing."""
        self.protocol.dataReceived(b"\xff\xf1+party\n")
        self.assertEqual(self.received, [b"+party\n"])

    def test_legacy_null_keepalive_is_preserved(self):
        """The inherited idle-command behavior remains byte-compatible."""
        self.protocol.dataReceived(b"\x00")
        self.assertEqual(self.received, [settings.IDLE_COMMAND.encode("utf-8") + b"\n\n"])

    def test_http_words_in_normal_game_input_are_not_rejected(self):
        """Ordinary lines containing HTTP terminology remain player commands."""
        self.protocol.dataReceived(b"get Potion\npage Friend=HTTP/1.1 help\n")
        self.assertEqual(self.received, [b"get Potion\n", b"page Friend=HTTP/1.1 help\n"])
        self.assertFalse(self.protocol.transport.disconnecting)


if __name__ == "__main__":
    unittest.main(verbosity=2)
