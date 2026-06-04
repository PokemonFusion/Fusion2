"""Idempotent alpha gym test content setup."""

from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any


ALPHA_BADGE_NAME = "Alpha Badge"
ALPHA_BADGE_REGION = "Alpha Test League"
ALPHA_LEAGUE_KEY = "alpha"
ALPHA_GYM_KEY = "alpha_gym"
ALPHA_BADGE_KEY = "alpha_badge"

ALPHA_LEADER_NAME = "Alpha Gym Leader - Rowan"
ALPHA_FOLLOWER_NAME = "Alpha Gym Trainer - Scout Mina"

ALPHA_LEADER_DESCRIPTION = (
    "Alpha/test gym leader for validating static NPC trainer battles, "
    "multi-Pokemon NPC teams, gym leader startup, and Alpha Badge rewards."
)
ALPHA_FOLLOWER_DESCRIPTION = (
    "Optional practice trainer for the alpha gym. This trainer is intentionally "
    "not linked to GymLeaderProfile and should not grant badges."
)
ALPHA_BADGE_DESCRIPTION = (
    "Temporary alpha badge awarded once for defeating Alpha Gym Leader - Rowan."
)

ZERO_STATS = [0, 0, 0, 0, 0, 0]

ALPHA_LEADER_TEMPLATES = (
    {
        "template_key": "alpha-rowan-1",
        "species": "Pikachu",
        "level": 8,
        "move_names": ["Thunder Shock", "Quick Attack", "Tail Whip"],
        "sort_order": 1,
    },
    {
        "template_key": "alpha-rowan-2",
        "species": "Bulbasaur",
        "level": 8,
        "move_names": ["Tackle", "Vine Whip", "Growl"],
        "sort_order": 2,
    },
    {
        "template_key": "alpha-rowan-3",
        "species": "Charmander",
        "level": 8,
        "move_names": ["Ember", "Scratch", "Growl"],
        "sort_order": 3,
    },
)

ALPHA_FOLLOWER_TEMPLATES = (
    {
        "template_key": "alpha-scout-mina-1",
        "species": "Rattata",
        "level": 6,
        "move_names": ["Tackle", "Tail Whip"],
        "sort_order": 1,
    },
    {
        "template_key": "alpha-scout-mina-2",
        "species": "Pidgey",
        "level": 6,
        "move_names": ["Tackle", "Sand Attack"],
        "sort_order": 2,
    },
)


@dataclass(frozen=True)
class AlphaGymSeedResult:
    """Objects created or updated by the alpha gym seed helper."""

    badge: Any
    leader: Any
    follower: Any
    profile: Any
    leader_templates: tuple[Any, ...]
    follower_templates: tuple[Any, ...]


def seed_alpha_gym_content() -> AlphaGymSeedResult:
    """Create or update alpha gym trainer content for test/dev environments."""

    models = _trainer_models()

    badge = _first_or_create(
        models.GymBadge,
        {"name": ALPHA_BADGE_NAME, "region": ALPHA_BADGE_REGION},
        {"description": ALPHA_BADGE_DESCRIPTION},
    )
    _update_fields(badge, description=ALPHA_BADGE_DESCRIPTION)

    leader = _first_or_create(
        models.NPCTrainer,
        {"name": ALPHA_LEADER_NAME},
        {"description": ALPHA_LEADER_DESCRIPTION},
    )
    _update_fields(leader, description=ALPHA_LEADER_DESCRIPTION)

    follower = _first_or_create(
        models.NPCTrainer,
        {"name": ALPHA_FOLLOWER_NAME},
        {"description": ALPHA_FOLLOWER_DESCRIPTION},
    )
    _update_fields(follower, description=ALPHA_FOLLOWER_DESCRIPTION)

    leader_templates = tuple(
        _upsert_template(models.NPCPokemonTemplate, leader, spec)
        for spec in ALPHA_LEADER_TEMPLATES
    )
    follower_templates = tuple(
        _upsert_template(models.NPCPokemonTemplate, follower, spec)
        for spec in ALPHA_FOLLOWER_TEMPLATES
    )

    profile = _upsert_gym_leader_profile(models.GymLeaderProfile, leader, badge)

    return AlphaGymSeedResult(
        badge=badge,
        leader=leader,
        follower=follower,
        profile=profile,
        leader_templates=leader_templates,
        follower_templates=follower_templates,
    )


def _upsert_template(model, trainer, spec: dict[str, Any]):
    template = _first(
        model.objects.filter(
            npc_trainer=trainer,
            template_key=spec["template_key"],
        ).order_by("id")
    )
    fields = {
        "npc_trainer": trainer,
        "template_key": spec["template_key"],
        "species": spec["species"],
        "level": spec["level"],
        "ability": "",
        "nature": "Hardy",
        "gender": "N",
        "ivs": list(ZERO_STATS),
        "evs": list(ZERO_STATS),
        "held_item": "",
        "move_names": list(spec["move_names"]),
        "sort_order": spec["sort_order"],
    }
    if template is None:
        return model.objects.create(**fields)
    _update_fields(template, **fields)
    return template


def _upsert_gym_leader_profile(model, leader, badge):
    profile = _first(
        model.objects.filter(
            league_key=ALPHA_LEAGUE_KEY,
            gym_key=ALPHA_GYM_KEY,
        ).order_by("id")
    )
    fields = {
        "npc_trainer": leader,
        "badge": badge,
        "league_key": ALPHA_LEAGUE_KEY,
        "gym_key": ALPHA_GYM_KEY,
        "badge_key": ALPHA_BADGE_KEY,
        "required_badge_count": 0,
        "is_enabled": True,
        "sort_order": 1,
    }
    if profile is None:
        return model.objects.create(**fields)
    _update_fields(profile, **fields)
    return profile


def _first_or_create(model, lookup: dict[str, Any], defaults: dict[str, Any]):
    row = _first(model.objects.filter(**lookup).order_by("id"))
    if row is not None:
        return row
    values = dict(lookup)
    values.update(defaults)
    return model.objects.create(**values)


def _first(queryset):
    first = getattr(queryset, "first", None)
    if callable(first):
        return first()
    rows = list(queryset or [])
    return rows[0] if rows else None


def _update_fields(obj, **fields) -> None:
    changed = []
    for name, value in fields.items():
        if getattr(obj, name, None) != value:
            setattr(obj, name, value)
            changed.append(name)
    save = getattr(obj, "save", None)
    if changed and callable(save):
        try:
            save(update_fields=changed)
        except TypeError:
            save()


def _trainer_models():
    from pokemon.models.trainer import (
        GymBadge,
        GymLeaderProfile,
        NPCPokemonTemplate,
        NPCTrainer,
    )

    return SimpleNamespace(
        GymBadge=GymBadge,
        GymLeaderProfile=GymLeaderProfile,
        NPCPokemonTemplate=NPCPokemonTemplate,
        NPCTrainer=NPCTrainer,
    )


__all__ = [
    "ALPHA_BADGE_KEY",
    "ALPHA_BADGE_NAME",
    "ALPHA_FOLLOWER_NAME",
    "ALPHA_GYM_KEY",
    "ALPHA_LEADER_NAME",
    "AlphaGymSeedResult",
    "seed_alpha_gym_content",
]
