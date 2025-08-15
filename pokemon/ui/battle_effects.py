"""Effects panel renderer (ANSI-safe, width-aware).

Renders a single-column panel showing:
- Field/global timers (Weather, Terrain, Rooms, etc)
- Side A/B timers & hazards (Screens, Tailwind, Hazards)
- On-field Pokémon: name/meta chips, HP line, stages, timed effects, item/ability

This reuses helpers from battle_render.py to keep visuals consistent.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Tuple

# Reuse existing ANSI-safe helpers and theme
from pokemon.ui.battle_render import (
    THEME,
    ansi_len,
    rpad,
    fmt_hp_line,
    status_badge,
    gender_chip,
    display_name,
)
from pokemon.ui.box_utils import render_box


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def _timer_chip(name: str, left: Optional[int] = None, total: Optional[int] = None) -> str:
    """Return a compact timer chip like "⏱ Rain 4/5" or "⏱ Taunt 2t" (when total unknown).
    Skips if no name or no time info."""
    if not name:
        return ""
    if left is None and total is None:
        return name
    if total is not None and left is not None:
        return f"⏱ {name} {left}/{total}"
    if left is not None:
        return f"⏱ {name} {left}t"
    return f"⏱ {name}"


def _wrap_tokens(tokens: List[str], width: int) -> List[str]:
    """Wrap space-separated tokens within width (ANSI-safe)."""
    lines: List[str] = []
    cur = ""
    for tok in tokens:
        tok = tok.strip()
        if not tok:
            continue
        if not cur:
            cur = tok
            continue
        if ansi_len(cur) + 2 + ansi_len(tok) <= width:
            cur = f"{cur}  {tok}"
        else:
            lines.append(cur)
            cur = tok
    if cur:
        lines.append(cur)
    return lines


def _stages_line(boosts: Dict[str, int]) -> str:
    """Return condensed stat stage string with colors, or '—' if all zero."""
    if not boosts:
        return "—"
    order = ("atk", "def", "spa", "spd", "spe", "accuracy", "evasion")
    name_map = {
        "atk": "Atk",
        "def": "Def",
        "spa": "SpA",
        "spd": "SpD",
        "spe": "Spe",
        "accuracy": "Acc",
        "evasion": "Eva",
    }
    parts: List[str] = []
    for k in order:
        v = int(boosts.get(k, 0) or 0)
        if v == 0:
            continue
        col = THEME["ok"] if v > 0 else THEME["bad"]
        sign = "+" if v > 0 else ""
        parts.append(f"{col}{name_map[k]}{sign}{v}|n")
    return " ".join(parts) if parts else "—"


def _hazards_line(h: Dict[str, int] | None) -> str:
    """Compact hazards string for a side."""
    if not h:
        return "None"
    parts: List[str] = []
    if h.get("sr") or h.get("stealthrock"):
        parts.append("SR")
    sp = h.get("spikes", 0)
    if sp:
        parts.append(f"Spikes×{sp}")
    ts = h.get("tspikes", h.get("toxicspikes", 0))
    if ts:
        parts.append(f"TSpikes×{ts}")
    if h.get("web") or h.get("stickyweb"):
        parts.append("Web")
    return " • ".join(parts) if parts else "None"


def _reveal(name: Optional[str], revealed: bool, is_self: bool) -> str:
    """Return revealed name, '?' if hidden and not self, or '—' if None."""
    if name:
        if revealed or is_self:
            return name
        return "?"
    return "—"


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------


class EffectsAdapter:
    """Lightweight adapter around a battle session/state so the renderer can be robust
    against engine differences. Only the attributes used below are expected."""

    def __init__(self, session, viewer):
        self.session = session
        self.viewer = viewer
        self.state = getattr(session, "state", session)

    def title(self) -> str:
        a = getattr(self.session, "captainA", None)
        b = getattr(self.session, "captainB", None)
        enc = (getattr(self.state, "encounter_kind", "") or "").lower()
        left = getattr(a, "name", "?")
        if enc == "wild":
            mon = getattr(getattr(b, "active_pokemon", None), "name", "Wild Pokémon")
            right = f"Wild {mon}"
        else:
            right = getattr(b, "name", "?")
        return f"{THEME['title']}{left}|n {THEME['vs']} {THEME['title']}{right}|n"

    def turn(self) -> int:
        return int(getattr(self.state, "round", getattr(self.state, "turn", 0)) or 0)

    def viewer_role(self) -> str:
        c = self.viewer
        if not c:
            return "W"
        if c in getattr(self.session, "teamA", []) or c == getattr(self.session, "captainA", None):
            return "A"
        if c in getattr(self.session, "teamB", []) or c == getattr(self.session, "captainB", None):
            return "B"
        return "W"

    def monA(self):
        return getattr(getattr(self.session, "captainA", None), "active_pokemon", None)

    def monB(self):
        return getattr(getattr(self.session, "captainB", None), "active_pokemon", None)

    # ---- Field/global ----
    def field_timers(self) -> List[Tuple[str, int | None, int | None]]:
        out: List[Tuple[str, int | None, int | None]] = []
        # Weather
        wname = getattr(self.state, "weather", getattr(self.state, "roomweather", None))
        if wname:
            out.append(
                (
                    "Rain" if str(wname).lower() == "rain" else str(wname).title(),
                    getattr(self.state, "weather_left", None),
                    getattr(self.state, "weather_total", None),
                )
            )
        # Terrain
        tname = getattr(self.state, "terrain", None)
        if tname:
            out.append(
                (
                    str(tname).title(),
                    getattr(self.state, "terrain_left", None),
                    getattr(self.state, "terrain_total", None),
                )
            )
        # Rooms / Gravity (common flags)
        for key, label in (
            ("trick_room", "Trick Room"),
            ("gravity", "Gravity"),
            ("magic_room", "Magic Room"),
            ("wonder_room", "Wonder Room"),
        ):
            if getattr(self.state, key, None):
                out.append(
                    (
                        label,
                        getattr(self.state, f"{key}_left", None),
                        getattr(self.state, f"{key}_total", None),
                    )
                )
        return out

    # ---- Side timers & hazards ----
    def side_data(self, side: str) -> Tuple[List[Tuple[str, int | None, int | None]], Dict[str, int]]:
        s = getattr(self.state, f"side_{side.lower()}", None)
        if not s:
            return ([], {})
        timers: List[Tuple[str, int | None, int | None]] = []
        for key, label in (
            ("light_screen", "Light Screen"),
            ("reflect", "Reflect"),
            ("aurora_veil", "Aurora Veil"),
            ("safeguard", "Safeguard"),
            ("mist", "Mist"),
            ("tailwind", "Tailwind"),
        ):
            if getattr(s, key, None):
                timers.append(
                    (
                        label,
                        getattr(s, f"{key}_left", None),
                        getattr(s, f"{key}_total", None),
                    )
                )
        haz = getattr(s, "hazards", {}) or {}
        return (timers, haz)


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def render_effects_panel(
    session,
    viewer,
    *,
    total_width: int = 78,
    brief: bool = False,
    focus: Optional[str] = None,
) -> str:
    """Render the full effects panel. `focus` can be "me" or "opp" to limit Pokémon section."""
    ad = EffectsAdapter(session, viewer)

    inner = max(40, total_width - 2)

    title = "Active Battle States & Effects"

    header = f" {ad.title()}".ljust(inner - 14) + f" Turn: {ad.turn()}".rjust(14)
    rows: List[str] = [rpad(header, inner)]

    # --- Field ---
    rows.append(rpad("─ Field " + ("─" * max(0, inner - 8)), inner))
    field_tokens = [_timer_chip(*t) for t in ad.field_timers() if _timer_chip(*t)]
    if field_tokens:
        for line in _wrap_tokens(field_tokens, inner):
            rows.append(rpad(line, inner))
    else:
        rows.append(rpad("None", inner))

    # --- Sides ---
    for side_label, side_key in (("Side A", "A"), ("Side B", "B")):
        rows.append(rpad(f"─ {side_label} " + ("─" * max(0, inner - len(side_label) - 3)), inner))
        timers, hazards = ad.side_data(side_key)
        side_tokens = [_timer_chip(*t) for t in timers if _timer_chip(*t)]
        haz_line = f"Hazards: {_hazards_line(hazards)}"
        if side_tokens:
            for line in _wrap_tokens(side_tokens, inner):
                rows.append(rpad(line, inner))
        else:
            rows.append(rpad("—", inner))
        rows.append(rpad(haz_line, inner))

    # --- Pokémon ---
    if not brief:
        rows.append(rpad("─ On-Field Pokémon " + ("─" * max(0, inner - 20)), inner))
        role = ad.viewer_role()
        for mon, self_side in (
            (ad.monA(), role in ("A", "W") and focus != "opp" or focus == "me" and role == "A"),
            (ad.monB(), role in ("B", "W") and focus != "me" or focus == "opp" and role in ("A", "B")),
        ):
            if not mon:
                continue
            # Line 1: Name + chips
            name_raw = display_name(mon)
            name_color = f"{THEME['name']}{name_raw}|n"
            chips = "  ".join(
                [p for p in (gender_chip(mon), f"Lv{getattr(mon,'level','?')}", status_badge(mon)) if p]
            )
            line1 = name_color if ansi_len(f"{name_color}  {chips}") > inner else f"{name_color}  {chips}"
            rows.append(rpad(line1, inner))
            # HP
            rows.append(rpad(fmt_hp_line(mon, inner, show_abs=self_side if role != "W" else self_side), inner))
            # Item/Ability with reveal
            is_self = (role == "A" and mon is ad.monA()) or (role == "B" and mon is ad.monB())
            item = _reveal(getattr(mon, "item_name", None), bool(getattr(mon, "item_revealed", False)), is_self)
            abil = _reveal(
                getattr(mon, "ability_name", None), bool(getattr(mon, "ability_revealed", False)), is_self
            )
            rows.append(rpad(f"Item: {item}   Ability: {abil}", inner))
            # Stages
            rows.append(rpad(f"Stages: {_stages_line(getattr(mon,'boosts',{}))}", inner))
            # Effects (volatiles with optional timers)
            effects = []
            for eff in getattr(mon, "effects", []) or []:
                key = str(eff.get("key") or eff.get("name") or "").strip()
                if not key:
                    continue
                left = eff.get("turns_left")
                total = eff.get("total")
                extra = eff.get("source") or eff.get("move")
                label = key.replace("_", " ").title()
                if extra:
                    label = f"{label}({extra})"
                effects.append(_timer_chip(label, left, total))
            if effects:
                for line in _wrap_tokens(effects, inner):
                    rows.append(rpad(f"Effects: {line}", inner))
            else:
                rows.append(rpad("Effects: —", inner))
    return render_box(title, inner, rows)
