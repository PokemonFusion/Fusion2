"""Real Twisted shutdown barriers and loopback binds without any game database."""

import os
from pathlib import Path
import socket
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'server.conf.settings')

from twisted.application.internet import TCPServer
from twisted.application.service import MultiService, Service
from twisted.internet.defer import Deferred


class DelayedListener(Service):
    """Keep a real internal listener bound until asynchronous close completes."""

    def __init__(self):
        self.listener = socket.socket()
        self.listener.bind(('127.0.0.1', 0))
        self.listener.listen()
        self.address = self.listener.getsockname()
        self.stopped = Deferred()
        self.stop_calls = 0

    def stopService(self):
        """Model Twisted's deferred stopListening, not an immediate port close."""
        Service.stopService(self)
        self.stop_calls += 1
        return self.stopped

    def finish(self):
        """Complete the old listener's close before releasing its Deferred."""
        self.listener.close()
        if not self.stopped.called:
            self.stopped.callback(None)

    def stopListening(self):
        """Expose the real TCPServer listening-port close contract."""
        return self.stopService()


class PortalNotification(Service):
    """Try a replacement bind when AMP disconnect tells the Portal to restart."""

    def __init__(self, address):
        self.address = address
        self.stop_calls = 0
        self.bind_error = None
        self.bound = False

    def stopService(self):
        """A real bind distinguishes released listeners from a status-only stop."""
        Service.stopService(self)
        self.stop_calls += 1
        with socket.socket() as replacement:
            try:
                replacement.bind(self.address)
                replacement.listen()
                self.bound = True
            except OSError as error:
                self.bind_error = error


class ServerShutdownCases(unittest.TestCase):
    """Reproduce the old ordering, then require AMP-last on delayed closes."""

    def setUp(self):
        """A lifecycle regression must never reach a game database."""
        guard = patch('django.db.backends.base.base.BaseDatabaseWrapper.cursor',
                      side_effect=AssertionError('Lifecycle tests refuse database access'))
        guard.start()
        self.addCleanup(guard.stop)

    def container(self):
        """Initialize only the real child-service collection, without game startup."""
        from server.conf.server_service import ReloadSafeServerService
        container = ReloadSafeServerService.__new__(ReloadSafeServerService)
        MultiService.__init__(container)
        return container

    def fixture(self, container):
        """Use Evennia's real registration order: AMP first, listener second."""
        listener = DelayedListener()
        self.addCleanup(listener.finish)
        amp = PortalNotification(listener.address)
        amp.setName('ServerAMPClient')
        amp.setServiceParent(container)
        web = TCPServer(listener.address[1])
        web._port = listener
        web.setName('EvenniaWebServer')
        web.setServiceParent(container)
        container.amp_service = amp
        return listener, amp

    def test_upstream_parallel_stop_reproduces_bind_conflict(self):
        """The old parent announces disconnect before stopListening completes."""
        container = MultiService()
        listener, amp = self.fixture(container)
        completed = []
        container.stopService().addCallback(completed.append)
        self.assertEqual(amp.stop_calls, 1)
        self.assertIsInstance(amp.bind_error, OSError)
        self.assertFalse(completed)
        listener.finish()
        self.assertEqual(len(completed), 1)

    def test_project_server_waits_for_actual_listener_close(self):
        """The same socket can bind at AMP disconnect only after the fix."""
        container = self.container()
        listener, amp = self.fixture(container)
        completed = []
        container.stopService().addCallback(completed.append)
        self.assertEqual(listener.stop_calls, 1)
        self.assertEqual(amp.stop_calls, 0)
        self.assertFalse(completed)
        listener.finish()
        self.assertEqual(amp.stop_calls, 1)
        self.assertTrue(amp.bound)
        self.assertIsNone(amp.bind_error)
        self.assertEqual(len(completed), 1)

    def test_real_evennia_wsgi_discarded_close_is_awaited(self):
        """Evennia 6.0's actual WSGI stop throws away TCPServer's Deferred."""
        from evennia.server.webserver import WSGIWebServer
        container = self.container()
        listener = DelayedListener()
        self.addCleanup(listener.finish)
        amp = PortalNotification(listener.address)
        amp.setServiceParent(container)
        container.amp_service = amp
        pool = SimpleNamespace(started=True, stop=Mock())
        web = WSGIWebServer(pool, listener.address[1])
        web._port = listener
        web.setServiceParent(container)
        completed = []
        container.stopService().addCallback(completed.append)
        self.assertEqual(listener.stop_calls, 1)
        pool.stop.assert_not_called()
        self.assertEqual(amp.stop_calls, 0)
        self.assertFalse(completed)
        listener.finish()
        pool.stop.assert_called_once()
        self.assertTrue(amp.bound)
        self.assertIsNone(amp.bind_error)
        self.assertEqual(len(completed), 1)

    def test_settings_select_real_server_subclass(self):
        """Evennia's configured extension owns shutdown, without patching its files."""
        from django.conf import settings
        from evennia.server.service import EvenniaServerService
        from evennia.utils.utils import class_from_module
        from server.conf.server_service import ReloadSafeServerService
        self.assertIs(class_from_module(settings.EVENNIA_SERVER_SERVICE_CLASS), ReloadSafeServerService)
        self.assertTrue(issubclass(ReloadSafeServerService, EvenniaServerService))

    def test_all_listeners_must_close_before_control_disconnect(self):
        """Out-of-order closes on multiple internal ports keep AMP alive."""
        container = self.container()
        first, amp = self.fixture(container)
        second = DelayedListener()
        self.addCleanup(second.finish)
        web = TCPServer(second.address[1])
        web._port = second
        web.setServiceParent(container)
        completed = []
        container.stopService().addCallback(completed.append)
        self.assertEqual(first.stop_calls, 1)
        self.assertEqual(second.stop_calls, 1)
        second.finish()
        self.assertEqual(amp.stop_calls, 0)
        self.assertFalse(completed)
        first.finish()
        self.assertEqual(amp.stop_calls, 1)
        self.assertTrue(amp.bound)
        self.assertEqual(len(completed), 1)

    def test_failed_listener_close_is_not_reported_as_clean_disconnect(self):
        """A failed close is surfaced without prematurely triggering a replacement."""
        container = self.container()
        listener, amp = self.fixture(container)
        failed = []
        container.stopService().addErrback(failed.append)
        listener.stopped.errback(RuntimeError('listener close failed'))
        self.assertEqual(len(failed), 1)
        self.assertIs(failed[0].type, RuntimeError)
        self.assertEqual(amp.stop_calls, 0)

    def test_empty_or_partially_started_server_still_stops_normally(self):
        """A failed startup with no listening port needs no invented close wait."""
        container = self.container()
        empty = []
        container.stopService().addCallback(empty.append)
        self.assertEqual(empty, [[]])
        container = self.container()
        child = TCPServer(1)
        child.setServiceParent(container)
        completed = []
        container.stopService().addCallback(completed.append)
        self.assertEqual(completed, [[(True, None)]])

    def test_async_control_stop_remains_part_of_service_completion(self):
        """Closing the HTTP port must not skip waiting for the AMP child itself."""
        container = self.container()
        listener, amp = self.fixture(container)
        control_done = Deferred()
        original_stop = amp.stopService
        def stop_control():
            original_stop()
            return control_done
        amp.stopService = stop_control
        completed = []
        container.stopService().addCallback(completed.append)
        listener.finish()
        self.assertTrue(amp.bound)
        self.assertFalse(completed)
        control_done.callback(None)
        self.assertEqual(len(completed), 1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
