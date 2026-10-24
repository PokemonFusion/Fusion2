"""Serialize existing Script/Attribute board state without replacing board storage."""

from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps

ACTIVE_BOARDS = ContextVar('pf2_active_board_transactions', default=frozenset())


class BoardError(ValueError):
    """An unavailable, changed or unauthorized board operation made no partial write."""


class BoardTransaction:
    """Lock one persistent board and discard stale Evennia Attribute/lock caches."""

    def __init__(self, board):
        """Permit the existing pure adapters while guarding every persisted board."""
        self.board = board
        self.identifier = getattr(board, 'pk', None)

    @property
    def persistent(self):
        """Only production Script instances have a database identity to serialize."""
        return self.identifier is not None

    def refresh(self):
        """Read authoritative attributes and lock text, including after rollback."""
        if not self.persistent:
            return
        from evennia.scripts.models import ScriptDB
        from evennia.typeclasses.attributes import Attribute
        row = ScriptDB.objects.filter(pk=self.identifier).values('db_lock_storage').first()
        if row is None:
            raise BoardError('This board is no longer available.')
        self.board.db_lock_storage = row['db_lock_storage']
        self.board.locks.reset()
        for identifier in self.board.db_attributes.values_list('pk', flat=True):
            cached = Attribute.get_cached_instance(identifier)
            if cached is not None:
                Attribute.flush_cached_instance(cached)
        self.board.attributes.reset_cache()

    @contextmanager
    def locked(self):
        """Take the Script row before reading/replacing its saved posts/read map."""
        if not self.persistent:
            yield
            return
        if self.identifier in ACTIVE_BOARDS.get():
            yield
            return
        from django.db import transaction
        from evennia.scripts.models import ScriptDB
        try:
            with transaction.atomic():
                if not ScriptDB.objects.select_for_update().filter(pk=self.identifier).values('pk').first():
                    raise BoardError('This board is no longer available.')
                self.refresh()
                token = ACTIVE_BOARDS.set(ACTIVE_BOARDS.get() | {self.identifier})
                try:
                    yield
                finally:
                    # Commit callbacks must start a fresh operation after this
                    # row lock is released, rather than inheriting a stale scope.
                    ACTIVE_BOARDS.reset(token)
        finally:
            self.refresh()

    def require(self, actor, action):
        """Recheck board access at the actual read/save, including an old editor."""
        if self.persistent:
            from evennia.objects.models import ObjectDB
            from evennia.objects.objects import DefaultCharacter
            if not isinstance(actor, ObjectDB) or not actor.is_typeclass(DefaultCharacter, exact=False):
                raise BoardError('Use bulletin boards as your active character.')
        if self.persistent and (actor is None or not self.board.access(actor, action, default=False)):
            raise BoardError(f'You are not allowed to {action} this board.')

    def notify(self, callback):
        """Deliver only committed notices; transport failure cannot undo a saved post."""
        def deliver():
            """Keep notification failures separate from persisted post success."""
            import logging
            try:
                callback()
            except Exception:
                logging.getLogger(__name__).exception('Could not notify readers of an already-saved board post')
        if self.persistent:
            from django.db import transaction
            transaction.on_commit(deliver)
        else:
            deliver()


def serialized(method):
    """Keep all reads, legacy normalization and compound writes on one board lock."""
    @wraps(method)
    def operation(self, *args, **kwargs):
        """Nested calls retain the same transaction/row lock and fresh stored state."""
        with BoardTransaction(self).locked():
            return method(self, *args, **kwargs)
    return operation
