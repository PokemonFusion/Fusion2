"""Bounded persisted gym rules and character-scoped rematch eligibility."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from pokemon.battle.ai_profiles import AI_PROFILE_ALIASES, DEFAULT_AI_PROFILES


@dataclass(frozen=True)
class GymPolicy:
    """Validate supported configuration before creating encounter rows."""

    battle_format: str
    ai_profile: str
    strategy_key: str
    reward_policy: str
    cooldown_seconds: int
    content_stage: str

    @classmethod
    def from_profile(cls, profile):
        """Reject unknown formats/profiles/strategies rather than silently falling back."""
        battle_format = getattr(profile, "battle_format", "single")
        requested = getattr(profile, "ai_profile", "gym_leader")
        if not isinstance(requested, str):
            raise ValueError("Gym AI profile must be a supported profile key.")
        ai_profile = AI_PROFILE_ALIASES.get(requested, requested)
        strategy = getattr(profile, "strategy_key", "")
        reward = getattr(profile, "reward_policy", "legacy")
        cooldown = getattr(profile, "rematch_cooldown_seconds", 0)
        stage = getattr(profile, "content_stage", "production")
        if battle_format not in {"single", "double"} or ai_profile not in DEFAULT_AI_PROFILES:
            raise ValueError("Gym battle format or AI profile is unsupported.")
        if strategy not in {"", "trick_room"}:
            raise ValueError("Gym strategy is unsupported.")
        room_profile = DEFAULT_AI_PROFILES[ai_profile].strategy_key == "trick_room"
        if room_profile != (strategy == "trick_room"):
            raise ValueError("Trick Room configuration must use the gym_trick_room profile and strategy.")
        if strategy and battle_format != "double":
            raise ValueError("The production Trick Room strategy requires doubles.")
        if reward not in {"legacy", "badge_only"} or stage not in {"test", "production"}:
            raise ValueError("Gym reward policy or content stage is unsupported.")
        if isinstance(cooldown, bool) or not isinstance(cooldown, int) or not 0 <= cooldown <= 604800:
            raise ValueError("Gym rematch cooldown must be between zero and seven days.")
        return cls(battle_format, ai_profile, strategy, reward, cooldown, stage)

    def availability(self, profile, player, *, has_badge, now=None):
        """Block unresolved awards and enforce cooldown from the last confirmed win."""
        if player is None or self.reward_policy != "badge_only":
            return ""
        from django.utils import timezone

        from pokemon.models.gym import GymVictory
        from pokemon.services.battle_rewards import BattleRewards

        character = BattleRewards.character(player)
        if not getattr(character, "pk", None):
            return "A persistent trainer character is required for this gym."
        victories = GymVictory.objects.filter(player=character, metadata__badge_id=profile.badge_id)
        if victories.filter(claimed_at__isnull=True).exists():
            return "Your previous gym award is pending. Use +gym claim before challenging again."
        last = victories.order_by("-recorded_at").first() if has_badge else None
        if last and self.cooldown_seconds:
            until = last.recorded_at + timedelta(seconds=self.cooldown_seconds)
            remaining = (until - (now or timezone.now())).total_seconds()
            if remaining > 0:
                return f"Rematch cooldown: try again in {int(remaining) + 1} seconds."
        return ""

    def metadata(self):
        """Freeze the supported rules so later content edits cannot redirect a battle."""
        return {"battle_format": self.battle_format, "ai_profile": self.ai_profile,
                "strategy_key": self.strategy_key, "reward_policy": self.reward_policy,
                "rematch_cooldown_seconds": self.cooldown_seconds}
