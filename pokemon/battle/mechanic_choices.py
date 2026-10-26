"""Serialize new player-mechanic declarations against the saved session identity."""

from contextlib import contextmanager
from copy import deepcopy


class MechanicChoices:
    """Keep reservations, saved state and notices in one room-locked transaction."""

    @staticmethod
    @contextmanager
    def locked(choices, *, preserve_state=False):
        """Reject stale inputs rather than overwriting another controller's checkpoint."""
        from django.db import connection, transaction
        from evennia.objects.models import ObjectDB
        from pokemon.services.battle_rewards import BattleRewards

        session, battle = choices.session, choices.battle
        if connection.in_atomic_block:
            raise ValueError("Submit this declaration as a fresh battle input and try again.")
        with transaction.atomic():
            room = ObjectDB.objects.select_for_update().get(pk=session.room.id)
            saved = BattleRewards.stored_attribute(room, session.storage._key("state"))
            data = BattleRewards.stored_attribute(room, session.storage._key("data"))
            if (
                not saved
                or not data
                or saved.get("reward_id") != session.state.reward_id
                or saved.get("ending")
                or session.state.ending
                or saved.get("mechanic_turn", 0) != battle.mechanic_turn
                or dict(saved.get("declare", {})) != dict(session.state.declare)
            ):
                raise ValueError(
                    "The battle input changed; refresh your current choices and try again."
                )
            for name in ("mega", "z", "tera"):
                setattr(battle, name + "_used", set(saved.get(name + "_used", [])))
                setattr(battle, name + "_pending", deepcopy(dict(saved.get(name + "_pending", {}))))
            previous = {
                name + suffix: deepcopy(getattr(battle, name + suffix))
                for name in ("mega", "z", "tera")
                for suffix in ("_used", "_pending")
            }
            old_state = deepcopy(session.state.to_dict()) if preserve_state else None
            old_declarations = deepcopy(session.state.declare)
            old_actions = choices.participant.pending_action
            old_positions = {name: deepcopy(position.turninit)
                             for name, position in session.data.turndata.positions.items()}
            try:
                if getattr(session.state, 'multi', None):
                    from datetime import datetime
                    from django.utils import timezone
                    if datetime.fromisoformat(session.state.multi['deadline']) <= timezone.now():
                        raise ValueError('The action deadline expired. The room timer will finish this Multi Battle; use +status to check it.')
                character = BattleRewards.character(choices.caller)
                if (
                    str(BattleRewards.stored_attribute(character, "battle_id"))
                    != str(session.battle_id)
                    or BattleRewards.stored_attribute(character, "battle_control") is not True
                ):
                    raise ValueError("This battle is not waiting for your current control.")
                battle.mechanic_session_id = str(session.battle_id)
                choices._check(*choices._mechanic_actor)
                yield
                session.logic.sync_runtime_state()
                session.storage.set(
                    "state", session._compact_state_for_persist(session.state.to_dict())
                )
            except Exception:
                for name, value in previous.items():
                    setattr(battle, name, value)
                session.state.declare = old_declarations
                choices.participant.pending_action = old_actions
                for name, turninit in old_positions.items():
                    session.data.turndata.positions[name].turninit = turninit
                session.logic.sync_runtime_state()
                if old_state is not None:
                    session.logic.state = type(session.state).from_dict(old_state)
                session.room.attributes.reset_cache()
                raise

    @classmethod
    def mega(cls, choices, *, actor=None, cancel=False):
        """Reserve or cancel only the caller's unqueued current active slot."""
        from django.db import transaction
        from .mega_evolution import MegaEvolution
        from .terastallization import Terastallization

        position, pokemon = choices.actor(actor)
        choices._check(position, pokemon)
        choices._mechanic_actor = (position, pokemon)
        battle = choices.battle
        side = Terastallization.side(battle, choices.participant)
        with cls.locked(choices):
            if cancel:
                request = battle.mega_pending.get(side, {})
                if request.get("pokemon") != Terastallization.identifier(pokemon):
                    raise ValueError("That Pokemon has no Mega Evolution reserved.")
                battle.mega_pending.pop(side)
                message = f"{position}: Mega Evolution cancelled."
            else:
                request = MegaEvolution.reserve(battle, choices.participant, pokemon)
                message = f"{position} ({pokemon.name}): {request['target']} reserved. Choose a move with +attack."
            transaction.on_commit(lambda: choices.caller.msg(message), robust=True)

    @staticmethod
    def cancel_nonmove(battle, participant, pokemon):
        """A legal switch/item/flee cannot inherit another action's reservation."""
        from .terastallization import Terastallization

        side = Terastallization.side(battle, participant)
        identifier = Terastallization.identifier(pokemon)
        for name in ("mega", "z", "tera"):
            ledger = getattr(battle, name + "_pending", {})
            if ledger.get(side, {}).get("pokemon") == identifier:
                ledger.pop(side, None)
