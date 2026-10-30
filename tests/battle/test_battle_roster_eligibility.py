"""Roster membership differs from consciousness and never closes party holes."""

from types import SimpleNamespace

import pytest

from pokemon.battle.roster_eligibility import BattleRosterEligibility
from pokemon.helpers.party_helpers import pokemon_is_battle_member, pokemon_is_usable


@pytest.mark.parametrize("hp,egg,member,usable", [(10, False, True, True), (0, False, True, False),
                                                 (10, True, False, False), (0, True, False, False)])
def test_roster_membership_preserves_fainted_revive_targets(hp, egg, member, usable):
    """Fainted non-eggs belong in the roster; eggs never become battle actors."""
    mon = SimpleNamespace(is_egg=egg, current_hp=hp)
    assert pokemon_is_battle_member(mon) is member
    assert pokemon_is_usable(mon) is usable


def test_roster_filter_retains_source_order_without_changing_models():
    """A Fusion-first source stays first, and source holes/egg custody are untouched."""
    fusion = SimpleNamespace(current_hp=12)
    egg = SimpleNamespace(is_egg=True, current_hp=12)
    reserve = SimpleNamespace(current_hp=0)
    party = [fusion, None, egg, None, reserve]
    assert BattleRosterEligibility.models(party) == [fusion, reserve]
    assert party == [fusion, None, egg, None, reserve]
    assert egg.is_egg and egg.current_hp == 12
