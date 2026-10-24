"""Idempotent installation of the introductory Tempo strategy gym."""

from __future__ import annotations

from dataclasses import dataclass

GYM_KEY = "tempo_gym"
LEAGUE_KEY = "independent"
LEADER_NAME = "Gym Leader Cadence"
BADGE_NAME = "Tempo Badge"
CONTENT_VERSION = 1


@dataclass(frozen=True)
class ProductionGymSeedResult:
    """Return the durable profile and content version installed by this command."""

    profile: object
    version: int = CONTENT_VERSION


def seed_production_gym_content():
    """Install the authored Tempo definition through the shared content service."""
    import json
    from pathlib import Path
    from django.db import transaction
    from pokemon.models.trainer import GymLeaderProfile
    from pokemon.services.gym_content import install_gym_content

    definition = json.loads((Path(__file__).resolve().parents[2] / "world/content/gyms/tempo.json").read_text(encoding="utf-8"))
    with transaction.atomic():
        profile = install_gym_content(definition)
        GymLeaderProfile.objects.filter(league_key="alpha", gym_key="alpha_gym").update(is_enabled=False, content_stage="test")
    return ProductionGymSeedResult(profile, definition["version"])
