"""Examples proving moves, abilities, species, and held items are testable offline."""

from __future__ import annotations

from .outcome_harness import (
    MoveSpec,
    PokemonSpec,
    RandomControl,
    dex_move,
    percent_roll,
    pokemon_spec_from_dex,
    run_move_outcome,
    run_residual_outcome,
)


def test_move_status_outcome_without_live_battle():
    result = run_move_outcome(
        user=PokemonSpec(name="Caster", types=("Fire",)),
        target=PokemonSpec(name="Target", types=("Normal",)),
        move=dex_move("Will-O-Wisp", accuracy=True),
    )

    assert result.after.target.status == "brn"
    assert result.after.target.hp == result.before.target.hp
    assert result.after["target"]["status"] == "brn"


def test_ability_outcome_without_live_battle():
    result = run_move_outcome(
        user=PokemonSpec(name="Caster", types=("Water",)),
        target=PokemonSpec(
            name="Absorber",
            hp=100,
            max_hp=200,
            types=("Water",),
            ability="Water Absorb",
        ),
        move=dex_move("Water Gun", accuracy=True),
    )

    assert result.after.target.immune == "Water Absorb"
    assert result.after.target.hp == 150


def test_held_item_residual_outcome_without_live_battle():
    result = run_residual_outcome(
        user=PokemonSpec(name="Holder", hp=100, max_hp=160, item="Leftovers"),
    )

    assert result.after.user.item == "Leftovers"
    assert result.after.user.hp == 110


def test_species_data_can_feed_outcome_specs():
    steelix = pokemon_spec_from_dex("Steelix", moves=("Toxic",))

    assert steelix.name == "Steelix"
    assert "Steel" in steelix.types


def test_move_outcome_captures_damage_snapshot():
    result = run_move_outcome(
        user=PokemonSpec(name="Attacker", types=("Normal",)),
        target=PokemonSpec(name="Target", types=("Normal",)),
        move=MoveSpec(
            name="Proof Strike",
            power=40,
            type="Normal",
            category="Physical",
            accuracy=True,
            raw={"target": "normal"},
        ),
        random_control=RandomControl(
            random_values=(percent_roll(100 / 24, False),),
            randint_values=(100,),
        ),
    )

    assert result.damage[0].move_name == "Proof Strike"
    assert result.damage[0].per_hit == (28,)
    assert result.damage[0].total == 28
    assert result.damage[0].power == (40,)
