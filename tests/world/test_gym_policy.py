"""Pure validation of the bounded production gym configuration."""

from types import SimpleNamespace

import pytest

from pokemon.services.gym_policy import GymPolicy


def profile(**changes):
    """Construct only the policy inputs, without models or game persistence."""
    values = dict(battle_format="double", ai_profile="gym_trick_room", strategy_key="trick_room",
                  reward_policy="badge_only", rematch_cooldown_seconds=86400, content_stage="production")
    return SimpleNamespace(**(values | changes))


@pytest.mark.parametrize("changes", [
    {"battle_format": "triple"}, {"battle_format": "single"}, {"ai_profile": "unknown"},
    {"ai_profile": []}, {"ai_profile": "gym_leader"}, {"strategy_key": "weather"},
    {"strategy_key": ""}, {"reward_policy": "repeat_money"}, {"content_stage": "hidden"},
    {"rematch_cooldown_seconds": -1}, {"rematch_cooldown_seconds": True},
    {"rematch_cooldown_seconds": 604801}, {"rematch_cooldown_seconds": 1.5},
])
def test_unsupported_configuration_is_rejected(changes):
    """Invalid fields never become an implicit AI/format/reward fallback."""
    with pytest.raises(ValueError):
        GymPolicy.from_profile(profile(**changes))


def test_alias_and_frozen_policy_snapshot():
    """The strategy alias resolves explicitly and its policy snapshot is primitive."""
    source = profile(ai_profile="trick_room")
    policy = GymPolicy.from_profile(source)
    source.rematch_cooldown_seconds = 0
    assert policy.metadata() == {"battle_format": "double", "ai_profile": "gym_trick_room",
                                 "strategy_key": "trick_room", "reward_policy": "badge_only",
                                 "rematch_cooldown_seconds": 86400}


def test_existing_profiles_keep_legacy_policy_defaults():
    """Existing non-production fixtures do not acquire cooldowns or reward changes."""
    policy = GymPolicy.from_profile(SimpleNamespace())
    assert policy.reward_policy == "legacy"
    assert policy.battle_format == "single"
    assert policy.availability(None, None, has_badge=False) == ""
