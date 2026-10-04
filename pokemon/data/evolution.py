"""Fail-closed evolution rules for the checked-in dex (see docs/evolution.md)."""

from dataclasses import dataclass, field
from typing import List, Optional

from ..dex import POKEDEX

SUPPORTED_TYPES = frozenset({"level", "useItem", "levelFriendship", "levelMove", "levelHold", "levelExtra"})
UNSUPPORTED_TYPES = frozenset({"trade", "other"})
# These require state PF2 does not yet record, including omissions in the dex.
UNSUPPORTED_TARGETS = {"shedinja": "extra offspring and Poké Ball", "palafin": "Union Circle"}
SUPPORTED_CONDITIONS = frozenset(
    {
        "",
        "at night",
        "during the day",
        "during rain",
        "from a special Rockruff",
        "with an Atk stat > its Def stat",
        "with an Atk stat < its Def stat",
        "with an Atk stat equal to its Def stat",
        "with a Remoraid in party",
        "with a Dark-type in the party",
        "near a special magnetic field",
        "with a Fairy-type move and two levels of Affection",
    }
)
UNSUPPORTED_CONDITIONS = frozenset({"with the console turned upside-down"})


def normalize_name(value: str) -> str:
    """Normalize a complete name, never a prefix or substring."""
    return "".join(c for c in str(value).casefold() if c.isalnum())


def lookup_species(name):
    """Resolve generated keys and punctuated display names without guessing."""
    key = normalize_name(name)
    matches = {p.name: p for k, p in POKEDEX.items() if key in (normalize_name(k), normalize_name(p.name))}
    return next(iter(matches.values())) if len(matches) == 1 else None


@dataclass(frozen=True)
class EvolutionContext:
    """Server-derived evidence; missing context never satisfies a condition."""

    friendship: int = 0
    moves: tuple = ()
    move_types: tuple = ()
    held_item: str = ""
    gender: str = ""
    ability: str = ""
    nature: str = ""
    time: str = ""
    weather: str = ""
    region: str = ""
    magnetic_field: bool = False
    party_species: tuple = ()
    party_types: tuple = ()
    stats: dict = field(default_factory=dict)

    def meets(self, condition):
        """Evaluate only enumerated conditions, not arbitrary dex prose."""
        atk, defense = self.stats.get("atk"), self.stats.get("def")
        checks = {
            "": True,
            "at night": self.time == "night",
            "during the day": self.time == "day",
            "during rain": self.weather in {"rain", "raindance"},
            "from a special Rockruff": normalize_name(self.ability) == "owntempo" and self.time == "dusk",
            "with a Remoraid in party": "remoraid" in {normalize_name(s) for s in self.party_species},
            "with a Dark-type in the party": "dark" in {normalize_name(t) for t in self.party_types},
            "near a special magnetic field": self.magnetic_field,
            # Gen 9 merges affection into friendship.
            "with a Fairy-type move and two levels of Affection": self.friendship >= 160
            and "fairy" in {normalize_name(t) for t in self.move_types},
        }
        if atk is not None and defense is not None:
            checks.update(
                {
                    "with an Atk stat > its Def stat": atk > defense,
                    "with an Atk stat < its Def stat": atk < defense,
                    "with an Atk stat equal to its Def stat": atk == defense,
                }
            )
        return checks.get(condition, False)


def required_item(evo):
    """Include the dex's Kleavor spelling/field exception without editing data."""
    if normalize_name(evo.name) == "kleavor":
        return "Black Augurite"
    return evo.raw.get("evoItem")


def get_evolution_items() -> List[str]:
    """Return complete evolution item names, including held requirements."""
    return sorted({required_item(p) for p in POKEDEX.values() if required_item(p)})


def evolution_options(species, *, level, item=None, context=None):
    """Return validated direct successors of the exact current species/form."""
    current = lookup_species(species)
    context = context or EvolutionContext()
    if not current or normalize_name(context.held_item) == "everstone":
        return []
    result = []
    regional_bases = set()
    for name in current.evos:
        candidate = lookup_species(name)
        if candidate:
            region = candidate.raw.get("evoRegion", "")
            if "-Hisui" in candidate.name and "-Hisui" not in current.name:
                region = "Hisui"
            if region and normalize_name(region) == normalize_name(context.region):
                regional_bases.add(candidate.raw.get("baseSpecies"))
    for name in current.evos:
        evo = lookup_species(name)
        if not evo or normalize_name(evo.raw.get("prevo", "")) != normalize_name(current.name):
            continue
        raw, key = evo.raw, normalize_name(evo.name)
        kind = raw.get("evoType", "level")
        condition = raw.get("evoCondition", "")
        if key == "kleavor":
            condition = ""
        if kind not in SUPPORTED_TYPES or key in UNSUPPORTED_TARGETS:
            continue
        if level < (evo.evo_level or 0) or not context.meets(condition):
            continue
        gender = raw.get("gender")
        if gender in {"M", "F"} and context.gender != gender:
            continue
        region = raw.get("evoRegion", "")
        # Older dex rows omit evoRegion on Hisuian evolutions of base forms.
        if "-Hisui" in evo.name and "-Hisui" not in current.name:
            region = "Hisui"
        if region and normalize_name(context.region) != normalize_name(region):
            continue
        if kind == "useItem":
            if not item or not required_item(evo) or normalize_name(item) != normalize_name(required_item(evo)):
                continue
        elif item:  # Never spend a supplied item on an unrelated level evolution.
            continue
        elif kind == "levelFriendship" and context.friendship < 160:
            continue
        elif kind == "levelMove" and normalize_name(raw.get("evoMove", "")) not in {
            normalize_name(m) for m in context.moves
        }:
            continue
        elif kind == "levelHold" and (
            not required_item(evo) or normalize_name(context.held_item) != normalize_name(required_item(evo))
        ):
            continue
        if (
            normalize_name(current.name) == "rockruff"
            and normalize_name(context.ability) == "owntempo"
            and key != "lycanrocdusk"
        ):
            continue
        if key in {"toxtricity", "toxtricitylowkey"}:
            low_key = {
                "lonely",
                "bold",
                "relaxed",
                "timid",
                "serious",
                "modest",
                "mild",
                "quiet",
                "bashful",
                "calm",
                "gentle",
                "careful",
            }
            if not context.nature or (normalize_name(context.nature) in low_key) != (key == "toxtricitylowkey"):
                continue
        result.append(evo)
    # The matching regional branch supersedes its base counterpart.
    result = [p for p in result if p.name not in regional_bases]
    if any(p.name == "Sylveon" for p in result):
        result = [p for p in result if p.name not in {"Espeon", "Umbreon"}]
    return result


def get_evolution(species: str, *, level: int, item: Optional[str] = None, context=None, target=None) -> Optional[str]:
    """Choose a unique eligible branch, or an explicitly requested exact target."""
    choices = evolution_options(species, level=level, item=item, context=context)
    if target:
        choices = [p for p in choices if normalize_name(p.name) == normalize_name(target)]
    return choices[0].name if len(choices) == 1 else None


def attempt_evolution(pokemon, *, item=None, context=None, target=None):
    """Apply a validated transition in memory; persistence belongs to the service."""
    context = context or EvolutionContext(
        friendship=getattr(pokemon, "friendship", 0),
        held_item=getattr(pokemon, "held_item", ""),
        gender=getattr(pokemon, "gender", ""),
        ability=getattr(pokemon, "ability", ""),
        nature=getattr(pokemon, "nature", ""),
    )
    result = get_evolution(
        getattr(pokemon, "species", None) or pokemon.name,
        level=pokemon.level,
        item=item,
        context=context,
        target=target,
    )
    if not result:
        return None
    source = lookup_species(getattr(pokemon, "species", None) or pokemon.name)
    data = lookup_species(result)
    if hasattr(pokemon, "ability") and data.raw.get("abilities"):
        slot = next(
            (
                key
                for key, ability in source.raw.get("abilities", {}).items()
                if normalize_name(ability) == normalize_name(pokemon.ability)
            ),
            "0",
        )
        pokemon.ability = data.raw["abilities"].get(slot, data.raw["abilities"].get("0", ""))
    if hasattr(pokemon, "species"):
        pokemon.species = result
    else:
        pokemon.name = result
    if hasattr(pokemon, "type_"):
        pokemon.type_ = ", ".join(data.types)
    if data.raw.get("evoType") == "levelHold":
        pokemon.held_item = ""
    # Stats are calculated from species on demand; invalidate legacy overrides.
    for attr in ("_cached_stats", "_types_override"):
        pokemon.__dict__.pop(attr, None)
    return result
