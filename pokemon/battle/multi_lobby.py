"""Room-local persisted consent for four-controller Multi PvP sessions."""

from contextlib import contextmanager
from datetime import datetime, timedelta
from uuid import uuid4

from django.db import transaction
from django.utils import timezone

from pokemon.services.battle_rewards import BattleRewards
from pokemon.services.ownership import acting_character, assert_character_free, locked_owners

from .multi_state import POSITIONS

KEY = 'multi_pvp_lobby'


class MultiLobby:
    """Serialize lobby joins/readiness and launch using the existing room row."""

    def __init__(self, actor, *, clock=None):
        """Bind real character authority and its current room, never an account ID."""
        self.actor = acting_character(actor)
        if not self.actor.is_typeclass('evennia.objects.objects.DefaultCharacter', exact=False):
            raise ValueError('Use Multi PvP as your active character.')
        self.room = self.actor.location
        if self.room is None:
            raise ValueError('Enter a room before creating or joining Multi PvP.')
        self.clock = clock or timezone.now

    @contextmanager
    def locked(self):
        """Read current SQL after the room lock, without cached Attribute maps."""
        from evennia.objects.models import ObjectDB
        with transaction.atomic():
            room = ObjectDB.objects.select_for_update().get(pk=self.room.pk)
            saved = BattleRewards.stored_attribute(room, KEY)
            if saved and datetime.fromisoformat(saved['expires']) <= self.clock():
                room.attributes.remove(KEY)
                saved = None
            yield room, saved

    @staticmethod
    def save(room, lobby):
        """Persist one detached whole mapping, never an autosaving partial edit."""
        room.attributes.add(KEY, lobby)

    def _available(self, player):
        """Revalidate current ownership, battle freedom and usable canonical party."""
        from evennia.objects.models import ObjectDB
        from utils.character_reads import existing_trainer, existing_storage
        from pokemon.helpers.party_helpers import has_usable_pokemon
        if ObjectDB.objects.values_list('db_location_id', flat=True).get(pk=player.pk) != self.room.pk:
            raise ValueError(f'{player.key} must be in this room.')
        if not player.account or not player.sessions.all() or not existing_trainer(player) or not existing_storage(player):
            raise ValueError(f'{player.key} must finish character setup and be connected.')
        assert_character_free(player)
        if not has_usable_pokemon(player):
            raise ValueError(f'{player.key} needs a conscious eligible Pokemon.')

    def create(self):
        """Create one expiring room request; no pre-battle movement/asset locks."""
        with self.locked() as (room, lobby):
            if lobby:
                raise ValueError('This room already has a Multi lobby. Use +pvp/multi status or join.')
            with locked_owners([self.actor.pk]):
                self._available(self.actor)
            lobby = {'version': 1, 'id': str(uuid4()), 'host': self.actor.pk,
                'expires': (self.clock() + timedelta(minutes=10)).isoformat(),
                'members': {'A1': {'character': self.actor.pk, 'name': self.actor.key, 'ready': False}}}
            self.save(room, lobby)
            self._watch(room)
            return self.describe(lobby)

    @staticmethod
    def _watch(room):
        """Install one room-owned timer so idle lobbies/battles cannot strand players."""
        from evennia.scripts.models import ScriptDB
        from evennia.utils.create import create_script
        key = 'multi-pvp-watch-' + str(room.pk)
        if not ScriptDB.objects.filter(db_key=key, db_obj_id=room.pk).exists():
            create_script('typeclasses.multi_battle.MultiRoomWatch', key=key, obj=room)

    def status(self):
        """Discover current saved consent and expiry without granting a role."""
        with self.locked() as (_, lobby):
            return self.describe(lobby) if lobby else 'No open Multi lobby here. Use +pvp/multi create.'

    def join(self, slot):
        """Choose an empty own team slot; joining invalidates all old readiness."""
        slot = slot.upper()
        if slot not in POSITIONS:
            raise ValueError('Choose A1, A2, B1 or B2.')
        with self.locked() as (room, lobby):
            if not lobby:
                raise ValueError('There is no open Multi lobby here.')
            members = lobby['members']
            if slot in members:
                raise ValueError('That team slot is already occupied.')
            ids = [row['character'] for row in members.values()]
            from evennia.objects.models import ObjectDB
            players = list(ObjectDB.objects.filter(pk__in=ids))
            if any(player.pk != self.actor.pk and player.account == self.actor.account for player in players):
                raise ValueError('Multi requires four distinct player accounts; an alternate cannot fill another slot.')
            old = next((label for label, row in members.items() if row['character'] == self.actor.pk), None)
            if old == 'A1' and self.actor.pk == lobby['host']:
                raise ValueError('The host keeps A1; cancel and ask another player to host if needed.')
            with locked_owners([self.actor.pk]):
                self._available(self.actor)
            if old:
                members.pop(old)
            members[slot] = {'character': self.actor.pk, 'name': self.actor.key, 'ready': False}
            for row in members.values():
                row['ready'] = False
            self.save(room, lobby)
            return self.describe(lobby)

    def ready(self, value=True):
        """Only the current character can consent or revoke its own readiness."""
        with self.locked() as (room, lobby):
            if not lobby:
                raise ValueError('There is no open Multi lobby here.')
            own = next((row for row in lobby['members'].values() if row['character'] == self.actor.pk), None)
            if own is None:
                raise ValueError('Join a team slot first with +pvp/multi join A2, B1 or B2.')
            with locked_owners([self.actor.pk]):
                self._available(self.actor)
            own['ready'] = bool(value)
            self.save(room, lobby)
            return self.describe(lobby)

    def leave(self):
        """Leaving clears readiness; the host cancels the whole open request."""
        with self.locked() as (room, lobby):
            if not lobby:
                raise ValueError('There is no open Multi lobby here.')
            own = next((slot for slot, row in lobby['members'].items() if row['character'] == self.actor.pk), None)
            if own is None:
                raise ValueError('You have not joined this lobby.')
            if self.actor.pk == lobby['host']:
                room.attributes.remove(KEY)
                return 'Multi lobby cancelled. No battle or asset locks were acquired.'
            lobby['members'].pop(own)
            for row in lobby['members'].values():
                row['ready'] = False
            self.save(room, lobby)
            return 'You left the Multi lobby. Remaining players must ready again.'

    def start(self):
        """Atomically consume four current consents only with a saved complete battle."""
        from evennia.objects.models import ObjectDB
        from .battleinstance import BattleSession
        from .multi_battle import start
        session, players = None, {}
        try:
            with self.locked() as (room, lobby):
                if not lobby:
                    raise ValueError('There is no open Multi lobby here; it may already have started or expired.')
                if self.actor.pk != lobby['host']:
                    raise ValueError('Only the host can start this lobby.')
                if set(lobby['members']) != set(POSITIONS) or not all(row['ready'] for row in lobby['members'].values()):
                    raise ValueError('All four slots must be occupied and explicitly ready.')
                ids = [row['character'] for row in lobby['members'].values()]
                if len(set(ids)) != 4:
                    raise ValueError('Multi requires four different characters.')
                with locked_owners(ids):
                    players = {label: ObjectDB.objects.get(pk=row['character']) for label, row in lobby['members'].items()}
                    if len({player.account.pk for player in players.values() if player.account}) != 4:
                        raise ValueError('Multi requires four distinct connected player accounts.')
                    for player in players.values():
                        self._available(player)
                    session = BattleSession.__new__(BattleSession)
                    session.__init__(players['A1'], players['B1'])
                    start(session, players)
                    room.attributes.remove(KEY)
                    room.attributes.add('multi_pvp_last_start', {'lobby': lobby['id'], 'battle': session.battle_id, 'controllers': ids})
            return session
        except Exception:
            self.room.attributes.reset_cache()
            for player in players.values():
                player.attributes.reset_cache()
                if getattr(player.ndb, 'battle_instance', None) is session:
                    player.ndb.battle_instance = None
            if session is not None and getattr(session, 'battle_id', None) is not None:
                instances = getattr(self.room.ndb, 'battle_instances', None) or {}
                if instances.get(session.battle_id) is session:
                    instances.pop(session.battle_id, None)
                from .handler import battle_handler
                if battle_handler.instances.get(session.battle_id) is session:
                    battle_handler.unregister(session)
            raise

    @staticmethod
    def describe(lobby):
        """Show names, stable team positions, consent and actionable discovery."""
        lines = [f"Multi lobby {lobby['id']} (expires {lobby['expires']}):"]
        for label in POSITIONS:
            row = lobby['members'].get(label)
            lines.append(f"{label}: {row['name']} — {'READY' if row['ready'] else 'not ready'}" if row else f'{label}: open')
        return '\n'.join([*lines, '+pvp/multi join <slot>; ready; unready; leave. All four must ready, then the host uses +pvp/multi start.'])
