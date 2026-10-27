"""Compact ANSI battle presentation with stable field positions and ownership."""

from __future__ import annotations

import re
import textwrap
from dataclasses import dataclass

from utils.battle_display import strip_ansi


def screen_reader(viewer) -> bool:
    """Use the same accessible mode as room and party presentation."""
    return getattr(getattr(viewer, "db", None), "ui_mode", None) in {"sr", "screenreader"}


def battle_width(width) -> int:
    """Keep compact output readable on narrow and ordinary terminal windows."""
    try:
        return max(24, min(int(width or 78), 100))
    except (TypeError, ValueError):
        return 78


def same_character(left, right) -> bool:
    """Match a controller without treating two missing controllers as equal."""
    if left is None or right is None:
        return False
    if left is right:
        return True
    identifier = getattr(left, "pk", None)
    return identifier is not None and str(identifier) == str(getattr(right, "pk", None))


def uses_compact(viewer) -> bool:
    """Resolve presentation preference consistently for prompts and messages."""
    from pokemon.ui.battle_render import normalize_battle_ui_style

    return (
        screen_reader(viewer)
        or normalize_battle_ui_style(getattr(getattr(viewer, "db", None), "battle_ui_style", None))
        == "compact"
    )


class BattleText:
    """Wrap visible text safely, keeping ANSI markup out of width calculations."""

    def __init__(self, width=78, accessible=False):
        """Capture terminal width and whether visual decorations are permitted."""
        self.width = battle_width(width)
        self.accessible = accessible
        self.lines = []

    def add(self, text=""):
        """Keep short colored rows intact and wrap longer rows without truncation."""
        for line in str(text).split("\n"):
            plain = strip_ansi(line)
            if self.accessible:
                line = plain
            if len(plain) <= self.width:
                self.lines.append(line)
            else:
                # Wrapped continuations must not leave an ANSI sequence open.
                chunks = textwrap.wrap(
                    plain, self.width, break_long_words=True, break_on_hyphens=False
                ) or [""]
                self.lines.extend(
                    chunk if self.accessible else chunk.replace("|", "||") for chunk in chunks
                )

    def rule(self):
        """Separate visual sections without reading punctuation aloud."""
        if not self.accessible:
            self.add("|x" + "-" * self.width + "|n")

    def render(self):
        """Return complete terminal text, stripping color in accessible mode."""
        return "\n".join(self.lines)


@dataclass
class FieldCombatant:
    """One physical field cell and the trainer controlling its occupant."""

    position: str
    pokemon: object
    controller: object
    roster: list


class CompactBattleRenderer:
    """Present the real field without copying hidden opponent information."""

    def __init__(self, state, viewer, width=78, waiting_on=None, ascii_symbols=False):
        """Bind one recipient to the authoritative field and their preferences."""
        self.state = state
        self.viewer = viewer
        self.session = getattr(state, "session", None)
        self.side = state.get_side(viewer)
        self.waiting_on = waiting_on
        self.ascii = ascii_symbols
        self.text = BattleText(width, screen_reader(viewer))
        self.entries = self._combatants()

    def _combatants(self):
        """Prefer authoritative physical cells, including doubles and Multi."""
        positions = (
            getattr(getattr(getattr(self.session, "data", None), "turndata", None), "positions", {})
            or {}
        )
        participants = list(
            getattr(getattr(self.session, "battle", None), "participants", []) or []
        )
        entries = []
        for label, cell in sorted(positions.items()):
            mon = getattr(cell, "pokemon", None)
            part = next(
                (
                    part
                    for part in participants
                    if getattr(part, "field_position", None) == label
                    or any(
                        active is mon for active in getattr(part, "active", []) if mon is not None
                    )
                ),
                None,
            )
            trainer = getattr(part, "player", None) or self.state.get_trainer(label[:1])
            roster = list(getattr(part, "pokemons", None) or getattr(trainer, "team", []) or [])
            entries.append(FieldCombatant(label, mon, trainer, roster))
        if not entries:
            for side in ("A", "B"):
                trainer = self.state.get_trainer(side)
                if trainer is not None:
                    entries.append(
                        FieldCombatant(
                            side + "1",
                            getattr(trainer, "active_pokemon", None),
                            trainer,
                            list(getattr(trainer, "team", []) or []),
                        )
                    )
        return sorted(
            entries,
            key=lambda entry: (
                entry.position.startswith(self.side) if self.side else False,
                entry.position,
            ),
        )

    @staticmethod
    def _fusion(mon, trainer):
        """Identify a Fusion by native owned ID, never by its species or nickname."""
        if mon is None:
            return False
        if getattr(mon, "_pf2_active_fusion", False):
            return True
        fusion_id = getattr(getattr(trainer, "db", None), "fusion_id", None)
        identifier = str(getattr(mon, "model_id", "") or "")
        if identifier.startswith("owned:"):
            identifier = identifier[len("owned:") :]
        return bool(fusion_id and identifier == str(fusion_id))

    @staticmethod
    def _status(mon):
        """Read full status names; fainting takes precedence over conditions."""
        if getattr(mon, "hp", 0) <= 0 or getattr(mon, "is_fainted", False):
            return "FAINTED"
        value = getattr(mon, "status_name", None) or getattr(mon, "status", "")
        value = str(getattr(value, "value", value) or "").strip().lower()
        return {
            "": "",
            "0": "",
            "ok": "",
            "nrm": "",
            "norm": "",
            "par": "PARALYZED",
            "brn": "BURNED",
            "psn": "POISONED",
            "tox": "BADLY POISONED",
            "slp": "ASLEEP",
            "frz": "FROZEN",
        }.get(value, value.upper())

    @staticmethod
    def _effects(mon):
        """Summarize public conditions and stat stages, excluding hidden state."""
        volatile = getattr(mon, "volatiles", {}) or {}
        labels = {
            "confusion": "Confused",
            "taunt": "Taunted",
            "encore": "Encore",
            "substitute": "Substitute",
            "leechseed": "Leech Seed",
            "recharge": "Recharging",
        }
        effects = [label for key, label in labels.items() if key in volatile]
        boosts = getattr(mon, "boosts", {}) or {}
        for names, label in (
            (("atk", "attack"), "Attack"),
            (("def", "defense"), "Defense"),
            (("spa", "special_attack"), "Sp. Atk"),
            (("spd", "special_defense"), "Sp. Def"),
            (("spe", "speed"), "Speed"),
            (("accuracy",), "Accuracy"),
            (("evasion",), "Evasion"),
        ):
            value = next((boosts[name] for name in names if name in boosts), 0)
            if value:
                effects.append(f"{label} {int(value):+d}")
        return effects

    def _owns(self, entry):
        """Only the exact controller receives absolute HP and private prompts."""
        return same_character(entry.controller, self.viewer)

    def _phase(self):
        """Distinguish observer, waiting, queued and ready states."""
        if getattr(getattr(self.session, "battle", None), "battle_over", False):
            return "BATTLE OVER"
        if not self.side:
            return "WATCHING"
        if (getattr(self.session, "turn_state", None) or {}).get("error"):
            return "RETRY REQUIRED"
        if self.waiting_on:
            return "WAITING"
        owned = [
            entry
            for entry in self.entries
            if self._owns(entry)
            and entry.pokemon is not None
            and getattr(entry.pokemon, "hp", 0) > 0
        ]
        if not owned:
            return "REPLACEMENT NEEDED"
        declarations = getattr(getattr(self.session, "state", None), "declare", {}) or {}
        if owned and all(entry.position in declarations for entry in owned):
            return "ACTION QUEUED"
        return "YOUR MOVE"

    def _heading(self, left, right):
        """Align a right label when space allows, otherwise use a separate row."""
        gap = self.text.width - len(strip_ansi(left)) - len(strip_ansi(right))
        self.text.add(left + " " * gap + right if gap >= 2 else left + "\n" + right)

    def _card(self, entry):
        """Render a combatant's public identity, condition, HP, and effects."""
        from pokemon.ui.battle_render import display_name

        own = self._owns(entry)
        friendly = self.side and entry.position.startswith(self.side)
        role = (
            "YOU"
            if own
            else "ALLY" if friendly else "FOE" if self.side else "TEAM " + entry.position[:1]
        )
        color = "|c" if friendly else "|r" if self.side else "|w"
        mon = entry.pokemon
        if mon is None:
            self.text.add(f"{color}{role} {entry.position}|n  Empty field position")
            return
        name = strip_ansi(display_name(mon))
        wild = (
            entry.position.startswith("B") and getattr(self.state, "encounter_kind", "") == "wild"
        )
        fusion = self._fusion(mon, entry.controller)
        trainer_name = getattr(entry.controller, "name", None) or getattr(
            entry.controller, "key", "Trainer"
        )
        if fusion:
            from pokemon.battle.appearance import BattleAppearance

            disguise = BattleAppearance.illusion(mon)
            species = disguise["species"] if disguise else getattr(mon, "species", name)
            name = f"{trainer_name} ({species})"
        elif wild:
            name = "Wild " + name
        left = f"{color}{role} {entry.position}|n  |w{name}|n"
        self._heading(left, f"Lv {getattr(mon, 'level', '?')}")
        if not own and not wild:
            self.text.add(f"Trainer: {trainer_name}")
        badges = []
        if fusion:
            badges.append("|c[YOU / FUSION]|n" if own else "|c[FUSION]|n")
        status = self._status(mon)
        if status:
            badges.append(f"{'|r' if status == 'FAINTED' else '|y'}[{status}]|n")
        declarations = getattr(getattr(self.session, "state", None), "declare", {}) or {}
        if own and entry.position in declarations:
            badges.append("|c[QUEUED]|n")
        for attr, label in (("terastallized", "Tera"), ("mega_evolved", "Mega")):
            value = getattr(mon, attr, None)
            if value:
                badges.append(
                    f"|c[{label} {value if attr == 'terastallized' else getattr(mon, 'species', '')}]|n"
                )
        if badges:
            self.text.add("  ".join(badges))
        hp, maximum = max(0, int(getattr(mon, "hp", 0))), max(0, int(getattr(mon, "max_hp", 0)))
        percent = round(100 * hp / maximum) if maximum else 0
        numbers = f"{hp}/{maximum}" if own else f"{percent}%"
        if self.text.accessible:
            self.text.add("HP: " + numbers)
        else:
            filled = max(0, min(10, round(percent / 10)))
            if hp > 0 and maximum > 0:
                filled = max(1, filled)
            color = "|g" if percent > 50 else "|y" if percent > 20 else "|r"
            full, empty = ("#", "-") if self.ascii else ("█", "░")
            self.text.add(f"HP [{color}{full * filled}|n|x{empty * (10 - filled)}|n] {numbers}")
        effects = self._effects(mon)
        if effects:
            self.text.add("Effects: " + " / ".join(effects))

    def _teams(self):
        """Show complete owned rosters, including an extra trainer Fusion."""
        entry = next((entry for entry in self.entries if self._owns(entry)), None)
        if entry is None:
            return
        normal = [mon for mon in entry.roster if mon and not self._fusion(mon, entry.controller)]
        fused = [mon for mon in entry.roster if mon and self._fusion(mon, entry.controller)]
        ready = sum(
            getattr(mon, "hp", 0) > 0 and not getattr(mon, "is_fainted", False) for mon in normal
        )
        text = f"Team: {ready}/{len(normal)} ready"
        if fused:
            text += (
                " + Fusion"
                if any(
                    getattr(mon, "hp", 0) > 0 and not getattr(mon, "is_fainted", False)
                    for mon in fused
                )
                else " + Fusion fainted"
            )
        self.text.add(text)

    def render(self):
        """Build the compact HUD and actual previous-turn messages."""
        from pokemon.ui.battle_render import _battle_turn

        self.text.add("|cPOKEMON FUSION 2|n")
        self._heading(f"|wTURN {_battle_turn(self.state)}|n", f"|y{self._phase()}|n")
        self.text.rule()
        for index, entry in enumerate(self.entries):
            if index:
                self.text.add()
            self._card(entry)
        self._teams()
        field = []
        for label, value in (
            ("Weather", getattr(self.state, "weather", "")),
            ("Field", getattr(self.state, "field", "")),
        ):
            if str(value or "").lower() not in {"", "-", "clear", "neutral", "none"}:
                field.append(f"{label}: {value}")
        if field:
            self.text.add(" / ".join(field))
        events = getattr(self.session, "_battle_ui_last_events", None)
        if events:
            self.text.rule()
            self.text.add("|WLAST TURN|n")
            for message in events:
                self.text.add(BattleEventPresentation.format(message))
        self.text.rule()
        owned = [
            entry
            for entry in self.entries
            if self._owns(entry)
            and entry.pokemon is not None
            and getattr(entry.pokemon, "hp", 0) > 0
        ]
        declarations = getattr(getattr(self.session, "state", None), "declare", {}) or {}
        pending = [entry for entry in owned if entry.position not in declarations]
        if len(pending) == 1 and self._phase() == "YOUR MOVE":
            moves = list(getattr(pending[0].pokemon, "moves", []) or [])[:4]
            if moves:
                from pokemon.ui.move_gui import render_compact_moves

                if len(owned) > 1:
                    self.text.add(f"Moves for {pending[0].position}:")
                unavailable = {
                    index: "DISABLED"
                    for index, move in enumerate(moves)
                    if getattr(move, "disabled", False)
                }
                self.text.add(
                    render_compact_moves(
                        moves,
                        total_width=self.text.width,
                        unavailable=unavailable,
                        accessible=self.text.accessible,
                        hints=False,
                    )
                )
                target = next(
                    (
                        entry.position
                        for entry in self.entries
                        if not entry.position.startswith(self.side) and entry.pokemon is not None
                    ),
                    None,
                )
                command = "+attack " + pending[0].position if len(owned) > 1 else "+attack"
                self.text.add(
                    f"Use {command} A {target}, or {command} to choose."
                    if target
                    else f"Use {command} to choose."
                )
                self.text.add("Move details: +movedex <move>")
                self.text.rule()
        if self.waiting_on:
            self.text.add(
                "Waiting on " + str(getattr(self.waiting_on, "name", self.waiting_on)) + "..."
            )
        if self.side and self._phase() != "BATTLE OVER":
            if self._phase() == "RETRY REQUIRED":
                self.text.add("Turn not saved. Retry: +battle/retry")
            elif not owned:
                self.text.add("Choose a replacement. Switch: +switch")
            elif self._phase() == "ACTION QUEUED":
                self.text.add("Your action is queued. Waiting for the other choices.")
            elif len(owned) > 1:
                self.text.add("Your slots: " + ", ".join(entry.position for entry in pending))
                self.text.add("Fight: +attack <slot>")
                self.text.add("Switch: +switch <slot> <party slot>")
            else:
                self.text.add("Fight: +attack    Switch: +switch")
            if owned and self._phase() != "RETRY REQUIRED":
                bag = (
                    "Bag: +item <slot> <item>    Details: +status"
                    if len(owned) > 1
                    else "Bag: +item <item>    Details: +status"
                )
                self.text.add(bag)
            if (
                owned
                and self._phase() != "RETRY REQUIRED"
                and getattr(self.state, "encounter_kind", "") == "wild"
                and getattr(getattr(self.session, "state", self.state), "flee_allowed", True)
            ):
                self.text.add("Run: +flee")
        multi = getattr(getattr(self.session, "state", None), "multi", None)
        if multi:
            from datetime import datetime, timezone

            declarations = getattr(self.session.state, "declare", {}) or {}
            missing = sorted(
                entry.position
                for entry in self.entries
                if entry.pokemon is not None
                and getattr(entry.pokemon, "hp", 0) > 0
                and entry.position not in declarations
            )
            self.text.add("Waiting on: " + (", ".join(missing) or "no missing choices"))
            deadline = multi.get("deadline")
            if deadline:
                remaining = max(
                    0,
                    int(
                        (
                            datetime.fromisoformat(deadline) - datetime.now(timezone.utc)
                        ).total_seconds()
                    ),
                )
                self.text.add(f"Action deadline: {remaining // 60}m {remaining % 60}s")
        return self.text.render()


class BattleEventPresentation:
    """Style committed messages without changing battle events or outcomes."""

    @staticmethod
    def format(message):
        """Emphasize outcomes while preserving all original narrative content."""
        plain = strip_ansi(str(message)).strip()
        if re.search(r"critical|super effective", plain, re.I):
            return f"  |y{plain}|n"
        if re.search(
            r"fainted|doesn't affect|does not affect|missed|no effect|failed", plain, re.I
        ):
            return f"  |r{plain}|n"
        if re.search(r"\b(?:uses|used)\b", plain):
            return f"|w{plain}|n"
        return "  " + str(message).strip()
