"""Exact reviewed Finder weights and fail-closed source selection."""

from collections import Counter
from types import SimpleNamespace

from pokemon.services.itemfinder import FinderProfile


def test_all_hundred_conditional_rolls_match_reviewed_weights():
    """Every legal weighted boundary belongs to exactly one named reward."""
    actual = Counter(FinderProfile.select(FinderProfile.training, SimpleNamespace(
        randint=lambda _low, _high, value=roll: value)) for roll in range(1, 101))
    assert actual == dict(FinderProfile.training)
    assert len(actual) == 15


def test_only_exact_training_configuration_or_legacy_potion_resolves():
    """A typo, mixed source or changed chance cannot quietly enable a fallback."""
    def read(room, key, default=None):
        return room.get(key, default)

    training = {"itemfinder_profile": "training-v1", "itemfinder_rate": 5}
    assert FinderProfile.resolve(training, read)[2] == FinderProfile.training
    for change in ({"itemfinder_profile": "training"}, {"itemfinder_rate": True},
                   {"itemfinder_rate": 100}, {"itemfinder_rate": "5"},
                   {"itemfinder_item": "Potion"}):
        assert FinderProfile.resolve(dict(training, **change), read) is None
    assert FinderProfile.resolve({"itemfinder_item": "Potion", "itemfinder_rate": 5}, read)[0] == "potion"
    assert FinderProfile.select((("Potion", 100),), None) == "Potion"
