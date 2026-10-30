"""Exact Gen 9 native/form egg ancestry, with missing and battle data closed."""

import pytest
from pokemon.mirror_herb import MirrorHerbRules, MirrorHerbRuleError


@pytest.mark.parametrize("species,baby,move", [
    ("Eevee", "Eevee", "wish"), ("Umbreon", "Eevee", "wish"),
    ("Pikachu", "Pichu", "fakeout"), ("Raichu-Alola", "Pichu", "wish"),
    ("Ninetales-Alola", "Vulpix-Alola", "moonblast"),
    ("Slowbro-Galar", "Slowpoke-Galar", "bellydrum"),
])
def test_native_egg_species_and_exact_generation_nine_code(species, baby, move):
    """Evolved and regional recipients use their verified exact pre-evolution chain."""
    actual, moves = MirrorHerbRules.egg_moves(species)
    assert actual == baby
    assert move in moves


def test_regional_data_cannot_fall_back_to_ordinary_species():
    """Alolan Moonblast never becomes an ordinary Vulpix/Ninetales egg move."""
    assert "moonblast" not in MirrorHerbRules.egg_moves("Ninetales")[1]
    for species in ("Missing", "MissingNo", "Syclant", "Charizard-Mega-X", "Mewtwo-Mega-Y"):
        with pytest.raises(MirrorHerbRuleError):
            MirrorHerbRules.egg_moves(species)
