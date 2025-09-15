"""Command allowing a player to concede an active battle."""

from __future__ import annotations

from evennia import Command
from evennia.utils.evmenu import get_input

from world.system_init import get_system

from .cmd_battle_utils import NOT_IN_BATTLE_MSG


class CmdBattleConcede(Command):
    """Forfeit the current battle after confirmation.

    Usage:
      +battle/concede
      +concede
    """

    key = "+battle/concede"
    aliases = ["+concede", "+Concede", "+battleconcede"]
    locks = "cmd:all()"
    help_category = "Pokemon/Battle"

    def func(self) -> None:
        """Prompt for confirmation and process a concession."""
        if not getattr(self.caller.db, "battle_control", False):
            self.caller.msg("|rWe aren't waiting for you to command right now.")
            return

        system = get_system()
        manager = getattr(system, "battle_manager", None)
        inst = manager.for_player(self.caller) if manager else None
        if not inst:
            try:  # pragma: no cover - battle session may be absent in tests
                from pokemon.battle.battleinstance import BattleSession
            except Exception:  # pragma: no cover

                class BattleSession:  # type: ignore[override]
                    @staticmethod
                    def ensure_for_player(caller):
                        return getattr(caller.ndb, "battle_instance", None)

            inst = BattleSession.ensure_for_player(self.caller)
        if not inst:
            self.caller.msg(NOT_IN_BATTLE_MSG)
            return

        if not self._has_active_battle(inst):
            self.caller.msg(NOT_IN_BATTLE_MSG)
            return

        confirmation = (self.args or "").strip().lower()
        if confirmation:
            if confirmation in {"y", "yes"}:
                self._finalize_concession(inst, manager)
            else:
                self.caller.msg("Concession cancelled.")
            return

        prompt = (
            "Are you sure you want to concede this battle? Type |wyes|n to confirm "
            "or anything else to cancel."
        )

        def _confirm(caller, _prompt, response):
            """Handle the confirmation prompt result."""

            if (response or "").strip().lower() not in {"y", "yes"}:
                caller.msg("Concession cancelled.")
                return False
            self._finalize_concession(inst, manager)
            return False

        try:
            get_input(self.caller, prompt, _confirm)
        except Exception:
            self.caller.msg("Unable to open a confirmation prompt. Use '+concede yes' to confirm.")

    # ------------------------------------------------------------------
    # Helper utilities
    # ------------------------------------------------------------------
    def _has_active_battle(self, inst) -> bool:
        """Return ``True`` if ``inst`` appears to represent an active battle."""

        if getattr(inst, "battle", None):
            return True
        if getattr(inst, "logic", None):
            return True
        state = getattr(getattr(inst, "db", None), "state", None)
        return bool(state)

    def _finalize_concession(self, inst, manager) -> None:
        """Carry out the concession once confirmation has been received."""

        battle_id = self._extract_battle_id(inst)
        recorded = False
        if manager and battle_id is not None:
            try:
                recorded = bool(manager.abort_request(int(battle_id), self.caller))
            except Exception:
                recorded = False
        if not recorded and manager and battle_id is not None:
            self.caller.msg("Unable to contact the battle manager; ending the battle locally.")

        self.caller.msg("You concede the battle.")
        message = f"{getattr(self.caller, 'key', 'Someone')} has conceded the battle."

        opponents = self._gather_participants(inst)
        for opponent in opponents:
            try:
                opponent.msg(message)
            except Exception:
                continue
            if hasattr(opponent, "db"):
                try:
                    opponent.db.battle_control = False
                except Exception:
                    pass

        notified = False
        if hasattr(inst, "notify"):
            try:
                inst.notify(message)
                notified = True
            except Exception:
                notified = False
        if not notified and hasattr(inst, "msg"):
            try:
                inst.msg(message)
            except Exception:
                pass

        if hasattr(self.caller, "db"):
            try:
                self.caller.db.battle_control = False
            except Exception:
                pass

        if hasattr(inst, "end"):
            try:
                inst.end()
                return
            except Exception:
                pass

        if manager and battle_id is not None and hasattr(manager, "abort"):
            try:
                manager.abort(int(battle_id))
            except Exception:
                pass

    def _extract_battle_id(self, inst) -> int | None:
        """Best effort extraction of a battle identifier from ``inst``."""

        battle_id = getattr(inst, "battle_id", None)
        if not battle_id:
            state = getattr(getattr(inst, "db", None), "state", None)
            if isinstance(state, dict):
                battle_id = state.get("id")
        if not battle_id:
            battle_id = getattr(getattr(self.caller, "db", None), "battle_id", None)
        if battle_id is None:
            return None
        try:
            return int(battle_id)
        except (TypeError, ValueError):
            return None

    def _gather_participants(self, inst) -> list:
        """Collect other trainers involved in the battle."""

        participants = []

        def _add(obj) -> None:
            if not obj or obj is self.caller:
                return
            for existing in participants:
                if existing is obj:
                    return
            participants.append(obj)

        trainers = getattr(inst, "trainers", None)
        if trainers:
            try:
                for entry in trainers:
                    _add(entry)
            except TypeError:
                pass
        else:
            for attr in ("teamA", "teamB"):
                team = getattr(inst, attr, None)
                if not team:
                    continue
                try:
                    for entry in team:
                        _add(entry)
                except TypeError:
                    continue

        for attr in ("captainA", "captainB"):
            _add(getattr(inst, attr, None))

        battle = getattr(inst, "battle", None)
        if battle:
            for participant in getattr(battle, "participants", []):
                player = getattr(participant, "player", None)
                if player is None:
                    player = getattr(participant, "trainer", None)
                _add(player)

        ndb = getattr(inst, "ndb", None)
        chars = getattr(ndb, "characters", None) if ndb else None
        if isinstance(chars, dict):
            for obj in chars.values():
                _add(obj)

        return participants
