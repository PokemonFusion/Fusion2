"""Real Twisted AMP routing and wire tests without starting game services."""

import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")

import evennia
from django.conf import settings
from evennia.server.portal import amp
from evennia.server.portal.amp_server import AMPServerFactory, AMPServerProtocol
from twisted.protocols.amp import AMP
from twisted.test.iosim import connectedServerAndClient

from server.conf.amp import ReloadSafeAMPServerProtocol


class ServerPeer(AMP):
    """A Server peer accepting real AMP player input and sync frames."""

    def __init__(self):
        """Record decoded wire input."""
        super().__init__()
        self.messages = []
        self.synchronized = False

    @amp.AdminPortal2Server.responder
    def sync(self, packed_data):
        """Track that the session sync frame precedes gameplay."""
        self.synchronized = True
        return {}

    @amp.MsgPortal2Server.responder
    def receive(self, packed_data):
        """Fail if gameplay arrived before session synchronization."""
        assert self.synchronized
        self.messages.append(amp.loads(packed_data))
        return {}


class AMPReloadCases(unittest.TestCase):
    """Check reload gaps with simultaneous launcher and Server connections."""

    def setUp(self):
        """Build a shared factory with real Portal AMP configuration."""
        self.portal = SimpleNamespace(server_restart_mode="reload", start_time=1,
                                      server_info_dict={}, server_process_id=None)
        self.factory = AMPServerFactory(self.portal)
        self.protocol = self.factory.buildProtocol(None)
        self.protocol.transport = SimpleNamespace(connected=True)
        self.sessions = {1: SimpleNamespace(sessid=1), 2: SimpleNamespace(sessid=2)}
        self.handler = SimpleNamespace(get=self.sessions.get, get_all_sync_data=lambda: {},
                                       at_server_connection=Mock(), data_out=Mock())
        guard = patch.object(evennia, "PORTAL_SESSION_HANDLER", self.handler)
        guard.start()
        self.addCleanup(guard.stop)

    def test_settings_and_factory_select_project_protocol(self):
        """Evennia's real Portal factory instantiates the configured subclass."""
        self.assertEqual(settings.AMP_SERVER_PROTOCOL_CLASS, "server.conf.amp.ReloadSafeAMPServerProtocol")
        self.assertIsInstance(self.protocol, ReloadSafeAMPServerProtocol)
        self.assertIsInstance(self.protocol, AMPServerProtocol)

    def test_player_input_is_not_broadcast_to_launcher_during_gap(self):
        """The launcher has no MsgPortal2Server responder; it must receive none."""
        launcher = Mock()
        self.factory.launcher_connection = launcher
        self.factory.broadcasts = [launcher]
        self.protocol.broadcast = Mock()
        self.protocol.data_to_server(amp.MsgPortal2Server, 1, text=[["+party"], {}])
        self.protocol.data_to_server(amp.MsgPortal2Server, 2, text=[["+attack A2 Tackle B2"], {}])
        self.protocol.broadcast.assert_not_called()
        launcher.callRemote.assert_not_called()
        self.assertEqual([item[0] for item in self.factory.pending_player_input], [1, 2])

    def test_disconnected_server_transport_also_queues(self):
        """A stale factory reference cannot cause a send to a dead transport."""
        server = Mock(transport=SimpleNamespace(connected=False))
        self.factory.server_connection = server
        self.protocol.data_to_server(amp.MsgPortal2Server, 1, text=[["+party"], {}])
        server.callRemote.assert_not_called()
        self.assertEqual(len(self.factory.pending_player_input), 1)

    def test_live_server_routing_is_unchanged(self):
        """Normal player input retains the upstream send and error handling."""
        server = Mock(transport=SimpleNamespace(connected=True))
        self.factory.server_connection = server
        self.protocol.data_to_server(amp.MsgPortal2Server, 1, text=[["+party"], {}])
        args, kwargs = server.callRemote.call_args
        self.assertIs(args[0], amp.MsgPortal2Server)
        self.assertEqual(amp.loads(kwargs["packed_data"]), (1, {"text": [["+party"], {}]}))

    def test_administrative_routing_still_broadcasts(self):
        """Launcher startup/control requests keep Evennia's original behavior."""
        self.protocol.broadcast = Mock()
        self.protocol.data_to_server(amp.AdminPortal2Server, 0, operation=amp.SRELOAD)
        self.protocol.broadcast.assert_called_once()

    def test_queue_bound_reports_unqueued_input_to_its_session(self):
        """An extended outage cannot grow the queue without a limit."""
        self.protocol.max_pending_input = 1
        self.protocol.data_to_server(amp.MsgPortal2Server, 1, text=[["+party"], {}])
        self.protocol.data_to_server(amp.MsgPortal2Server, 2, text=[["+party"], {}])
        self.assertEqual(len(self.factory.pending_player_input), 1)
        self.handler.data_out.assert_called_once()
        self.assertIs(self.handler.data_out.call_args.args[0], self.sessions[2])
        self.assertIn("not queued", self.handler.data_out.call_args.kwargs["text"])

    def test_real_sync_wire_flushes_fifo_once_and_skips_disconnected_sessions(self):
        """The actual decorated responder flushes only after the sync frame."""
        self.protocol.data_to_server(amp.MsgPortal2Server, 1, text=[["+party"], {}])
        self.protocol.data_to_server(amp.MsgPortal2Server, 2, text=[["+sheet"], {}])
        self.protocol.data_to_server(amp.MsgPortal2Server, 1, text=[["+attack A2 Tackle B2"], {}])
        del self.sessions[2]
        client, server, pump = connectedServerAndClient(lambda: self.factory.buildProtocol(None), ServerPeer)
        # iosim's FakeTransport lacks TCP transport's connected attribute.
        server.transport.connected = True
        received = []
        client.callRemote(amp.AdminServer2Portal, packed_data=amp.dumps((0, {
            "operation": amp.PSYNC, "info_dict": {}, "spid": 123,
        }))).addCallback(received.append)
        pump.flush()
        self.assertEqual(received, [{}])
        self.assertEqual(client.messages, [(1, {"text": [["+party"], {}]}),
                                           (1, {"text": [["+attack A2 Tackle B2"], {}]})])
        self.assertFalse(self.factory.pending_player_input)
        client.callRemote(amp.AdminServer2Portal, packed_data=amp.dumps((0, {
            "operation": amp.PSYNC, "info_dict": {}, "spid": 123,
        })))
        pump.flush()
        self.assertEqual(len(client.messages), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
