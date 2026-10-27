"""Reject false passes while accepting the nine diagnosed native/timing cases."""

import copy
from dataclasses import asdict
from types import SimpleNamespace

import pytest

from tests.test_live_dex_runner import observations
import live_dex_cases as cases
import live_dex_runner as runner
from pokemon.helpers.pokemon_helpers import get_max_hp, get_stats


@pytest.fixture(scope="module")
def catalog():
    """Use the actual saved-case contract and local dex definitions."""
    return {case.key: case for case in cases.catalog()}


def native_observations(case):
    """Observe a declared native entry while retaining its owned identity."""
    states = observations()
    expectation = next(item for item in case.assertions if item["type"] in {"species_identity", "active_species"})
    form = expectation.get("entry_form", expectation.get("value"))
    data = SimpleNamespace(species=form, level=case.a[0].level, ivs=[0] * 6, evs=[0] * 6, nature="Hardy")
    stats = get_stats(data)
    from pokemon import dex

    species = next(entry for _, entry in cases.unique_entries(dex.POKEDEX) if cases.key(entry.raw["name"]) == cases.key(form))
    for state in states:
        state["players"]["a"]["pokemon"][0]["species"] = case.a[0].species
        actor = state["battle"]["sides"]["A"]["active"][0]
        actor.update(species=form, types=list(species.raw["types"]), max_hp=get_max_hp(data),
                     stats={short: stats[long] for short, long in
                            {"atk": "attack", "def": "defense", "spa": "special_attack",
                             "spd": "special_defense", "spe": "speed"}.items()},
                     ability="Tera Shell" if form == "Terapagos-Terastal" else case.a[0].ability)
    return states


NATIVE_CASES = ("pokemon-castformrainy", "pokemon-castformsnowy", "pokemon-castformsunny",
                "pokemon-cherrimsunshine", "pokemon-minior", "pokemon-terapagos", "ability-terashift")


@pytest.mark.parametrize("name", NATIVE_CASES)
def test_declared_native_entry_passes(catalog, name):
    case = catalog[name]
    assert runner.evaluate(case, native_observations(case), [""])["status"] == "outcome_verified"


@pytest.mark.parametrize("name", NATIVE_CASES)
@pytest.mark.parametrize("fault", ("form", "types", "stat", "max_hp"))
def test_native_entry_does_not_accept_an_arbitrary_transition(catalog, name, fault):
    case = catalog[name]
    states = native_observations(case)
    actor = states[0]["battle"]["sides"]["A"]["active"][0]
    if fault == "form":
        actor["species"] = "Mew"
    elif fault == "types":
        actor["types"] = ["Bug"]
    elif fault == "stat":
        actor["stats"]["atk"] += 1
    else:
        actor["max_hp"] += 1
    with pytest.raises(AssertionError):
        runner.evaluate(case, states, [""])


@pytest.mark.parametrize("name", ("pokemon-terapagos", "ability-terashift"))
def test_tera_shift_requires_tera_shell(catalog, name):
    case = catalog[name]
    states = native_observations(case)
    states[0]["battle"]["sides"]["A"]["active"][0]["ability"] = "No Ability"
    with pytest.raises(AssertionError):
        runner.evaluate(case, states, [""])


def imposter_observations():
    """A copied runtime move spends temporary PP while the owned slot stays 35."""
    states = observations(spent=False)
    for index, state in enumerate(states):
        owned = state["players"]["a"]["pokemon"][0]
        owned.update(species="Ditto", moves=[{"move__name": "Tackle", "current_pp": 35}])
        actor = state["battle"]["sides"]["A"]["active"][0]
        actor.update(id="owned:a", species="Wailord", ability="No Ability",
                     runtime_moves=[{"name": "Tackle", "pp": 5 - index}])
    states[1]["battle"]["sides"]["B"]["active"][0]["hp"] = 80
    return states


def test_imposter_checks_temporary_pp_and_copied_effect(catalog):
    assert runner.evaluate(catalog["ability-imposter"], imposter_observations(), [""])["status"] == "outcome_verified"


@pytest.mark.parametrize("fault", ("no_debit", "wrong_pool", "owned_debit", "wrong_actor", "wrong_form", "wrong_ability", "no_damage"))
def test_imposter_cannot_pass_from_copy_text_or_owned_pp_alone(catalog, fault):
    states = imposter_observations()
    actor = states[-1]["battle"]["sides"]["A"]["active"][0]
    if fault == "no_debit":
        actor["runtime_moves"][0]["pp"] = 5
    elif fault == "wrong_pool":
        states[0]["battle"]["sides"]["A"]["active"][0]["runtime_moves"][0]["pp"] = 10
        actor["runtime_moves"][0]["pp"] = 9
    elif fault == "owned_debit":
        states[-1]["players"]["a"]["pokemon"][0]["moves"][0]["current_pp"] -= 1
    elif fault == "wrong_actor":
        actor["id"] = "owned:reserve"
    elif fault in {"wrong_form", "wrong_ability"}:
        states[0]["battle"]["sides"]["A"]["active"][0]["species" if fault == "wrong_form" else "ability"] = "Mew" if fault == "wrong_form" else "Blaze"
    else:
        states[-1]["battle"]["sides"]["B"]["active"][0]["hp"] = 100
    with pytest.raises(AssertionError):
        runner.evaluate(catalog["ability-imposter"], states, ["Imposter copied the foe!"])


def plasma_observations():
    """The converted attack is immune during the first turn and damages next turn."""
    states = observations(move="Plasma Fists")
    states.append(copy.deepcopy(states[-1]))
    states[-1]["battle"]["turn"] += 1
    for index, state in enumerate(states):
        state["players"]["b"]["pokemon"][0]["moves"] = [{"move__name": "Tackle", "current_pp": 10 - index}]
        state["battle"]["field"]["pseudo_weather"] = []
        state["battle"]["sides"]["B"]["active"][0].update(
            hp=80 if index else 100,
            last_executed_move={"name": "Tackle", "type": "Electric" if index == 1 else "Normal"})
    states[-1]["battle"]["sides"]["A"]["active"][0]["hp"] = 80
    return states


def test_plasma_fists_verifies_same_turn_conversion_and_expiry(catalog):
    case = catalog["move-plasmafists"]
    assert runner.evaluate(case, plasma_observations(), [""])["status"] == "outcome_verified"
    assert asdict(cases.from_dict(asdict(case))) == asdict(case)


@pytest.mark.parametrize("fault", ("no_conversion", "no_expiry", "field_leak", "missing_damage", "missing_debit"))
def test_plasma_fists_does_not_pass_on_expiry_alone(catalog, fault):
    states = plasma_observations()
    if fault == "no_conversion":
        states[1]["battle"]["sides"]["B"]["active"][0]["last_executed_move"]["type"] = "Normal"
    elif fault == "no_expiry":
        states[2]["battle"]["sides"]["B"]["active"][0]["last_executed_move"]["type"] = "Electric"
    elif fault == "field_leak":
        states[1]["battle"]["field"]["pseudo_weather"] = ["iondeluge"]
    elif fault == "missing_damage":
        for state in states:
            state["battle"]["sides"]["B"]["active"][0]["hp"] = 100
    else:
        states[2]["players"]["b"]["pokemon"][0]["moves"][0]["current_pp"] = 9
    with pytest.raises(AssertionError):
        runner.evaluate(catalog["move-plasmafists"], states, ["The field expired!"])
