"""Player command for starting and controlling Adventures."""

from __future__ import annotations

from django.db import DatabaseError

try:
    from evennia import Command as _EvenniaCommand
except Exception:  # pragma: no cover - lightweight test fallback
    _EvenniaCommand = None
if _EvenniaCommand is None:  # pragma: no cover - lightweight test fallback
    class Command:  # type: ignore[no-redef]
        pass
else:
    Command = _EvenniaCommand

from .cmdsets import attach_movement_cmdset, detach_movement_cmdset
from .constants import STATE_COMPLETED
from .interlocks import inspect_adventure_battle
from .renderer import render_objectives, render_session, render_template_info
from .sessions import (
    board_offers,
    choose_session_route,
    get_current_session_for_player,
    leave_session,
    retry_encounter_results,
    search_session,
    start_session,
)
from .templates import get_session_template, get_template


_ACTIONS = ("board", "list", "info", "take", "start", "status", "look", "objectives",
            "search", "choose", "retry", "claim", "leave")


def _parse_slash_switches(command) -> set[str]:
    """Extract Evennia-style /switches for bare Command subclasses."""

    switches: list[str] = []
    for switch in getattr(command, "switches", []) or []:
        switches.extend(part for part in str(switch).lower().split("/") if part)

    cmdstring = str(getattr(command, "cmdstring", "") or "").lower()
    if "/" in cmdstring:
        _command, switch_text = cmdstring.split("/", 1)
        switches.extend(part for part in switch_text.split("/") if part)

    raw_args = (command.args or "").strip()
    if raw_args.startswith("/") and len(raw_args) > 1:
        switch_text, _, raw_args = raw_args[1:].partition(" ")
        switches.extend(part for part in switch_text.lower().split("/") if part)
        command.args = raw_args.strip()

    command.switches = set(switches)
    return command.switches


class CmdAdventure(Command):
    """Start and control compact Adventure instances.

    Usage:
      +adventure/board (alias: +adventure/list)
      +adventure/info <adventure>
      +adventure/take <adventure> (alias: +adventure/start)
      +adventure/status
      +adventure/look
      +adventure/objectives
      +adventure/search
      +adventure/choose <wild||trainer>
      +adventure/retry
      +adventure/claim
      +adventure/leave

    Examples:
      +adventure/board
      +adventure/take alpha_meadow
      +adventure/search

    Notes:
      Enter Adventure Hall via the adventures exit. Taking a mission enters
      its instance and saves your progress for reconnect. Bring a battle-ready
      Pokemon for optional encounters. The survey can be done without a Pokemon.
    """

    key = "+adventure"
    aliases = ["+adv"]
    locks = "cmd:all()"
    help_category = "Adventure"

    def parse(self):
        _parse_slash_switches(self)

    def func(self):
        action, arg = self._action_and_arg()
        if action in {"board", "list"}:
            self._list()
        elif action == "info":
            self._info(arg)
        elif action in {"take", "start"}:
            self._start(arg)
        elif action == "status":
            self._status()
        elif action == "look":
            self._look()
        elif action == "objectives":
            self._objectives()
        elif action == "search":
            self._search()
        elif action == "choose":
            self._choose(arg)
        elif action == "retry":
            self._retry()
        elif action == "claim":
            self._claim()
        elif action == "leave":
            self._leave()
        else:
            self.caller.msg(_usage())

    def _action_and_arg(self) -> tuple[str, str]:
        switches = getattr(self, "switches", set())
        for action in _ACTIONS:
            if action in switches:
                return action, (self.args or "").strip()
        raw = (self.args or "").strip()
        if not raw:
            return "help", ""
        first, _, rest = raw.partition(" ")
        first = first.lower()
        if first in _ACTIONS:
            return first, rest.strip()
        return "help", raw

    def _list(self) -> None:
        """Show offers installed on the local Hall's board."""

        templates = board_offers(getattr(self.caller, "location", None))
        if not templates:
            self.caller.msg("No missions are posted here. Go to Adventure Hall to check its mission board. "
                            "Use +adventure/status for your current or most recent run.")
            return
        lines = ["Adventure Mission Board"]
        for template in templates:
            lines.append(f"  {template.key} - {template.name} ({template.category})")
        lines.append("Use +adventure/info <mission> to inspect or +adventure/take <mission> to enter.")
        self.caller.msg("\n".join(lines))

    def _info(self, arg: str) -> None:
        template = get_template(arg)
        if template is None:
            self.caller.msg("Usage: +adventure/info <adventure>")
            return
        from .progress import reward_status

        offered = next((offer for offer in board_offers(getattr(self.caller, "location", None))
                        if offer.key == template.key), None)
        availability = (
            f"Posted here. Use +adventure/take {offered.key} to enter." if offered
            else "This mission is only available while posted at the Adventure Hall board."
        )
        self.caller.msg("\n".join((render_template_info(offered or template), availability,
                                   reward_status(self.caller, template.key))))

    def _start(self, arg: str) -> None:
        if not arg:
            self.caller.msg("Usage: +adventure/take <adventure>")
            return
        try:
            result = start_session(self.caller, arg)
        except DatabaseError:
            self.caller.msg("The mission could not be saved. Use +adventure/take to try again.")
            return
        self.caller.msg(result.message)
        if result.ok and result.session is not None:
            attach_movement_cmdset(self.caller)
            self.caller.msg(render_session(result.session))

    def _status(self) -> None:
        """Show this character's latest run and recovery actions."""

        from .progress import latest_run, reward_status

        session = get_current_session_for_player(self.caller) or latest_run(self.caller)
        lines = ["You have no Adventure runs yet."]
        if session is not None:
            template = get_session_template(session)
            name = template.name if template else session.template_key
            lines = [f"{name} — {session.state.title()}."]
            if outcome := (session.metadata or {}).get("encounter_result"):
                lines.append(f"Encounter result: {outcome}.")
            if session.holds_instance:
                command = "+adventure/leave" if session.state == STATE_COMPLETED else "+adventure/look"
                lines.append(f"Use {command} to continue.")
                gate = inspect_adventure_battle(self.caller, session)
                if gate.blocked:
                    lines.append(gate.message)
            lines.append(reward_status(self.caller, session.template_key))
        if (session is None or not session.holds_instance) and inspect_adventure_battle(self.caller).pending_result:
            lines.append("An encounter result is pending. Use +adventure/retry.")
        self.caller.msg("\n".join(line for line in lines if line))

    def _look(self) -> None:
        session = get_current_session_for_player(self.caller)
        if session is None:
            self.caller.msg("You are not in an adventure.")
            return
        attach_movement_cmdset(self.caller)
        self.caller.msg(render_session(session))

    def _objectives(self) -> None:
        session = get_current_session_for_player(self.caller)
        if session is None:
            self.caller.msg("You are not in an adventure.")
            return
        self.caller.msg("Objectives:\n" + render_objectives(session))

    def _search(self) -> None:
        result = search_session(self.caller)
        self.caller.msg(result.message)
        if result.ok and result.session is not None:
            self.caller.msg("Objectives:\n" + render_objectives(result.session))

    def _choose(self, arg: str) -> None:
        if not arg:
            self.caller.msg("Usage: +adventure/choose <route>")
            return
        try:
            from pokemon.battle.battleinstance import BattleSession
        except Exception:
            BattleSession = None
        if BattleSession is not None:
            try:
                active_battle = BattleSession.ensure_for_player(self.caller)
            except Exception:
                active_battle = getattr(getattr(self.caller, "ndb", None), "battle_instance", None)
            if active_battle:
                self.caller.msg("Finish your current battle before choosing a route.")
                return
            if not BattleSession.has_usable_party(self.caller):
                self.caller.msg("You need a battle-ready Pokemon to choose an encounter. You can continue the survey without battling.")
                return

        result = choose_session_route(self.caller, arg)
        self.caller.msg(result.message)
        if not result.ok or result.session is None or result.data is None:
            return
        if BattleSession is None:
            self.caller.msg("The battle system is unavailable; use the same choice to retry.")
            return
        choice = result.data
        battle = None
        try:
            battle = BattleSession(self.caller)
            battle.start_adventure_encounter(
                species=choice.species,
                level=choice.level,
                encounter_kind=choice.encounter_kind,
                opponent_name=choice.opponent_name,
                adventure_session_id=getattr(result.session, "pk", getattr(result.session, "id", 0)),
                route_key=choice.key,
                outcome_key=choice.outcome_key or choice.key,
            )
        except Exception:
            battle = battle or getattr(getattr(self.caller, "ndb", None), "battle_instance", None)
            if battle is not None:
                battle._startup_failed = True
                try:
                    battle.end()
                except Exception:
                    self.caller.msg("The encounter could not start and cleanup is pending. Use +adventure/retry, then choose the route again.")
                    return
            self.caller.msg("The encounter could not start; use the same choice to retry.")

    def _retry(self) -> None:
        """Finish retained terminal battles, then replay saved Adventure results."""

        from pokemon.battle.battleinstance import BattleSession

        try:
            battle = BattleSession.ensure_for_player(self.caller)
            if battle is not None and getattr(battle, "_startup_failed", False):
                battle.end()
                self.caller.msg("The incomplete encounter was cleaned up. Choose the same route to retry.")
            elif battle is not None and getattr(battle, "_adventure_result", None):
                battle._handle_battle_result(None)
                battle.end()
            message = retry_encounter_results(self.caller)
        except Exception:
            message = "The encounter result could not be saved. Use +adventure/retry again later."
        self.caller.msg(message)

    def _claim(self) -> None:
        """Retry this character's unpaid rewards without requiring an active run."""

        from .progress import claim_completed_rewards

        try:
            message = claim_completed_rewards(self.caller)
        except Exception:
            message = "Adventure rewards are unavailable. Use +adventure/claim again later."
        self.caller.msg(message)

    def _leave(self) -> None:
        result = leave_session(self.caller)
        if result.ok or result.session is None:
            detach_movement_cmdset(self.caller)
        self.caller.msg(result.message)


def _usage() -> str:
    return (
        "Usage: +adventure/board | +adventure/info <adventure> | "
        "+adventure/take <adventure> | +adventure/status | +adventure/look | "
        "+adventure/objectives | +adventure/search | "
        "+adventure/choose <route> | +adventure/retry | +adventure/claim | +adventure/leave"
    )
