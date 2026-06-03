"""Staff-only AI debug trace viewer for active battles."""

from __future__ import annotations

from typing import Any

try:
    from evennia import Command as _EvenniaCommand
except Exception:  # pragma: no cover - optional in lightweight tests
    _EvenniaCommand = None

from pokemon.battle.battleinstance import BattleSession


if _EvenniaCommand is None:  # pragma: no cover - direct test/Django imports
    class Command:  # type: ignore[no-redef]
        """Lightweight command base used when Evennia is not configured."""

        pass
else:
    Command = _EvenniaCommand


MAX_CONSIDERED_ACTIONS = 6
LINE_WIDTH = 78


class CmdAIDebugTrace(Command):
    """Show the most recent internal AI decision trace for the current battle.

    Usage:
      +aidebug
      +aidebug/last
    """

    key = "+aidebug"
    aliases = ["+aidebug/last", "@aidebug", "@aidebug/last"]
    locks = "cmd:perm(Wizards)"
    help_category = "Admin"

    def func(self):
        inst, message = _current_battle_for_caller(self.caller)
        if not inst:
            self.caller.msg(message or "No active battle found for you or this room.")
            return

        trace = _latest_ai_trace(inst)
        if trace is None:
            battle_id = getattr(inst, "battle_id", None)
            suffix = f" for battle #{battle_id}" if battle_id is not None else ""
            self.caller.msg(f"No AI debug trace recorded yet{suffix}.")
            return

        self.caller.msg(render_ai_debug_trace(trace, battle_id=getattr(inst, "battle_id", None)))


def _current_battle_for_caller(caller) -> tuple[Any | None, str | None]:
    ensure_for_player = getattr(BattleSession, "ensure_for_player", None)
    if callable(ensure_for_player):
        try:
            inst = ensure_for_player(caller)
            if inst:
                return inst, None
        except Exception:
            pass

    inst = getattr(getattr(caller, "ndb", None), "battle_instance", None)
    if inst:
        return inst, None

    room = getattr(caller, "location", None)
    battle_map = getattr(getattr(room, "ndb", None), "battle_instances", None)
    if isinstance(battle_map, dict):
        live = [inst for inst in battle_map.values() if inst is not None]
        if len(live) == 1:
            return live[0], None
        if len(live) > 1:
            return None, "Multiple battles are active here. Join the battle you want to inspect first."

    return None, "No active battle found for you or this room."


def _latest_ai_trace(inst) -> Any | None:
    for source in _trace_sources(inst):
        trace = getattr(source, "last_ai_debug_trace", None)
        if trace is not None:
            return trace
        traces = getattr(source, "ai_debug_traces", None)
        if isinstance(traces, list):
            for candidate in reversed(traces):
                if candidate is not None:
                    return candidate
    return None


def _trace_sources(inst) -> list[Any]:
    sources: list[Any] = [inst]
    for attr in ("battle", "logic"):
        value = getattr(inst, attr, None)
        if value is not None:
            sources.append(value)
            battle = getattr(value, "battle", None)
            if battle is not None:
                sources.append(battle)
    battle = getattr(getattr(inst, "logic", None), "battle", None)
    if battle is not None:
        sources.append(battle)
    return sources


def render_ai_debug_trace(trace, *, battle_id: Any | None = None) -> str:
    requested = _text(_field(trace, "requested_profile_key"), "none")
    resolved = _text(
        _field(trace, "resolved_profile_key") or _field(trace, "profile_key"),
        "unknown",
    )
    chosen = _text(_field(trace, "chosen_action"), "none")
    intent = _text(_field(trace, "chosen_intent"), "none")
    actor = _text(_field(trace, "actor_name"), "unknown")
    target = _text(_field(trace, "target_name"), "unknown")

    title = "AI Debug Trace"
    if battle_id is not None:
        title = f"{title} #{battle_id}"

    lines = [
        title,
        f"Profile: requested=`{requested}`, resolved=`{resolved}`",
        f"Actor: {actor}",
        f"Target: {target}",
        f"Intent: {intent}",
        f"Chosen Action: {chosen}",
        "",
        "Considered Moves:",
    ]

    entries = _score_entries(trace)
    if entries:
        shown = entries[:MAX_CONSIDERED_ACTIONS]
        for entry in shown:
            lines.append(_format_score_entry(entry))
        remaining = len(entries) - len(shown)
        if remaining > 0:
            lines.append(f"  ... {remaining} more not shown.")
    else:
        actions = [_text(action, "unknown") for action in _field(trace, "legal_actions_considered", []) or []]
        for action in actions[:MAX_CONSIDERED_ACTIONS]:
            lines.append(_clip(f"  {action}: score unavailable", LINE_WIDTH))
        if not actions:
            lines.append("  none recorded")

    lines.extend(
        [
            "",
            "Notes:",
            "Weighted choice among top candidates.",
            "Debug output is staff-only.",
        ]
    )
    return "\n".join(lines)


def _score_entries(trace) -> list[dict[str, Any]]:
    scores = _field(trace, "scores", []) or []
    entries = []
    for index, score in enumerate(scores):
        action = _field(score, "action")
        value = _field(score, "score")
        reasons = _reasons(_field(score, "reasons", ()) or ())
        entries.append(
            {
                "action": _text(action, "unknown"),
                "score": _number(value),
                "reasons": tuple(_text(reason, "unknown") for reason in reasons),
                "index": index,
            }
        )
    entries.sort(key=lambda entry: (entry["score"] is not None, entry["score"] or 0.0), reverse=True)
    return entries


def _format_score_entry(entry: dict[str, Any]) -> str:
    score = "?" if entry["score"] is None else f"{entry['score']:.1f}"
    reasons = ", ".join(reason for reason in entry["reasons"] if reason)
    suffix = f" - {reasons}" if reasons else ""
    return _clip(f"  {entry['action']}: {score}{suffix}", LINE_WIDTH)


def _field(obj, name: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _text(value: Any, default: str) -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text or default


def _number(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _reasons(value: Any) -> tuple[Any, ...]:
    if isinstance(value, str):
        return (value,)
    try:
        return tuple(value)
    except TypeError:
        return (value,)


def _clip(text: str, width: int) -> str:
    if len(text) <= width:
        return text
    if width <= 3:
        return text[:width]
    return text[: width - 3] + "..."


__all__ = ["CmdAIDebugTrace", "render_ai_debug_trace"]
