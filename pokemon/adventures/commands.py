"""Player command for starting and controlling Adventures."""

from __future__ import annotations

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
from .renderer import render_objectives, render_session, render_template_info
from .sessions import (
    choose_session_route,
    get_current_session_for_player,
    leave_session,
    search_session,
    start_session,
)
from .templates import get_template, list_templates


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
      +adventure/list
      +adventure/info <adventure>
      +adventure/start <adventure>
      +adventure/look
      +adventure/objectives
      +adventure/search
      +adventure/choose <wild|trainer>
      +adventure/leave

    Examples:
      +adventure/list
      +adventure/start alpha_meadow
      +adventure/search

    Notes:
      Adventures are solo-first authored missions started from Adventure Hall.
    """

    key = "+adventure"
    aliases = ["+adv"]
    locks = "cmd:all()"
    help_category = "Adventure"

    def parse(self):
        _parse_slash_switches(self)

    def func(self):
        action, arg = self._action_and_arg()
        if action == "list":
            self._list()
        elif action == "info":
            self._info(arg)
        elif action == "start":
            self._start(arg)
        elif action == "look":
            self._look()
        elif action == "objectives":
            self._objectives()
        elif action == "search":
            self._search()
        elif action == "choose":
            self._choose(arg)
        elif action == "leave":
            self._leave()
        else:
            self.caller.msg(_usage())

    def _action_and_arg(self) -> tuple[str, str]:
        switches = getattr(self, "switches", set())
        for action in ("list", "info", "start", "look", "objectives", "search", "choose", "leave"):
            if action in switches:
                return action, (self.args or "").strip()
        raw = (self.args or "").strip()
        if not raw:
            return "help", ""
        first, _, rest = raw.partition(" ")
        first = first.lower()
        if first in {"list", "info", "start", "look", "objectives", "search", "choose", "leave"}:
            return first, rest.strip()
        return "help", raw

    def _list(self) -> None:
        templates = list_templates()
        if not templates:
            self.caller.msg("No adventures are available.")
            return
        lines = ["Available adventures:"]
        for template in templates:
            lines.append(f"  {template.key} - {template.name} ({template.category})")
        self.caller.msg("\n".join(lines))

    def _info(self, arg: str) -> None:
        template = get_template(arg)
        if template is None:
            self.caller.msg("Usage: +adventure/info <adventure>")
            return
        self.caller.msg(render_template_info(template))

    def _start(self, arg: str) -> None:
        if not arg:
            self.caller.msg("Usage: +adventure/start <adventure>")
            return
        result = start_session(self.caller, arg)
        self.caller.msg(result.message)
        if result.ok and result.session is not None:
            attach_movement_cmdset(self.caller)
            self.caller.msg(render_session(result.session))

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

        result = choose_session_route(self.caller, arg)
        self.caller.msg(result.message)
        if not result.ok or result.session is None or result.data is None:
            return
        if BattleSession is None:
            self.caller.msg("The battle system is unavailable; use the same choice to retry.")
            return
        choice = result.data
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
            self.caller.msg("The encounter could not start; use the same choice to retry.")

    def _leave(self) -> None:
        result = leave_session(self.caller)
        detach_movement_cmdset(self.caller)
        self.caller.msg(result.message)


def _usage() -> str:
    return (
        "Usage: +adventure/list | +adventure/info <adventure> | "
        "+adventure/start <adventure> | +adventure/look | "
        "+adventure/objectives | +adventure/search | "
        "+adventure/choose <route> | +adventure/leave"
    )
