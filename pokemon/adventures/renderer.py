"""Text renderers for Adventure sessions."""

from __future__ import annotations

from typing import Any

from .constants import STATE_COMPLETED
from .templates import AdventureTemplate, get_template


def render_for_room(room: Any, looker: Any) -> str | None:
    """Return Adventure room text for ``looker`` or ``None`` for normal room look."""

    try:
        from .sessions import get_active_session_for_room

        session = get_active_session_for_room(room, looker)
    except Exception:
        return None
    if session is None:
        return None
    return render_session(session)


def render_session(session: Any) -> str:
    """Render the current virtual Adventure location."""

    template = get_template(getattr(session, "template_key", ""))
    if template is None:
        return "Adventure data is missing."
    node = template.nodes.get(getattr(session, "current_node", ""))
    if node is None:
        return "Adventure location data is missing."

    lines = [
        template.name,
        "-" * min(72, max(24, len(template.name))),
        node.name,
        "",
        node.description,
        "",
    ]
    map_text = render_map(template, session)
    if map_text:
        lines.extend(["Map:", map_text, ""])
    exits = ", ".join(sorted(node.exits)) or "none"
    actions = _actions_for_node(node, session)
    lines.append(f"Exits: {exits}")
    lines.append(f"Actions: {actions}")
    lines.extend(["", "Objectives:", render_objectives(session)])
    if getattr(session, "state", None) == STATE_COMPLETED:
        lines.extend(["", "Adventure complete. Use +adventure/leave to return."])
    return "\n".join(lines)


def render_objectives(session: Any) -> str:
    """Render objective progress for an Adventure session."""

    template = get_template(getattr(session, "template_key", ""))
    if template is None:
        return "  Adventure data is missing."
    progress = dict(getattr(session, "objective_progress", None) or {})
    lines = []
    for objective in template.objectives:
        mark = "x" if int(progress.get(objective.key, 0) or 0) >= 1 else " "
        lines.append(f"  [{mark}] {objective.description}")
    return "\n".join(lines)


def render_template_info(template: AdventureTemplate) -> str:
    """Render player-facing summary text for a template."""

    lines = [
        template.name,
        "-" * min(72, max(24, len(template.name))),
        template.description,
        "",
        f"Category: {template.category}",
        f"Region: {template.region}",
        f"Biome: {template.biome}",
        f"Recommended level: {template.recommended_level}",
        f"Party size: solo, max {template.max_party_size}",
        "",
        "Objectives:",
    ]
    lines.extend(f"  - {objective.description}" for objective in template.objectives)
    return "\n".join(lines)


def render_map(template: AdventureTemplate, session: Any) -> str:
    """Render a compact ASCII node map."""

    coords = {
        key: node.coordinates
        for key, node in template.nodes.items()
        if node.coordinates is not None
    }
    if not coords:
        return ""
    xs = [coord[0] for coord in coords.values() if coord is not None]
    ys = [coord[1] for coord in coords.values() if coord is not None]
    if not xs or not ys:
        return ""
    current = getattr(session, "current_node", "")
    visited = set(getattr(session, "visited_nodes", None) or [])
    rows = []
    for y in range(max(ys), min(ys) - 1, -1):
        cells = []
        for x in range(min(xs), max(xs) + 1):
            key = next((node_key for node_key, coord in coords.items() if coord == (x, y)), None)
            if key is None:
                cells.append(" ")
            elif key == current:
                cells.append("@")
            elif key == template.start_node:
                cells.append("E")
            elif key in visited:
                cells.append(".")
            else:
                cells.append("?")
        rows.append("  " + " ".join(cells).rstrip())
    return "\n".join(rows)


def _actions_for_node(node: Any, session: Any) -> str:
    actions = ["objectives", "leave"]
    if getattr(node, "search_text", "") or getattr(node, "search_objective", ""):
        actions.insert(0, "search")
    if getattr(session, "state", None) == STATE_COMPLETED:
        return "leave"
    return ", ".join(actions)
