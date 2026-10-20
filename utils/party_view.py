"""Compact party cards using the same roster and selectors as battles."""

from dataclasses import dataclass
from types import SimpleNamespace

from pokemon.helpers.party_helpers import get_party_slots, pokemon_is_usable
from pokemon.helpers.pokemon_helpers import get_max_hp
from pokemon.models.stats import level_for_exp
from utils.ansi_widgets import apply_screen_reader, type_chip
from utils.display import _get_pokemon_types
from utils.fusion import _growth_from_pokemon, get_active_fusion_pokemon, get_battle_party_with_fusion
from utils.pokemon_utils import build_battle_pokemon_from_model
from utils.xp_utils import get_display_xp


@dataclass
class PartyEntry:
    """A displayed member and its stable player-facing selector."""

    selector: int | str
    pokemon: object
    source: object
    owner: str = ""
    is_fusion: bool = False

    @property
    def name(self) -> str:
        """Keep species visible when a companion has a nickname."""
        species = getattr(self.pokemon, "species", "Unknown")
        species = str(getattr(species, "name", species))
        if self.is_fusion:
            return f"{self.owner} ({species} form)"
        name = str(getattr(self.pokemon, "name", None) or species)
        return f"{name} ({species})" if name != species else name

    @property
    def hp(self) -> int:
        """Read current HP in the same order as battle preparation."""
        hp = getattr(self.pokemon, "current_hp", None)
        if hp is None:
            hp = getattr(self.pokemon, "hp", 0)
        return max(0, int(hp or 0))

    @property
    def status(self) -> str:
        """Use full condition names, giving fainting priority."""
        if not pokemon_is_usable(self.pokemon):
            return "FAINTED"
        code = str(getattr(self.pokemon, "status", "") or "").strip().lower()
        return {
            "": "OK",
            "0": "OK",
            "nrm": "OK",
            "norm": "OK",
            "brn": "BURNED",
            "psn": "POISONED",
            "tox": "BADLY POISONED",
            "par": "PARALYZED",
            "slp": "ASLEEP",
            "frz": "FROZEN",
        }.get(code, code.upper())


class PartyView:
    """Build party cards without closing gaps or reordering stored slots."""

    def __init__(self, caller):
        """Overlay the active Fusion while retaining canonical selectors."""
        self.caller = caller
        slots = get_party_slots(caller)
        self.roster = get_battle_party_with_fusion(caller, [mon for mon in slots if mon])
        fused = get_active_fusion_pokemon(caller)
        db = getattr(caller, "db", SimpleNamespace())
        self.entries = [PartyEntry(slot, mon, mon) for slot, mon in enumerate(slots, 1) if mon]
        self.fusion = None
        if fused is not None or getattr(db, "fusion_species", None):
            display = self._fusion_display(fused, db)
            existing = next((entry for entry in self.entries if self._same(entry.source, fused)), None)
            selector = (
                existing.selector
                if existing
                else next((slot for slot, mon in enumerate(slots, 1) if mon is None), "fusion")
            )
            self.fusion = PartyEntry(selector, display, fused, getattr(caller, "key", "You"), True)
            if existing:
                self.entries.remove(existing)
            self.entries.append(self.fusion)
            self.entries.sort(key=lambda entry: 7 if entry.selector == "fusion" else entry.selector)
        self.lead = next((mon for mon in self.roster if pokemon_is_usable(mon)), None)
        self.screen_reader = getattr(db, "ui_mode", None) in {"sr", "screenreader"}
        attributes = getattr(caller, "attributes", None)
        if attributes is not None:
            self.screen_reader = self.screen_reader or bool(attributes.get("sheet_screen_reader", default=False))

    @staticmethod
    def _same(left, right) -> bool:
        """Match separately loaded ORM instances by their owned identifier."""
        if left is None or right is None:
            return False
        if left is right:
            return True
        identifier = getattr(left, "unique_id", None)
        return identifier is not None and str(identifier) == str(getattr(right, "unique_id", None))

    @staticmethod
    def _fusion_display(fused, db):
        """Use the battle adapter for active-form level, HP, and boosted stats."""
        if fused is not None:
            battle = build_battle_pokemon_from_model(fused)
            display = SimpleNamespace(
                name=fused.species,
                species=fused.species,
                gender=getattr(db, "gender", "?"),
                level=battle.level,
                hp=battle.hp,
                status=getattr(fused, "status", ""),
                held_item=getattr(fused, "held_item", ""),
                types=battle.types,
                total_exp=getattr(fused, "_pf2_fusion_xp", getattr(fused, "total_exp", 0)),
                growth_rate=_growth_from_pokemon(fused),
                unique_id=getattr(fused, "unique_id", None),
                ability=getattr(fused, "ability", None),
                nature=getattr(fused, "nature", None),
                _cached_stats={
                    name: battle.getStat(key, True, True)
                    for name, key in (
                        ("hp", "hp"),
                        ("attack", "atk"),
                        ("defense", "def"),
                        ("special_attack", "spa"),
                        ("special_defense", "spd"),
                        ("speed", "spe"),
                    )
                },
            )
            for attr in ("activemoveslot_set", "pp_bonuses", "moves", "ivs", "evs"):
                if hasattr(fused, attr):
                    setattr(display, attr, getattr(fused, attr))
        else:
            # Legacy characters may retain a form description without a model.
            # Keep it inspectable, but never include it in the battle-ready count.
            stats = getattr(db, "stats", None) or {}
            hp = getattr(db, "hp", None)
            display = SimpleNamespace(
                name=db.fusion_species,
                species=db.fusion_species,
                gender=getattr(db, "gender", "?"),
                level=getattr(db, "level", None),
                total_exp=getattr(db, "total_exp", 0),
                hp=hp if hp is not None else 0,
                ability=getattr(db, "fusion_ability", None),
                nature=getattr(db, "fusion_nature", None),
                status=getattr(db, "status", ""),
                held_item="",
                _cached_stats=stats,
                unique_id=getattr(db, "fusion_id", None),
            )
        display._pf2_is_fusion_slot = True
        return display

    def select(self, selector) -> PartyEntry | None:
        """Resolve a numbered slot or the same Fusion alias used in battle."""
        if selector == "fusion":
            return self.fusion
        return next((entry for entry in self.entries if entry.selector == selector), None)

    @staticmethod
    def _hp_bar(hp, maximum, width=10) -> str:
        """Draw an ASCII health bar that also works in text-only clients."""
        ratio = max(0, min(1, hp / maximum)) if maximum > 0 else 0
        filled = max(1, int(width * ratio)) if ratio > 0 else 0
        color = "|g" if ratio > 0.5 else "|y" if ratio > 0.2 else "|r"
        return f"{color}[{'#' * filled}{'-' * (width - filled)}]|n"

    def render(self) -> str:
        """Return two-line cards and discoverable summary/moves commands."""
        if not self.entries:
            return "You have no Pokémon in your party."
        count = sum(not entry.is_fusion for entry in self.entries)
        ready = sum(pokemon_is_usable(mon) for mon in self.roster)
        extra = " + Fusion" if self.fusion else ""
        lines = [f"|wParty Pokémon|n - {count}/6{extra} | {ready} able to battle", ""]
        for entry in self.entries:
            mon = entry.pokemon
            level = getattr(mon, "computed_level", None) or getattr(mon, "level", None)
            if level is None:
                level = level_for_exp(get_display_xp(mon), getattr(mon, "growth_rate", "medium_fast"))
            types = _get_pokemon_types(mon)
            type_text = "/".join(type_chip(t.upper()) for t in types) or "Unknown"
            badges = []
            if entry.is_fusion:
                badges.append("|c[YOU / FUSION]|n")
                if not any(self._same(entry.source, member) for member in self.roster):
                    badges.append("|x[NOT BATTLING]|n")
            if self._same(entry.source, self.lead):
                badges.append("|y[LEAD]|n")
            gender = getattr(mon, "gender", None) or "?"
            lines.append(
                f"{entry.selector}: |w{entry.name}|n  {gender}  Lv {level}  [{type_text}] {' '.join(badges)}".rstrip()
            )
            maximum = get_max_hp(mon)
            hp_bar = "" if self.screen_reader else self._hp_bar(entry.hp, maximum) + " "
            status = entry.status
            color = "|g" if status == "OK" else "|r" if status == "FAINTED" else "|y"
            held = getattr(mon, "held_item", None) or "None"
            lines.append(f"   HP {hp_bar}{entry.hp}/{maximum}  {color}{status}|n  Held: {held}")
            lines.append("")
        lines.extend(("Summary: +party <slot>", "Moves:   +party/moves <slot>"))
        if self.fusion:
            lines.append("Fusion:  +party fusion | +party/moves fusion")
        output = "\n".join(lines)
        return apply_screen_reader(output) if self.screen_reader else output
