from pokemon.dex import ITEMDEX


def test_medicine_items_present():
	expected = [
		"Potion",
		"Antidote",
		"Revive",
		"Ether",
		"Abilitycapsule",
		"Abilitypatch",
		"Healthfeather",
		"Rarecandy",
	]
	for item in expected:
		assert item in ITEMDEX
