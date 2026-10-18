"""Idempotent installation of the introductory Tempo strategy gym."""

from __future__ import annotations

from dataclasses import dataclass

GYM_KEY = "tempo_gym"
LEAGUE_KEY = "independent"
LEADER_NAME = "Gym Leader Cadence"
BADGE_NAME = "Tempo Badge"
CONTENT_VERSION = 1
ROSTER = (
    ("tempo-setter", "Slowbro", "Own Tempo", ("Trick Room", "Water Gun", "Heal Pulse", "Protect")),
    ("tempo-support", "Slowking", "Own Tempo", ("Trick Room", "Water Gun", "Recover", "Helping Hand")),
    ("tempo-anchor", "Snorlax", "Immunity", ("Tackle", "Body Slam", "Protect", "Rest")),
)
RULES = (
    "Doubles: bring at least two conscious party members. Cadence's three-Pokemon team is level 20. "
    "Trick Room reverses normal speed order for five turns; move priority still applies. "
    "Your first clear earns one Tempo Badge. Gym attempts grant no money, items, Pokemon XP, EVs or trainer XP. "
    "Losses and concessions allow immediate retries. Rematches are practice only, with a 24-hour cooldown "
    "after your last victory. Pending badge delivery must be claimed before another challenge."
)


@dataclass(frozen=True)
class ProductionGymSeedResult:
    """Return the durable profile and content version installed by this command."""

    profile: object
    version: int = CONTENT_VERSION


def seed_production_gym_content():
    """Update only this gym's owned content under one transaction and leader lock."""
    from django.db import transaction

    from pokemon.models.trainer import GymBadge, GymLeaderProfile, NPCPokemonTemplate, NPCTrainer

    with transaction.atomic():
        leader, _ = NPCTrainer.objects.get_or_create(name=LEADER_NAME)
        leader = NPCTrainer.objects.select_for_update().get(pk=leader.pk)
        profile = GymLeaderProfile.objects.filter(league_key=LEAGUE_KEY, gym_key=GYM_KEY).first()
        if profile is not None and profile.npc_trainer_id != leader.pk:
            raise ValueError("Tempo Gym is linked to a different leader; resolve that content conflict first.")
        badge = profile.badge if profile else GymBadge.objects.filter(name=BADGE_NAME, region="Independent Gyms").first()
        if badge is None:
            badge = GymBadge.objects.create(name=BADGE_NAME, region="Independent Gyms")
        badge.description = "Awarded once for mastering Cadence's Trick Room doubles challenge."
        badge.save(update_fields=["description"])
        leader.description = "Cadence teaches trainers to control the tempo of doubles battles with Trick Room."
        leader.save(update_fields=["description"])
        keys = [entry[0] for entry in ROSTER]
        if leader.pokemon_templates.exclude(template_key__in=keys).exists():
            raise ValueError("Tempo Gym has unrecognized roster rows; preserve and review them before updating.")
        for order, (key, species, ability, moves) in enumerate(ROSTER, 1):
            rows = NPCPokemonTemplate.objects.filter(npc_trainer=leader, template_key=key)
            if rows.count() > 1:
                raise ValueError("Tempo Gym has duplicate roster keys; repair those rows before updating.")
            NPCPokemonTemplate.objects.update_or_create(npc_trainer=leader, template_key=key, defaults={
                "species": species, "level": 20, "ability": ability, "nature": "Hardy", "gender": "N",
                "ivs": [0] * 6, "evs": [0] * 6, "held_item": "", "move_names": list(moves), "sort_order": order,
            })
        fields = {
            "npc_trainer": leader, "badge": badge, "badge_key": "tempo_badge", "required_badge_count": 0,
            "is_enabled": True, "sort_order": 1, "battle_format": "double", "ai_profile": "gym_trick_room",
            "strategy_key": "trick_room", "content_stage": "production", "reward_policy": "badge_only",
            "rematch_cooldown_seconds": 86400, "rules_text": RULES,
            "intro_text": f'Cadence: "Speed alone does not decide a battle. Learn to change its tempo!"\n{RULES}',
            "victory_text": 'Cadence: "You found your rhythm. Well battled!" Use +gym check tempo_gym for rematch availability.',
            "defeat_text": 'Cadence: "Watch who moves first, then choose your moment." No victory rewards were awarded. Heal your party and use +gym challenge tempo_gym to retry.',
        }
        profile, _ = GymLeaderProfile.objects.update_or_create(league_key=LEAGUE_KEY, gym_key=GYM_KEY, defaults=fields)
        GymLeaderProfile.objects.filter(league_key="alpha", gym_key="alpha_gym").update(
            is_enabled=False, content_stage="test")
        return ProductionGymSeedResult(profile)
