"""Deterministic supported-pair and genetic inheritance checks against actual dex data."""

import random
from types import SimpleNamespace
from uuid import uuid4

import pytest

from pokemon.services.breeding_rules import BreedingRuleError, BreedingRules
from pokemon.names import normalize_name


def parent(species="Squirtle", *, gender="F", ability="Torrent", item="", ivs=None, nature="Hardy"):
    """Represent only stored genetic fields consumed by the pure trait planner."""
    return SimpleNamespace(pk=uuid4(), species=species, gender=gender, ability=ability,
        held_item=item, nature=nature, ivs=ivs or [0, 1, 2, 3, 4, 5], is_egg=False)


def test_ditto_pair_and_gen9_baby_do_not_require_incense():
    """Use the real compatibility helper and species/learnset data."""
    ditto = parent("Ditto", gender="N", ability="Limber")
    for species, ability, offspring in (("Pikachu", "Static", "Pichu"), ("Snorlax", "Immunity", "Munchlax")):
        child, _, _ = BreedingRules.pair(parent(species, ability=ability), ditto)
        assert child.name == offspring


def test_ditto_ditto_genders_groups_eggs_and_excluded_forms_fail_before_a_plan():
    """Unsupported families receive a refusal rather than an invented offspring."""
    ditto = parent("Ditto", gender="N", ability="Limber")
    egg = parent()
    egg.is_egg = True
    for left, right in ((ditto, parent("Ditto", gender="N", ability="Limber")),
            (parent(), parent()), (parent(), parent("Geodude", gender="M", ability="Rock Head")),
            (egg, ditto), (parent("Volbeat", gender="M", ability="Illuminate"), ditto),
            (parent("Pikachu-Partner", ability="Static"), ditto)):
        with pytest.raises(BreedingRuleError):
            BreedingRules.pair(left, right)


def test_destiny_knot_everstone_and_genetic_hyper_training_separation():
    """The trace proves five distinct inherited stats and ignores battle IV flags."""
    left = parent(item="Everstone", nature="Modest")
    right = parent(gender="M", item="Destiny Knot", ivs=[20, 21, 22, 23, 24, 25])
    from pokemon.hyper_training import HyperTraining

    left.flags = [HyperTraining.prefix + stat for stat in HyperTraining.stats]
    first = BreedingRules.plan(left, right, (["Mirror Coat"], ["Tackle"]), rng=random.Random(42))
    assert first == BreedingRules.plan(left, right, (["Mirror Coat"], ["Tackle"]), rng=random.Random(42))
    assert first["nature"] == "Modest"
    assert len(first["genetic_iv_sources"]) == 5
    for stat, source in first["genetic_iv_sources"].items():
        assert first["ivs"][int(stat)] == (left, right)[source].ivs[int(stat)]
    assert first["evs"] == [0] * 6
    assert "mirrorcoat" in {normalize_name(move) for move in first["moves"]}


def test_power_item_counts_within_destiny_knot_total():
    """A guaranteed stat does not become a sixth inherited stat."""
    left = parent(item="Power Weight", ivs=[7, 8, 9, 10, 11, 12])
    right = parent(gender="M", item="Destiny Knot", ivs=[25] * 6)
    plan = BreedingRules.plan(left, right, ([], []), rng=random.Random(8))
    assert len(plan["genetic_iv_sources"]) == 5
    assert plan["genetic_iv_sources"]["0"] == 0
    assert plan["ivs"][0] == 7


class TraitRoll:
    """Control the ability threshold while keeping other draws deterministic."""

    def __init__(self, roll):
        self.roll = roll
        self.other = random.Random(5)

    def choice(self, values):
        return self.other.choice(values)

    def sample(self, values, count):
        return self.other.sample(values, count)

    def randrange(self, stop):
        return self.other.randrange(stop)

    def random(self):
        return self.roll


def test_ordinary_and_hidden_ability_slots_use_documented_thresholds():
    """Different native names in the same slot do not substitute father/Ditto traits."""
    mother = parent("Eevee", ability="Adaptability")
    father = parent("Eevee", gender="M", ability="Run Away")
    low = BreedingRules.plan(mother, father, ([], []), rng=TraitRoll(.79))
    high = BreedingRules.plan(mother, father, ([], []), rng=TraitRoll(.81))
    assert normalize_name(low["ability"]) == "adaptability"
    assert normalize_name(high["ability"]) == "runaway"
    assert len(low["genetic_iv_sources"]) == 3
    mother.ability = "Anticipation"
    assert BreedingRules.plan(mother, father, ([], []), rng=TraitRoll(.59))["ability_slot"] == "H"
    assert BreedingRules.plan(mother, father, ([], []), rng=TraitRoll(.61))["ability_slot"] != "H"


def test_ditto_ability_never_supplies_its_hidden_slot_to_an_ordinary_parent():
    """A hidden non-Ditto parent can pass its own slot; a hidden Ditto cannot."""
    male = parent("Eevee", gender="M", ability="Run Away")
    ditto = parent("Ditto", gender="N", ability="Imposter")
    assert BreedingRules.plan(male, ditto, ([], []), rng=TraitRoll(.1))["ability_slot"] != "H"
    male.ability = "Anticipation"
    assert BreedingRules.plan(male, ditto, ([], []), rng=TraitRoll(.1))["ability_slot"] == "H"
