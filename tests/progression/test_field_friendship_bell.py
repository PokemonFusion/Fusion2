"""Pre-feed tiers and exact native held identity for the bounded Bell effect."""

from types import SimpleNamespace
import pytest

from pokemon.field_friendship import FieldFriendship


@pytest.mark.parametrize("friendship,base,bell", [(0, 10, 15), (99, 10, 15), (100, 5, 7),
                                                 (199, 5, 7), (200, 2, 3), (255, 2, 3)])
def test_pre_use_friendship_tiers_and_rounding(friendship, base, bell):
    """Only a physical exact Bell changes these positive deltas; capping is separate."""
    for item, expected in (("", base), ("Soothe Bell", bell), ("soothe-bell", bell), ("Shell Bell", base)):
        assert FieldFriendship.ev_berry_gain(SimpleNamespace(held_item=item), friendship) == expected
