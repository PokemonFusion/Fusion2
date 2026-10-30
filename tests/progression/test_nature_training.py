"""Strict mint/genetic boundaries and neutral/no-effect rules without a database."""

from types import SimpleNamespace

import pytest

from pokemon.nature_training import NatureTraining, NatureTrainingError


@pytest.mark.parametrize("name", NatureTraining.mint_names)
def test_twenty_one_values_change_only_the_effective_modifier(name):
    """The resolver leaves both saved fields intact and never repurposes IV flags."""
    mon = SimpleNamespace(nature="Hardy", trained_stat_nature=name, flags=["hypertrained:attack"])
    assert NatureTraining.effective(mon) == name
    assert mon.nature == "Hardy" and mon.trained_stat_nature == name
    assert mon.flags == ["hypertrained:attack"]


@pytest.mark.parametrize(
    "value",
    [False, 0, [], {}, "adamant", " Adamant", "Hardy", "Docile", "Bashful", "Quirky", "unknown"],
)
def test_invalid_training_does_not_silently_fall_back_to_genetics(value):
    """Malformed state cannot become a neutral/random/default stat calculation."""
    with pytest.raises(NatureTrainingError):
        NatureTraining.effective(SimpleNamespace(nature="Hardy", trained_stat_nature=value))


@pytest.mark.parametrize("nature", ["Hardy", "Docile", "Bashful", "Quirky", "Serious"])
def test_serious_is_no_effect_for_any_neutral_genetics(nature):
    """Equivalent neutral preferences never consume a mint merely to add a label."""
    mon = SimpleNamespace(nature=nature, trained_stat_nature=None)
    assert not NatureTraining.useful(mon, "Serious")


@pytest.mark.parametrize("genetic", [None, "", False, 1, "unknown"])
def test_mint_cannot_repair_or_hide_invalid_genetics(genetic):
    """Legacy blank neutral stat compatibility does not authorize a paid mint use."""
    with pytest.raises(NatureTrainingError):
        NatureTraining.useful(SimpleNamespace(nature=genetic, trained_stat_nature=None), "Adamant")


def test_same_effect_and_existing_overlay_are_resolved_before_replacement():
    """Same genetic effect has no useful change; a different explicit overlay can replace it."""
    mon = SimpleNamespace(nature="Adamant", trained_stat_nature=None)
    assert not NatureTraining.useful(mon, "Adamant")
    assert NatureTraining.useful(mon, "Modest")
    mon.trained_stat_nature = "Modest"
    assert not NatureTraining.useful(mon, "Modest")
    assert NatureTraining.useful(mon, "Adamant")


def test_legacy_blank_is_only_an_untrained_stat_read_and_is_never_written():
    """Preserve the preexisting neutral display compatibility while refusing trained blank genetics."""
    mon = SimpleNamespace(nature="", trained_stat_nature=None)
    assert NatureTraining.effective(mon) == "Hardy" and mon.nature == ""
    mon.trained_stat_nature = "Adamant"
    with pytest.raises(NatureTrainingError):
        NatureTraining.effective(mon)
