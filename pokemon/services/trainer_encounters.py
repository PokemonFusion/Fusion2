"""Random NPC trainer encounter generation."""

from __future__ import annotations

import random
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from utils.pokemon_config import RARITY_WEIGHTS, TIERS


DEFAULT_TRAINER_CLASSES = (
    "Youngster",
    "Lass",
    "Camper",
    "Picnicker",
    "Bug Catcher",
)
DEFAULT_TRAINER_NAMES = (
    "Alex",
    "Bailey",
    "Casey",
    "Devon",
    "Emery",
)
FALLBACK_TEAM_POOL = (
    {"species": "Rattata", "min_level": 5, "max_level": 5, "weight": 1},
    {"species": "Pidgey", "min_level": 5, "max_level": 5, "weight": 1},
    {"species": "Caterpie", "min_level": 5, "max_level": 5, "weight": 1},
)


@dataclass(frozen=True)
class TrainerEncounter:
    """Battle-ready data for an NPC trainer source."""

    display_name: str
    trainer_class: str
    source_type: str
    battle_format: str
    ai_profile: str
    team: list[Any]
    intro_text: str
    victory_text: str = ""
    defeat_text: str = ""
    reward_profile: dict[str, object] = field(default_factory=dict)
    ruleset: dict[str, object] = field(default_factory=dict)
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class StaticTrainerTemplateCheck:
    """Read-only validation summary for one NPCPokemonTemplate row."""

    template_key: str
    species: str
    level: int
    sort_order: int
    issues: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    @property
    def is_valid(self) -> bool:
        return not self.issues


@dataclass(frozen=True)
class StaticTrainerCheck:
    """Read-only validation summary for a static NPC trainer."""

    name: str
    found: bool
    templates: tuple[StaticTrainerTemplateCheck, ...] = ()
    issues: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    @property
    def template_count(self) -> int:
        return len(self.templates)

    @property
    def can_start_battle(self) -> bool:
        return self.found and bool(self.templates) and not self.issues


class TrainerEncounterError(ValueError):
    """Base error for trainer encounter construction failures."""


class StaticTrainerNotFoundError(TrainerEncounterError):
    """Raised when a named static NPC trainer cannot be found."""


class StaticTrainerTeamError(TrainerEncounterError):
    """Raised when a static NPC trainer has no usable template team."""


def generate_random_trainer_encounter(
    room=None,
    *,
    rng=None,
    display_name: str | None = None,
) -> TrainerEncounter:
    """Generate an ephemeral random trainer encounter for a hunt or fallback."""

    rng = rng or random
    entries = _trainer_entries_from_room(room)
    entry = _weighted_choice(entries, rng)

    trainer_class = _text(
        entry.get("trainer_class")
        or entry.get("class")
        or entry.get("trainer_type")
        or _choose(DEFAULT_TRAINER_CLASSES, rng),
        "Trainer",
    )
    display_value = display_name or entry.get("display_name") or entry.get("trainer_name")
    if not display_value:
        display_value = f"{trainer_class} {_choose(DEFAULT_TRAINER_NAMES, rng)}"
    resolved_display_name = _text(display_value, f"{trainer_class} Trainer")

    team = [_build_battle_pokemon(spec, entry, rng) for spec in _team_specs(entry)]
    if not team:
        team = [_build_battle_pokemon(dict(FALLBACK_TEAM_POOL[0]), entry, rng)]

    lead_name = getattr(team[0], "name", "Pokemon")
    intro_text = _text(
        entry.get("intro_text"),
        f"{resolved_display_name} challenges you with {lead_name}!",
    )

    return TrainerEncounter(
        display_name=resolved_display_name,
        trainer_class=trainer_class,
        source_type=_text(entry.get("source_type"), "random"),
        battle_format=_text(entry.get("battle_format"), "single"),
        ai_profile=_text(entry.get("ai_profile"), "basic"),
        team=team,
        intro_text=intro_text,
        victory_text=_text(entry.get("victory_text"), ""),
        defeat_text=_text(entry.get("defeat_text"), ""),
        reward_profile=_dict(entry.get("reward_profile")),
        ruleset=_dict(entry.get("ruleset")),
        metadata=_dict(entry.get("metadata")),
    )


def generate_static_trainer_encounter(trainer_or_name) -> TrainerEncounter:
    """Build a battle-ready encounter from an existing NPCTrainer."""

    trainer = _resolve_static_trainer(trainer_or_name)
    templates = _templates_for_trainer(trainer)
    display_name = _trainer_display_name(trainer)
    if not templates:
        raise StaticTrainerTeamError(f"NPC trainer '{display_name}' has no Pokemon templates.")

    team = []
    for template in templates:
        team.append(_battle_pokemon_from_template(template, trainer))
    if not team:
        raise StaticTrainerTeamError(f"NPC trainer '{display_name}' has no usable Pokemon templates.")

    lead_name = getattr(team[0], "name", "Pokemon")
    trainer_class = _text(
        getattr(trainer, "trainer_class", None)
        or getattr(trainer, "title", None)
        or getattr(trainer, "npc_class", None),
        "NPC Trainer",
    )

    return TrainerEncounter(
        display_name=display_name,
        trainer_class=trainer_class,
        source_type="static",
        battle_format=_text(getattr(trainer, "battle_format", None), "single"),
        ai_profile=_text(getattr(trainer, "ai_profile", None), "basic"),
        team=team,
        intro_text=_text(
            getattr(trainer, "intro_text", None),
            f"{display_name} challenges you with {lead_name}!",
        ),
        victory_text=_text(getattr(trainer, "victory_text", None), ""),
        defeat_text=_text(getattr(trainer, "defeat_text", None), ""),
        reward_profile=_dict(getattr(trainer, "reward_profile", None)),
        ruleset=_dict(getattr(trainer, "ruleset", None)),
        metadata={
            "npc_trainer_id": getattr(trainer, "id", None),
            "template_keys": [
                _text(getattr(template, "template_key", None), "")
                for template in templates
            ],
        },
    )


def check_static_trainer(trainer_or_name) -> StaticTrainerCheck:
    """Return a read-only startup validation summary for a static trainer."""

    try:
        trainer = _resolve_static_trainer(trainer_or_name)
    except StaticTrainerNotFoundError:
        name = _text(trainer_or_name, "")
        return StaticTrainerCheck(
            name=name,
            found=False,
            issues=(f"NPC trainer '{name}' was not found.",),
        )

    templates = tuple(_check_template(template) for template in _templates_for_trainer(trainer))
    issues: list[str] = []
    warnings: list[str] = []
    if not templates:
        issues.append("No Pokemon templates.")
    if len(templates) > 6:
        warnings.append(
            f"Trainer has {len(templates)} template Pokemon; battle Team storage is capped at 6."
        )
    for index, template in enumerate(templates, start=1):
        for issue in template.issues:
            issues.append(f"Template {index}: {issue}")
        for warning in template.warnings:
            warnings.append(f"Template {index}: {warning}")

    return StaticTrainerCheck(
        name=_trainer_display_name(trainer),
        found=True,
        templates=templates,
        issues=tuple(issues),
        warnings=tuple(warnings),
    )


def list_static_trainers_with_templates() -> list[StaticTrainerCheck]:
    """Return static trainers that currently have at least one template row."""

    model = _npc_trainer_model()
    manager = getattr(model, "objects", None)
    checks: list[StaticTrainerCheck] = []
    for trainer in _all_manager(manager):
        check = check_static_trainer(trainer)
        if check.template_count > 0:
            checks.append(check)
    return sorted(checks, key=lambda check: check.name.lower())


def _trainer_entries_from_room(room) -> list[dict[str, Any]]:
    db = getattr(room, "db", None)
    if db is not None:
        trainer_chart = _coerce_entries(getattr(db, "npc_trainer_chart", None))
        if trainer_chart:
            return trainer_chart

        hunt_chart = _coerce_entries(getattr(db, "hunt_chart", None))
        if hunt_chart:
            return hunt_chart

        spawn_table = _coerce_entries(getattr(db, "spawn_table", None))
        if spawn_table:
            return spawn_table

    return [dict(entry) for entry in FALLBACK_TEAM_POOL]


def _coerce_entries(value) -> list[dict[str, Any]]:
    if not value or isinstance(value, (str, bytes)):
        return []
    if isinstance(value, Mapping):
        if _species_name(value) or value.get("team"):
            return [dict(value)]
        value = value.values()
    if not isinstance(value, Iterable):
        return []

    entries: list[dict[str, Any]] = []
    for raw in value:
        if isinstance(raw, Mapping):
            entry = dict(raw)
        elif isinstance(raw, str):
            entry = {"species": raw}
        else:
            continue
        if _species_name(entry) or entry.get("team"):
            entries.append(entry)
    return entries


def _team_specs(entry: Mapping[str, Any]) -> list[dict[str, Any]]:
    team = entry.get("team")
    if team and not isinstance(team, (str, bytes)):
        specs: list[dict[str, Any]] = []
        for raw in team:
            if isinstance(raw, Mapping):
                spec = dict(raw)
            elif isinstance(raw, str):
                spec = {"species": raw}
            else:
                continue
            if _species_name(spec):
                specs.append(spec)
        if specs:
            return specs

    if _species_name(entry):
        return [dict(entry)]
    return [dict(FALLBACK_TEAM_POOL[0])]


def _build_battle_pokemon(spec: Mapping[str, Any], defaults: Mapping[str, Any], rng):
    species = _species_name(spec) or _species_name(defaults) or FALLBACK_TEAM_POOL[0]["species"]
    level = _level_for(spec, defaults, rng)
    move_names = spec.get("move_names", defaults.get("move_names"))
    if move_names is not None and not isinstance(move_names, list):
        move_names = (
            list(move_names)
            if isinstance(move_names, Sequence) and not isinstance(move_names, str)
            else None
        )

    return _create_battle_pokemon(
        species,
        level,
        trainer=None,
        is_wild=False,
        template_key=_text(spec.get("template_key") or defaults.get("template_key"), "random"),
        move_names=move_names,
    )


def _battle_pokemon_from_template(template, trainer):
    species = _text(getattr(template, "species", None), "")
    if not species:
        raise StaticTrainerTeamError("NPC trainer template is missing a species.")
    level = max(1, _int(getattr(template, "level", 1), 1))

    try:
        from pokemon.data.generation import generate_pokemon

        generated = generate_pokemon(species, level=level)
    except Exception as err:
        raise StaticTrainerTeamError(
            f"NPC trainer template for '{species}' could not be generated: {err}"
        ) from err

    move_names = list(
        getattr(template, "move_names", None)
        or getattr(generated, "moves", [])
        or ["Tackle"]
    )[:4]
    move_cls, pokemon_cls = _battle_classes()
    max_hp = getattr(getattr(generated, "stats", None), "hp", level)
    ability = _text(getattr(template, "ability", None), _text(getattr(generated, "ability", ""), ""))
    nature = _text(getattr(template, "nature", None), _text(getattr(generated, "nature", ""), "Hardy"))
    gender = _text(getattr(template, "gender", None), _text(getattr(generated, "gender", ""), "N"))
    encounter = _create_encounter_pokemon(
        species=getattr(getattr(generated, "species", None), "name", species),
        level=level,
        source_kind="npc",
        gender=gender,
        nature=nature,
        ability=ability,
        ivs=list(getattr(template, "ivs", []) or []),
        evs=list(getattr(template, "evs", []) or []),
        held_item=_text(getattr(template, "held_item", None), ""),
        current_hp=max_hp,
        move_names=move_names,
        npc_trainer=trainer,
        template_key=_text(getattr(template, "template_key", None), ""),
    )

    return pokemon_cls(
        name=getattr(getattr(generated, "species", None), "name", species),
        level=level,
        hp=max_hp,
        max_hp=max_hp,
        moves=[move_cls(name=move_name) for move_name in move_names],
        ability=ability,
        ivs=list(getattr(template, "ivs", []) or []),
        evs=list(getattr(template, "evs", []) or []),
        nature=nature,
        model_id=_encounter_ref(encounter),
        gender=gender,
        item=_text(getattr(template, "held_item", None), ""),
    )


def _check_template(template) -> StaticTrainerTemplateCheck:
    species = _text(getattr(template, "species", None), "")
    level = _int(getattr(template, "level", 1), 1)
    issues: list[str] = []
    if not species:
        issues.append("missing species")
    if level < 1:
        issues.append("level must be at least 1")
    move_names = getattr(template, "move_names", None)
    if move_names is not None and not isinstance(move_names, list):
        issues.append("move_names must be a list")
    warnings: list[str] = []
    if isinstance(move_names, list):
        unknown_moves = _unknown_move_names(move_names)
        if unknown_moves:
            warnings.append(
                "unknown move name(s): " + ", ".join(unknown_moves)
            )
    if species:
        try:
            from pokemon.data.generation import generate_pokemon

            generate_pokemon(species, level=max(1, level))
        except Exception as err:
            issues.append(f"species could not be generated: {err}")

    return StaticTrainerTemplateCheck(
        template_key=_text(getattr(template, "template_key", None), ""),
        species=species,
        level=level,
        sort_order=_int(getattr(template, "sort_order", 0), 0),
        issues=tuple(issues),
        warnings=tuple(warnings),
    )


def _unknown_move_names(move_names: list[Any]) -> list[str]:
    unknown: list[str] = []
    for move_name in move_names:
        text = _text(move_name, "")
        if text and not _move_exists(text):
            unknown.append(text)
    return unknown


def _move_exists(move_name: str) -> bool:
    try:
        from pokemon.battle._shared import _normalize_key, ensure_movedex_aliases
        from pokemon.dex import MOVEDEX
    except Exception:
        return True
    if not MOVEDEX:
        return True
    try:
        ensure_movedex_aliases(MOVEDEX)
    except Exception:
        pass
    candidates = {
        move_name,
        move_name.lower(),
        _normalize_key(move_name),
    }
    return any(candidate and candidate in MOVEDEX for candidate in candidates)


def _create_battle_pokemon(*args, **kwargs):
    from pokemon.battle.pokemon_factory import create_battle_pokemon

    return create_battle_pokemon(*args, **kwargs)


def _create_encounter_pokemon(*args, **kwargs):
    from pokemon.services.encounters import create_encounter_pokemon

    return create_encounter_pokemon(*args, **kwargs)


def _encounter_ref(encounter) -> str | None:
    from pokemon.services.encounters import encounter_ref

    return encounter_ref(encounter)


def _battle_classes():
    from pokemon.battle.battledata import Move, Pokemon

    return Move, Pokemon


def _resolve_static_trainer(trainer_or_name):
    if trainer_or_name is not None and not isinstance(trainer_or_name, str):
        return trainer_or_name

    name = _text(trainer_or_name, "")
    if not name:
        raise StaticTrainerNotFoundError("Usage: +npcbattle <npc trainer name>")

    model = _npc_trainer_model()
    manager = getattr(model, "objects", None)
    if manager is None:
        raise StaticTrainerNotFoundError(f"NPC trainer '{name}' was not found.")

    trainer = _first(_filter_manager(manager, name__iexact=name))
    if trainer is None:
        trainer = _first(_filter_manager(manager, name=name))
    if trainer is None:
        raise StaticTrainerNotFoundError(f"NPC trainer '{name}' was not found.")
    return trainer


def _templates_for_trainer(trainer) -> list[Any]:
    model = _npc_template_model()
    manager = getattr(model, "objects", None)
    if manager is not None:
        queryset = _filter_manager(manager, npc_trainer=trainer)
        if hasattr(queryset, "order_by"):
            queryset = queryset.order_by("sort_order", "id")
        return list(queryset or [])

    related = getattr(trainer, "pokemon_templates", None)
    if related is None:
        return []
    if hasattr(related, "all"):
        related = related.all()
    if hasattr(related, "order_by"):
        related = related.order_by("sort_order", "id")
    return list(related or [])


def _npc_trainer_model():
    from pokemon.models.trainer import NPCTrainer

    return NPCTrainer


def _npc_template_model():
    from pokemon.models.trainer import NPCPokemonTemplate

    return NPCPokemonTemplate


def _filter_manager(manager, **kwargs):
    filter_func = getattr(manager, "filter", None)
    if callable(filter_func):
        return filter_func(**kwargs)
    return []


def _all_manager(manager):
    if manager is None:
        return []
    all_func = getattr(manager, "all", None)
    if callable(all_func):
        queryset = all_func()
    else:
        queryset = getattr(manager, "rows", [])
    if hasattr(queryset, "order_by"):
        queryset = queryset.order_by("name")
    return list(queryset or [])


def _first(queryset):
    if queryset is None:
        return None
    first = getattr(queryset, "first", None)
    if callable(first):
        return first()
    rows = list(queryset)
    return rows[0] if rows else None


def _trainer_display_name(trainer) -> str:
    return _text(
        getattr(trainer, "display_name", None) or getattr(trainer, "name", None),
        "NPC Trainer",
    )


def _species_name(entry: Mapping[str, Any]) -> str:
    return _text(entry.get("species") or entry.get("pokemon") or entry.get("name"), "")


def _level_for(spec: Mapping[str, Any], defaults: Mapping[str, Any], rng) -> int:
    raw_level = spec.get("level", defaults.get("level"))
    if raw_level is not None:
        return max(1, _int(raw_level, 5))

    tier_min, tier_max = _tier_bounds(spec.get("tiers", defaults.get("tiers")))
    min_level = _int(spec.get("min_level", defaults.get("min_level", tier_min)), tier_min)
    max_level = _int(spec.get("max_level", defaults.get("max_level", tier_max)), tier_max)
    if max_level < min_level:
        max_level = min_level
    return rng.randint(max(1, min_level), max(1, max_level))


def _weighted_choice(entries: Sequence[dict[str, Any]], rng) -> dict[str, Any]:
    pool = list(entries) or [dict(FALLBACK_TEAM_POOL[0])]
    weights = [_weight_for(entry) for entry in pool]
    return dict(rng.choices(pool, weights=weights, k=1)[0])


def _weight_for(entry: Mapping[str, Any]) -> int:
    if entry.get("weight") is not None:
        return max(1, _int(entry.get("weight"), 1))
    rarity = _text(entry.get("rarity", entry.get("frequency", "common")), "common").lower()
    return max(1, int(RARITY_WEIGHTS.get(rarity, 1)))


def _tier_bounds(value) -> tuple[int, int]:
    tiers = _as_list(value)
    bounds = [TIERS[tier] for tier in tiers if tier in TIERS]
    if not bounds:
        return (5, 5)
    return (min(low for low, _high in bounds), max(high for _low, high in bounds))


def _as_list(value) -> list[Any]:
    if not value:
        return []
    if isinstance(value, (str, bytes)):
        return [str(value)]
    if isinstance(value, Iterable):
        return list(value)
    return [value]


def _choose(values: Sequence[str], rng) -> str:
    return rng.choice(tuple(values))


def _text(value, default: str) -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text or default


def _int(value, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _dict(value) -> dict[str, object]:
    return dict(value) if isinstance(value, Mapping) else {}


__all__ = [
    "TrainerEncounter",
    "TrainerEncounterError",
    "StaticTrainerCheck",
    "StaticTrainerNotFoundError",
    "StaticTrainerTemplateCheck",
    "StaticTrainerTeamError",
    "check_static_trainer",
    "generate_random_trainer_encounter",
    "generate_static_trainer_encounter",
    "list_static_trainers_with_templates",
]
