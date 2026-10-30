"""Dex name regressions covering spaces, punctuation, accents and gender."""

import csv
from pathlib import Path
from types import SimpleNamespace

import pytest

from pokemon.names import find_named, normalize_name, resolve_dex_entry
from utils.pokedex import DexTrackerMixin


@pytest.mark.parametrize(
    ("display", "key"),
    [
        (" Water  Gun ", "watergun"),
        ("Mr. Mime", "mrmime"),
        ("Mime Jr.", "mimejr"),
        ("Type: Null", "typenull"),
        ("Farfetch’d", "farfetchd"),
        ("Flabébé", "flabebe"),
        ("Nidoran♀", "nidoranf"),
        ("Nidoran♂", "nidoranm"),
    ],
)
def test_equivalent_names_normalize_without_losing_species_identity(display, key):
    """User-facing spelling variants share the key used for identity lookup."""
    assert normalize_name(display) == key


def test_dex_lookup_accepts_dictionary_and_object_entries():
    """Both supported dex representations resolve legacy and display names."""
    move = {"name": "King's Shield", "pp": 10}
    species = SimpleNamespace(name="Mr. Mime")
    assert resolve_dex_entry({"Kingsshield": move}, "King’s Shield") is move
    assert resolve_dex_entry({"Mrmime": species}, "Mr Mime") is species
    assert resolve_dex_entry({"Mrmime": species}, "unknown") is None
    assert resolve_dex_entry({"Mrmime": species}, "") is None
    assert find_named([species], "MR.  MIME") is species


def test_pokedex_reads_legacy_spelling_and_avoids_duplicate_records():
    """Existing saved dex lists need no rewrite to accept alternate spellings."""
    tracker = DexTrackerMixin()
    tracker.db = SimpleNamespace(
        dex_seen=["mr. mime"], dex_owned=["type: null"], dex_caught=["farfetch’d"],
    )
    assert tracker.get_dex_symbol("Mrmime") == "[S]"
    assert tracker.get_dex_symbol("Type Null") == "[O]"
    assert tracker.get_dex_symbol("Farfetchd") == "[C]"
    tracker.mark_seen("MR MIME")
    assert tracker.db.dex_seen == ["mr. mime"]
    tracker.mark_caught("Nidoran♀")
    assert tracker.get_dex_symbol("Nidoran-F") == "[C]"
    assert tracker.get_dex_symbol("Nidoran-M") == ""


def test_all_loaded_species_and_moves_resolve_by_key_and_display_name():
    """Audit the entire shipped dex instead of only a few hand-picked names."""
    from pokemon.dex import MOVEDEX, POKEDEX

    for dex in (POKEDEX, MOVEDEX):
        for key, entry in dex.items():
            assert resolve_dex_entry(dex, key) is entry, key
            display = getattr(entry, "name", key)
            resolved = resolve_dex_entry(dex, display)
            assert resolved is not None, display
            assert normalize_name(getattr(resolved, "name", display)) == normalize_name(display)


def test_reward_data_covers_every_species_with_a_matching_csv_record():
    """Spaced species and forms cannot be silently omitted by reward generation."""
    from pokemon.dex import POKEDEX
    from pokemon.dex.exp_ev_yields import GAIN_INFO

    source = Path(__file__).resolve().parents[2] / "pokemon" / "data"
    with (source / "pokemon.csv").open(encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    base_exp = {normalize_name(row["identifier"]): int(row["base_experience"]) for row in rows}
    identifiers = {row["id"]: normalize_name(row["identifier"]) for row in rows}
    stats = {"1": "hp", "2": "atk", "3": "def", "4": "spa", "5": "spd", "6": "spe"}
    yields = {}
    with (source / "pokemon_stats.csv").open(encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            if int(row["effort"]):
                yields.setdefault(identifiers[row["pokemon_id"]], {})[stats[row["stat_id"]]] = int(row["effort"])
    for key in POKEDEX:
        identity = normalize_name(key)
        if identity in base_exp:
            assert GAIN_INFO[key] == {"exp": base_exp[identity], "evs": yields.get(identity, {})}, key


@pytest.mark.parametrize("name", ["Mr. Mime", "Mime Jr.", "Type: Null", "Tapu Koko", "Great Tusk", "Farfetch'd"])
def test_spaced_species_use_the_same_learnsets_and_generated_moves(name):
    """Display names must not silently fall back to Struggle or empty moves."""
    from pokemon.data.generation import choose_wild_moves, generate_pokemon, get_valid_moves
    from pokemon.middleware import get_moveset_by_name, get_pokemon_by_name

    canonical, entry = get_pokemon_by_name(name)
    assert entry is not None
    key, moveset = get_moveset_by_name(name)
    assert key == normalize_name(canonical)
    assert moveset and moveset["level-up"]
    assert get_valid_moves(name, 50) == get_valid_moves(canonical, 50)
    assert get_valid_moves(name, 50)
    assert choose_wild_moves(name, 50, seed=7) == choose_wild_moves(canonical, 50, seed=7)
    assert choose_wild_moves(name, 50, seed=7) != ["Struggle"]
    assert generate_pokemon(name, level=50).species is entry


def test_spaced_evolution_and_breeding_lookups_preserve_species_names():
    """Names at evolution and breeding boundaries use the same dex entries."""
    from pokemon.data.breeding import _lookup_species
    from pokemon.data.evolution import EvolutionContext, attempt_evolution, get_evolution
    from pokemon.dex import POKEDEX

    assert _lookup_species("Mr. Mime") is POKEDEX["Mrmime"]
    assert get_evolution("Mime Jr.", level=50) is None
    context = EvolutionContext(moves=("Mimic",))
    assert (
        get_evolution("Mime Jr.", level=50, context=context)
        == get_evolution("Mimejr", level=50, context=context)
        == "Mr. Mime"
    )
    mon = SimpleNamespace(species="Mime Jr.", name="Baby Stage", level=50, type_="")
    assert attempt_evolution(mon, context=context) == "Mr. Mime"
    assert mon.species == "Mr. Mime"
    assert mon.name == "Baby Stage"
    assert mon.type_ == "Psychic, Fairy"
