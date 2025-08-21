from pokemon.battle.battledata import Pokemon


def test_basic_pokemon_has_types():
	mon = Pokemon("Bulbasaur", level=5)
	assert mon.types == ["Grass", "Poison"]


def test_from_dict_populates_types():
	mon = Pokemon.from_dict({"name": "Charmander", "level": 5})
	assert mon.types == ["Fire"]
