"""Room-owned bounded cleanup timer for ordinary Multi Battle requests/sessions."""

from datetime import datetime

from django.db import transaction
from django.utils import timezone
from evennia import DefaultScript


class MultiRoomWatch(DefaultScript):
    """Expire only this room's saved Multi lobby and active Multi sessions."""

    def at_script_creation(self):
        """Use a persistent timer without restarting any game service."""
        self.interval, self.persistent, self.start_delay = 30, True, True

    def at_repeat(self):
        """Reconnect exact controllers before enforcing the unchanged deadline."""
        from evennia.objects.models import ObjectDB
        from pokemon.services.battle_rewards import BattleRewards
        from pokemon.battle.multi_lobby import KEY
        from pokemon.battle.multi_battle import check_timeout
        from pokemon.battle.battleinstance import BattleSession
        from pokemon.battle.storage import BattleDataWrapper
        room = self.obj
        if not room:
            self.stop()
            return
        with transaction.atomic():
            ObjectDB.objects.select_for_update().get(pk=room.pk)
            lobby = BattleRewards.stored_attribute(room, KEY)
            if lobby and datetime.fromisoformat(lobby['expires']) <= timezone.now():
                room.attributes.remove(KEY)
            elif lobby:
                # An absent controller cannot leave old readiness behind and
                # return to a launch they did not review after rejoining.
                members = lobby['members']
                absent = []
                for label, row in members.items():
                    player = ObjectDB.objects.filter(pk=row['character']).first()
                    if not player or player.db_location_id != room.pk or not player.sessions.all():
                        absent.append(label)
                if any(members[label]['character'] == lobby['host'] for label in absent):
                    room.attributes.remove(KEY)
                elif absent:
                    for label in absent:
                        members.pop(label)
                    for row in members.values():
                        row['ready'] = False
                    room.attributes.add(KEY, lobby)
        active = False
        for battle_id in BattleRewards.stored_attribute(room, 'battles', default=[]) or []:
            saved = BattleRewards.stored_attribute(room, BattleDataWrapper(room, battle_id)._key('state')) or {}
            if not saved.get('multi'):
                continue
            active = True
            try:
                session = (getattr(room.ndb, 'battle_instances', None) or {}).get(battle_id)
                session = session or BattleSession.restore(room, battle_id)
                if session:
                    if session.state.multi.get('result'):
                        session.end()
                    else:
                        check_timeout(session)
            except Exception:
                from evennia.utils.logger import log_warn
                log_warn(f'Multi Battle {battle_id} timer recovery remains pending.', exc_info=True)
        if not active and not BattleRewards.stored_attribute(room, KEY):
            self.delete()
