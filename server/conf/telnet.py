"""Project Telnet input handling compatible with Evennia 6 byte streams."""

import re

from django.conf import settings
from evennia.server.portal.telnet import TelnetProtocol

_LINEBREAK = re.compile(rb"\n\r|\r\n|\n|\r")
_HTTP_REQUEST = re.compile(
    rb"^(GET|HEAD|POST|PUT|DELETE|TRACE|OPTIONS|CONNECT|PATCH) .*? HTTP/[0-9]\.[0-9]$",
    re.I,
)
_HTTP_WARNING = (
    b"This is Evennia's Telnet port. Use a Telnet client here, "
    b"or connect to the dedicated web port with your browser.\r\n"
)


class FusionTelnetProtocol(TelnetProtocol):
    """Keep normal Telnet negotiation while fixing the upstream HTTP guard."""

    def applicationDataReceived(self, data):
        """Buffer bytes, reject HTTP requests, and forward complete game lines."""
        if not data:
            lines = [data]
        elif data.strip() == b"\x00":
            lines = [settings.IDLE_COMMAND.encode("utf-8") + b"\n"]
        else:
            lines = _LINEBREAK.split(self.line_buffer + data)
            if _HTTP_REQUEST.fullmatch(lines[0]):
                self.line_buffer = b""
                self.transport.write(_HTTP_WARNING)
                self.transport.loseConnection()
                return
            self.line_buffer = lines.pop()
        for line in lines:
            self.data_in(text=line + b"\n")
