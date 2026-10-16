"""Battle checkpoints must retain an additional trainer Fusion participant."""

import pytest

from pokemon.battle.battledata import Pokemon, Team


@pytest.mark.parametrize("count", [0, 1, 6, 7])
def test_team_checkpoint_preserves_the_complete_roster(count):
    """Legacy teams stay six slots wide; the seventh participant is not truncated."""
    pokemon = [Pokemon(f"Member {i}", hp=10, max_hp=10, model_id=f"owned:{i}") for i in range(count)]
    team = Team("Trainer", pokemon)
    restored = Team.from_dict(team.to_dict())
    expected = [mon.model_id for mon in pokemon] + [None] * max(0, 6 - count)
    assert [mon.model_id if mon else None for mon in restored.returnlist()] == expected
    assert list(restored.returndict()) == list(range(1, max(6, count) + 1))
