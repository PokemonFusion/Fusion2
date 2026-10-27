"""Ordinary status sources retain explicit move-type immunity requirements."""

import pytest

from .test_diagnosed_item_effects import native_battle
from .test_pending_action_effects import action


@pytest.mark.parametrize(
    "species,expected", [("Diglett", False), ("Jolteon", False), ("Wailord", True)]
)
def test_ordinary_thunder_wave_respects_ground_and_electric_targets(species, expected):
    """Ground blocks the Electric move; Electric blocks paralysis; Water can be affected."""
    battle, user, target = native_battle("Mareep", foe=species)
    battle.use_move(action(battle, user, target, "Thunder Wave"))
    assert (target.status == "par") is expected
    assert not getattr(battle, "_callback_failures", [])


def test_normal_growl_keeps_its_status_effect_against_ghost():
    """Explicit Thunder Wave immunity cannot become an accidental blanket status rule."""
    battle, user, target = native_battle(foe="Gastly")
    battle.use_move(action(battle, user, target, "Growl"))
    assert target.boosts["attack"] == -1
