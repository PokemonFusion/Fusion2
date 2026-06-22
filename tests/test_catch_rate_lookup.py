from pokemon.dex.functions import pokedex_funcs


def test_catch_rate_lookup_handles_punctuated_species_names():
	expected = {
		"Nidoran-F": 235,
		"Nidoran-M": 235,
		"Mr. Mime": 45,
		"Ho-Oh": 3,
		"Mime Jr.": 145,
		"Porygon-Z": 30,
		"Type: Null": 3,
		"Jangmo-o": 45,
		"Hakamo-o": 45,
		"Kommo-o": 45,
		"Tapu Koko": 3,
		"Mr. Rime": 45,
		"Great Tusk": 30,
		"Iron Crown": 10,
	}

	for species, catch_rate in expected.items():
		assert pokedex_funcs.get_catch_rate(species) == catch_rate


def test_catch_rate_lookup_handles_form_display_names():
	expected = {
		"Venusaur-Mega": 45,
		"Rattata-Alola": 255,
		"Mr. Mime-Galar": 45,
		"Zacian-Crowned": 10,
	}

	for species, catch_rate in expected.items():
		assert pokedex_funcs.get_catch_rate(species) == catch_rate


def test_catch_rate_lookup_handles_normalized_spellings():
	assert pokedex_funcs.get_catch_rate("greattusk") == 30
	assert pokedex_funcs.get_catch_rate("mr mime") == 45
	assert pokedex_funcs.get_catch_rate("type null") == 3
