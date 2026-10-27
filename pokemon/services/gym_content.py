"""Validated, versioned content installation using the existing gym framework."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from types import SimpleNamespace

from pokemon.services.gym_policy import GymPolicy

PROFILE_FIELDS = {
    "badge_key", "required_badge_count", "is_enabled", "sort_order", "battle_format",
    "ai_profile", "strategy_key", "content_stage", "reward_policy", "rematch_cooldown_seconds",
    "intro_text", "victory_text", "defeat_text", "rules_text",
}
TEAM_FIELDS = {"template_key", "species", "level", "ability", "nature", "gender", "ivs", "evs", "held_item", "move_names"}


def _integer(value, label, minimum, maximum):
    """Reject coercions and booleans in authored numeric rules."""
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError(f"{label} must be an integer from {minimum} to {maximum}.")


def _text(value, label, maximum, *, blank=False):
    """Keep content strings within their durable column limits."""
    if not isinstance(value, str) or len(value) > maximum or (not blank and not value.strip()):
        raise ValueError(f"{label} must be {'an optional' if blank else 'a nonempty'} string of at most {maximum} characters.")


@dataclass(frozen=True)
class GymContent:
    """Own a detached JSON definition and its canonical content fingerprint."""

    definition: dict
    digest: str

    @classmethod
    def parse(cls, value):
        """Validate every supported author field before any database allocation."""
        from pokemon.dex import POKEDEX
        from pokemon.data.generation import NATURES
        from pokemon.names import normalize_name, resolve_dex_entry
        from pokemon.services.trainer_encounters import _check_template

        try:
            data = json.loads(json.dumps(value, allow_nan=False))
        except (TypeError, ValueError) as error:
            raise ValueError("Gym content must be a finite JSON object.") from error
        if not isinstance(data, dict) or set(data) != {"version", "league_key", "gym_key", "leader", "badge", "profile", "team"}:
            raise ValueError("Gym content requires exactly version, league_key, gym_key, leader, badge, profile and team.")
        _integer(data["version"], "version", 1, 2147483647)
        for key in ("league_key", "gym_key"):
            if not isinstance(data[key], str) or not re.fullmatch(r"[a-z][a-z0-9_]{0,79}", data[key]):
                raise ValueError(f"{key} must be a stable lowercase key (at most 80 characters).")
        for key, fields in (("leader", {"name", "description"}), ("badge", {"name", "region", "description"})):
            row = data[key]
            if not isinstance(row, dict) or set(row) != fields:
                raise ValueError(f"{key} has unknown or missing fields; expected {sorted(fields)}.")
            for field, text in row.items():
                _text(text, f"{key}.{field}", 10000 if field == "description" else (100 if field == "region" else 255), blank=field == "description")
        profile = data["profile"]
        if not isinstance(profile, dict) or set(profile) != PROFILE_FIELDS:
            raise ValueError(f"profile has unknown or missing fields; expected {sorted(PROFILE_FIELDS)}.")
        if not isinstance(profile["badge_key"], str) or not re.fullmatch(r"[a-z][a-z0-9_]{0,79}", profile["badge_key"]):
            raise ValueError("profile.badge_key must be a stable lowercase key.")
        _integer(profile["required_badge_count"], "required_badge_count", 0, 65535)
        _integer(profile["sort_order"], "sort_order", 0, 65535)
        if type(profile["is_enabled"]) is not bool:
            raise ValueError("is_enabled must be true or false.")
        for key in ("intro_text", "victory_text", "defeat_text", "rules_text"):
            _text(profile[key], key, 10000, blank=True)
        for key, maximum in (("battle_format", 10), ("ai_profile", 80), ("strategy_key", 40), ("content_stage", 16), ("reward_policy", 16)):
            _text(profile[key], key, maximum, blank=key == "strategy_key")
        policy = GymPolicy.from_profile(SimpleNamespace(**profile))
        if policy.reward_policy != "badge_only":
            raise ValueError("Authored gyms support badge_only first clears and practice rematches; legacy rewards are not authorable.")
        team = data["team"]
        if not isinstance(team, list) or not (2 if policy.battle_format == "double" else 1) <= len(team) <= 6:
            raise ValueError("Team must contain one to six members, or two to six for doubles.")
        keys = set()
        for index, row in enumerate(team, 1):
            if not isinstance(row, dict) or set(row) != TEAM_FIELDS:
                raise ValueError(f"Team member {index} has unknown or missing fields; expected {sorted(TEAM_FIELDS)}.")
            for key, maximum in (("template_key", 100), ("species", 50), ("ability", 50), ("nature", 20), ("gender", 10), ("held_item", 50)):
                _text(row[key], f"team[{index}].{key}", maximum, blank=key == "held_item")
            if row["template_key"] in keys:
                raise ValueError(f"Duplicate team template_key: {row['template_key']}.")
            keys.add(row["template_key"])
            _integer(row["level"], f"team[{index}].level", 1, 100)
            for key, maximum in (("ivs", 31), ("evs", 252)):
                if not isinstance(row[key], list) or len(row[key]) != 6:
                    raise ValueError(f"team[{index}].{key} must contain six integers.")
                for number in row[key]:
                    _integer(number, f"team[{index}].{key}", 0, maximum)
            if sum(row["evs"]) > 510:
                raise ValueError(f"team[{index}].evs exceeds 510 total.")
            if row["gender"] not in {"M", "F", "N"}:
                raise ValueError(f"team[{index}].gender must be M, F or N.")
            if normalize_name(row["nature"]) not in {normalize_name(name) for name in NATURES}:
                raise ValueError(f"team[{index}].nature is unknown.")
            species = resolve_dex_entry(POKEDEX, row["species"])
            if not species:
                raise ValueError(f"team[{index}].species is unknown.")
            if any(species.raw.get(key) for key in ("battleOnly", "requiredItem", "requiredItems", "requiredAbility")):
                raise ValueError(f"team[{index}] uses a form requiring an unsupported pre-battle activation.")
            if normalize_name(row["ability"]) not in {normalize_name(getattr(name, "name", name)) for name in species.abilities.values()}:
                raise ValueError(f"team[{index}].ability is not native to its species.")
            moves = row["move_names"]
            if not isinstance(moves, list) or not 1 <= len(moves) <= 4 or any(not isinstance(move, str) or not move for move in moves):
                raise ValueError(f"team[{index}].move_names requires one to four named moves.")
            if len({normalize_name(move) for move in moves}) != len(moves):
                raise ValueError(f"team[{index}] repeats a move.")
            if row["held_item"]:
                from pokemon.dex import ITEMDEX
                item = ITEMDEX.get(normalize_name(row["held_item"]))
                if item is None or getattr(item, "is_nonstandard", None):
                    raise ValueError(f"team[{index}].held_item is unknown or unsupported.")
            check = _check_template(SimpleNamespace(**row, sort_order=index))
            if check.issues or check.warnings:
                raise ValueError(f"Team member {index}: {'; '.join(check.issues + check.warnings)}")
        digest = hashlib.sha256(json.dumps(data, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        return cls(data, digest)

    @classmethod
    def from_profile(cls, profile):
        """Fail closed if an installed version was edited outside its author route."""
        content = cls.parse(profile.content_definition)
        data = content.definition
        if content.digest != profile.content_digest or data["version"] != profile.content_version:
            raise ValueError("Gym version/fingerprint disagrees with its definition; reinstall the approved content.")
        if (profile.league_key, profile.gym_key) != (data["league_key"], data["gym_key"]):
            raise ValueError("Gym identity differs from its installed content.")
        if any(getattr(profile, key) != value for key, value in data["profile"].items()):
            raise ValueError("Gym rules differ from their installed version; reinstall or publish a new content version.")
        if any(getattr(profile.npc_trainer, key) != value for key, value in data["leader"].items()):
            raise ValueError("Gym leader differs from its installed version.")
        if any(getattr(profile.badge, key) != value for key, value in data["badge"].items()):
            raise ValueError("Gym badge differs from its installed version.")
        team = [{key: getattr(row, key) for key in TEAM_FIELDS} for row in profile.npc_trainer.pokemon_templates.order_by("sort_order", "id")]
        if team != data["team"]:
            raise ValueError("Gym roster differs from its installed version; reinstall approved content.")
        return content


def install_gym_content(definition):
    """Atomically install validated owned rows without resetting badges or receipts."""
    from django.db import connection, transaction
    from pokemon.models.trainer import GymBadge, GymLeaderProfile, NPCPokemonTemplate, NPCTrainer

    content = GymContent.parse(definition)
    data = content.definition
    with transaction.atomic():
        # Serialize first installations too, before a profile/leader row exists.
        if connection.vendor == "postgresql":
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_advisory_xact_lock(%s)", [int.from_bytes(hashlib.sha256((data["league_key"] + ":" + data["gym_key"]).encode()).digest()[:8], "big", signed=True)])
        profile = GymLeaderProfile.objects.select_for_update().filter(league_key=data["league_key"], gym_key=data["gym_key"]).first()
        if profile and (profile.badge_key != data["profile"]["badge_key"] or profile.badge.name != data["badge"]["name"] or profile.badge.region != data["badge"]["region"]):
            raise ValueError("Leader and badge identities are stable; review the existing reward before installation.")
        if profile and profile.content_version:
            old = profile.content_definition
            if data["version"] < profile.content_version or (data["version"] == profile.content_version and content.digest != profile.content_digest):
                raise ValueError("Changed content needs a higher version; downgrades and same-version replacements are refused.")
            if old["leader"]["name"] != data["leader"]["name"] or old["badge"]["name"] != data["badge"]["name"] or old["badge"]["region"] != data["badge"]["region"] or old["profile"]["badge_key"] != data["profile"]["badge_key"]:
                raise ValueError("Leader and badge identities are stable; use a new gym key for a different reward.")
        leader, created = NPCTrainer.objects.get_or_create(name=data["leader"]["name"], defaults={"description": data["leader"]["description"]})
        leader = NPCTrainer.objects.select_for_update().get(pk=leader.pk)
        if profile and profile.npc_trainer_id != leader.pk:
            raise ValueError("Gym is linked to a different leader; review the existing row before installation.")
        if not profile and not created and (leader.pokemon_templates.exists() or GymLeaderProfile.objects.filter(npc_trainer=leader).exists()):
            raise ValueError("Leader name is already in use; choose a distinct owned content identity.")
        keys = [row["template_key"] for row in data["team"]]
        if leader.pokemon_templates.exclude(template_key__in=keys).exists():
            raise ValueError("Gym has unrecognized roster rows; review them before installation (no automatic deletion).")
        for order, row in enumerate(data["team"], 1):
            if leader.pokemon_templates.filter(template_key=row["template_key"]).count() > 1:
                raise ValueError("Gym has duplicate roster keys; review them before installation.")
            NPCPokemonTemplate.objects.update_or_create(npc_trainer=leader, template_key=row["template_key"], defaults={**row, "sort_order": order})
        leader.description = data["leader"]["description"]
        leader.save(update_fields=["description"])
        if profile:
            badge = profile.badge
        else:
            if GymBadge.objects.filter(name=data["badge"]["name"], region=data["badge"]["region"]).exists():
                raise ValueError("Badge identity already exists outside this gym; review it before installation.")
            badge = GymBadge.objects.create(**data["badge"])
        for key, value in data["badge"].items():
            setattr(badge, key, value)
        badge.save()
        profile, _ = GymLeaderProfile.objects.update_or_create(league_key=data["league_key"], gym_key=data["gym_key"], defaults={
            **data["profile"], "npc_trainer": leader, "badge": badge, "content_version": data["version"],
            "content_digest": content.digest, "content_definition": data,
        })
        return profile
