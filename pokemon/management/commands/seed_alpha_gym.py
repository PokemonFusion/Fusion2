"""Seed alpha gym test content."""

from __future__ import annotations

from django.core.management.base import BaseCommand

from pokemon.services.alpha_gym_seed import (
    ALPHA_GYM_KEY,
    ALPHA_LEADER_NAME,
    ALPHA_FOLLOWER_NAME,
    seed_alpha_gym_content,
)


class Command(BaseCommand):
    """Create or update alpha gym test content."""

    help = "Create or update Alpha Gym NPCTrainer, NPCPokemonTemplate, GymBadge, and GymLeaderProfile rows."

    def handle(self, *args, **options):
        result = seed_alpha_gym_content()
        self.stdout.write(self.style.SUCCESS("Alpha gym content seeded."))
        self.stdout.write(f"Badge: {result.badge.name}")
        self.stdout.write(
            f"Follower: {ALPHA_FOLLOWER_NAME} ({len(result.follower_templates)} Pokemon)"
        )
        self.stdout.write(
            f"Leader: {ALPHA_LEADER_NAME} ({len(result.leader_templates)} Pokemon)"
        )
        self.stdout.write(f"Gym key: {ALPHA_GYM_KEY}")
        self.stdout.write("")
        self.stdout.write("Validate with:")
        self.stdout.write(f"  +npcbattle/check {ALPHA_FOLLOWER_NAME}")
        self.stdout.write(f"  +npcbattle {ALPHA_FOLLOWER_NAME}")
        self.stdout.write(f"  +gymbattle/check {ALPHA_GYM_KEY}")
        self.stdout.write(f"  +gymbattle {ALPHA_GYM_KEY}")
