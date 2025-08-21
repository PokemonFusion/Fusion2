from pokemon.models.stats import exp_for_level, level_for_exp


class DummyManager:
	def __init__(self):
		self.created = []

	def create(self, **kwargs):
		obj = FakeOwnedPokemon(**kwargs)
		self.created.append(obj)
		return obj

	def filter(self, **kwargs):
		results = self.created
		for key, val in kwargs.items():
			attr = key.split("__")[0]
			results = [o for o in results if getattr(o, attr) == val]
		return results


class FakeOwnedPokemon:
	objects = DummyManager()

	def __init__(self, species, level=1):
		self.species = species
		self.level = level
		self.total_exp = 0

	@property
	def computed_level(self):
		return level_for_exp(self.total_exp)

	def set_level(self, lvl):
		self.total_exp = exp_for_level(lvl)
		self.level = lvl


def test_level_field_filter_after_set_level():
	FakeOwnedPokemon.objects.created.clear()
	mon = FakeOwnedPokemon.objects.create(species="Bulbasaur")
	mon.set_level(12)
	res = FakeOwnedPokemon.objects.filter(level=12)
	assert res == [mon]
	assert mon.computed_level == 12
