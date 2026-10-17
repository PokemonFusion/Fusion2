"""Keep player input away from launcher AMP connections during Server reloads."""

from collections import deque

import evennia
from evennia.server.portal import amp
from evennia.server.portal.amp_server import AMPServerProtocol


class ReloadSafeAMPServerProtocol(AMPServerProtocol):
    """Queue input across reconnects instead of broadcasting it to launchers."""

    max_pending_input = 1000

    def _pending_input(self):
        """Share the queue across the Portal's launcher and Server connections."""
        if not hasattr(self.factory, "pending_player_input"):
            self.factory.pending_player_input = deque()
        return self.factory.pending_player_input

    def _server_connected(self):
        """Require the identified Server connection and a live transport."""
        server = self.factory.server_connection
        return server is not None and getattr(server.transport, "connected", False)

    def data_to_server(self, command, sessid, **kwargs):
        """Buffer only player input; retain upstream administrative routing."""
        if command is amp.MsgPortal2Server and not self._server_connected():
            pending = self._pending_input()
            if len(pending) < self.max_pending_input:
                pending.append((sessid, kwargs))
            else:
                handler = evennia.PORTAL_SESSION_HANDLER
                session = handler.get(sessid)
                if session is not None:
                    handler.data_out(session, text="The server is reconnecting. That command was not queued; please try again shortly.")
            return None
        return super().data_to_server(command, sessid, **kwargs)

    @amp.AdminServer2Portal.responder
    def portal_receive_adminserver2portal(self, packed_data):
        """Deliver queued input after session synchronization, once and in order."""
        result = super().portal_receive_adminserver2portal(packed_data)
        _, payload = self.data_in(packed_data)
        if payload.get("operation") == amp.PSYNC:
            pending = self._pending_input()
            while pending and self._server_connected():
                sessid, kwargs = pending.popleft()
                if evennia.PORTAL_SESSION_HANDLER.get(sessid) is not None:
                    super().data_to_server(amp.MsgPortal2Server, sessid, **kwargs)
        return result
