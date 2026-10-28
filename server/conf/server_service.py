"""Release Server listeners before AMP announces a completed shutdown."""

from evennia.server.service import EvenniaServerService
from evennia.utils import logger
from twisted.application.internet import TCPServer
from twisted.application.service import Service
from twisted.internet.defer import DeferredList, inlineCallbacks, maybeDeferred


class ReloadSafeServerService(EvenniaServerService):
    """Retain Evennia's lifecycle while keeping its AMP restart signal last."""

    @inlineCallbacks
    def stopService(self):
        """Close listening ports before the normal child-service shutdown.

        Twisted's MultiService stops children concurrently. A TCP listener's
        stopListening may finish later than the AMP client's disconnect, so the
        Portal can launch the next Server while the old HTTP port is still bound.
        Evennia's WSGIWebServer also discards TCPServer's close Deferred. Capture
        the listening ports explicitly so both cases wait for actual release.
        Existing save/checkpoint hooks and the normal child stops stay intact.
        """
        Service.stopService(self)
        closing = []
        for child in self:
            if isinstance(child, TCPServer):
                listener = getattr(child, '_port', None)
                if listener is not None:
                    # TCPServer normally clears this volatile reference itself.
                    # Detach it now so its later stop won't close the port twice.
                    child._port = None
                    closing.append(maybeDeferred(listener.stopListening))
        outcomes = yield DeferredList(closing, consumeErrors=True)
        for succeeded, outcome in outcomes:
            if not succeeded:
                outcome.raiseException()
        logger.log_msg('Server listening ports closed; stopping child services and AMP.')
        result = yield super().stopService()
        return result
