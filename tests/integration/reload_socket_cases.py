"""Exercise real reactor sockets, deferred HTTP closes and AMP disconnect timing."""

import json
import os
from pathlib import Path
import socket
import sys
from types import SimpleNamespace
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'server.conf.settings')

from twisted.application.internet import TCPClient
from twisted.application.service import MultiService
from twisted.internet import defer, protocol, task
from twisted.protocols.amp import AMP
from evennia.server.webserver import WSGIWebServer
from server.conf.server_service import ReloadSafeServerService


class DelayedClose:
    """Keep the real listening port live while its async close is pending."""

    def __init__(self, reactor, port):
        self.reactor = reactor
        self.port = port
        self.done = defer.Deferred()

    def stopListening(self):
        """Model a slower listener close without any production sleeps/retries."""
        closing = task.deferLater(self.reactor, 0.05, self.port.stopListening)
        closing.chainDeferred(self.done)
        return self.done


@defer.inlineCallbacks
def scenario(reactor, fixed):
    """Attempt the next bind on a real remote AMP transport's disconnect."""
    observed = defer.Deferred()
    connected = defer.Deferred()
    address = {}

    class PortalPeer(AMP):
        """Observe the real connection loss used as Evennia's restart signal."""

        def connectionMade(self):
            super().connectionMade()
            connected.callback(None)

        def connectionLost(self, reason):
            super().connectionLost(reason)
            with socket.socket() as replacement:
                try:
                    replacement.bind(('127.0.0.1', address['port']))
                    replacement.listen()
                    observed.callback(True)
                except OSError:
                    observed.callback(False)

    portal_factory = protocol.Factory.forProtocol(PortalPeer)
    portal = reactor.listenTCP(0, portal_factory, interface='127.0.0.1')
    if fixed:
        services = ReloadSafeServerService.__new__(ReloadSafeServerService)
        MultiService.__init__(services)
    else:
        services = MultiService()
    factory = protocol.ClientFactory.forProtocol(AMP)
    control = TCPClient('127.0.0.1', portal.getHost().port, factory, reactor=reactor)
    control.setServiceParent(services)
    services.amp_service = control
    pool = SimpleNamespace(started=False, start=Mock(), stop=Mock())
    web = WSGIWebServer(pool, 0, protocol.Factory.forProtocol(protocol.Protocol),
                        interface='127.0.0.1', reactor=reactor)
    web.setServiceParent(services)
    services.startService()
    yield connected.addTimeout(5, reactor)
    address['port'] = web._port.getHost().port
    listener = DelayedClose(reactor, web._port)
    web._port = listener
    try:
        yield services.stopService().addTimeout(5, reactor)
        available = yield observed.addTimeout(5, reactor)
        yield listener.done.addTimeout(5, reactor)
        assert available is fixed, ('fixed' if fixed else 'unfixed', available)
    finally:
        yield portal.stopListening()
    return dict(fixed=fixed, replacement_bind_succeeded=available)


@defer.inlineCallbacks
def main(reactor):
    """Keep the process database-free while repeating the actual socket handoff."""
    with patch('django.db.backends.base.base.BaseDatabaseWrapper.cursor',
               side_effect=AssertionError('Socket handoff tests refuse database access')):
        results = [(yield scenario(reactor, False))]
        for _ in range(5):
            results.append((yield scenario(reactor, True)))
    assert len(results) == 6
    print(json.dumps(dict(unfixed_conflicts=1, fixed_cycles=5, fixed_conflicts=0,
                         results=results, database_access=False)))


if __name__ == '__main__':
    task.react(main)
