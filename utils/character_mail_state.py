"""Recipient-specific state on existing Evennia mail messages and tags."""

from contextlib import contextmanager

STATE_CATEGORY = 'pf2_mail_recipient_state'


class CharacterMailboxState:
    """Serialize message mutations while keeping each character's read state separate."""

    def __init__(self, character=None):
        """Keep actor identity distinct from an account or another recipient."""
        self.character = character

    @staticmethod
    def _mail():
        """Load formatting/lookup helpers without an import cycle."""
        from utils import character_mail
        return character_mail

    @classmethod
    def _persistent(cls):
        """Use transaction guarantees with the real manager, preserving pure adapters."""
        return callable(getattr(cls._mail()._msg_model().objects, 'select_for_update', None))

    @classmethod
    def validate_character(cls, actor):
        """Production mail belongs to a real character, never a coincident account ID."""
        if cls._persistent():
            from evennia.objects.models import ObjectDB
            from evennia.objects.objects import DefaultCharacter
            if not isinstance(actor, ObjectDB) or not actor.is_typeclass(DefaultCharacter, exact=False):
                raise cls._mail().CharacterMailError('Use character mail as your active character.')
        return actor

    def recipient(self, message):
        """Infer only an unambiguous single recipient for older helper callers."""
        mail = self._mail()
        receivers = list(message.receivers or [])
        actor = self.character
        if actor is None:
            if len(receivers) != 1:
                raise mail.CharacterMailError('Shared mail needs an explicit character recipient.')
            actor = receivers[0]
        self.validate_character(actor)
        if self._persistent():
            from evennia.objects.models import ObjectDB
            matches = [receiver for receiver in receivers if isinstance(receiver, ObjectDB) and receiver.pk == actor.pk]
        else:
            matches = [receiver for receiver in receivers if mail.character_identity(actor) == mail.character_identity(receiver)]
        if not matches:
            raise mail.CharacterMailError('That mail does not belong to this character.')
        return actor

    @staticmethod
    def _tag(message, key):
        """Read persistent state freshly instead of trusting a prior session's tag cache."""
        manager = getattr(message, 'db_tags', None)
        if callable(getattr(manager, 'filter', None)):
            return manager.filter(db_key=key, db_category=STATE_CATEGORY).exists()
        return bool(message.tags.has(key, category=STATE_CATEGORY))

    def is_unread(self, message):
        """Retain the legacy shared flag only as the untouched recipient's baseline."""
        mail = self._mail()
        actor = self.recipient(message)
        identifier = str(mail.character_identity(actor))
        if self._tag(message, 'read:' + identifier):
            return False
        if self._tag(message, 'unread:' + identifier):
            return True
        return mail._has_tag(message, mail.UNREAD_TAG)

    def _set(self, message, *, unread):
        """Write just this recipient's mutually exclusive override tags."""
        actor = self.recipient(message)
        identifier = str(self._mail().character_identity(actor))
        message.tags.remove(('read:' if unread else 'unread:') + identifier, category=STATE_CATEGORY)
        message.tags.add(('unread:' if unread else 'read:') + identifier, category=STATE_CATEGORY)
        return message

    @contextmanager
    def transaction(self):
        """Use the production transaction boundary without a database in pure adapters."""
        if self._persistent():
            from django.db import transaction
            with transaction.atomic():
                yield
        else:
            yield

    @contextmanager
    def locked(self, raw_id):
        """Lock one existing message and then recheck current recipient visibility."""
        mail = self._mail()
        self.validate_character(self.character)
        needle = mail.parse_mail_id(raw_id)
        with self.transaction():
            if self._persistent():
                row = mail._msg_model().objects.select_for_update().filter(pk=needle).values('pk').first()
                if row is None:
                    raise mail.CharacterMailError(f'No mail #{needle} found.')
            message = mail.get_character_mail(self.character, needle)
            self.recipient(message)
            yield message

    def read(self, raw_id, *, unread=False):
        """Read/unread retries change only this character, including shared messages."""
        with self.locked(raw_id) as message:
            return self._set(message, unread=unread)

    def archive(self, raw_id):
        """Hide only this recipient's inbox entry without deleting the shared message."""
        with self.locked(raw_id) as message:
            self._set(message, unread=False)
            hidden = getattr(message, 'db_hide_from_objects', None)
            if callable(getattr(hidden, 'add', None)):
                hidden.add(self.character)
            else:
                hidden_for = getattr(message, 'hidden_for', set())
                hidden_for.add(self._mail().character_identity(self.character))
                message.hidden_for = hidden_for
            return message
