
class FakePokemon:
    def __init__(self, name, slot):
        self.name = name
        self.slot = slot

class FakeQuerySet(list):
    def order_by(self, field):
        assert field == "active_slots__slot"
        return FakeQuerySet(sorted(self, key=lambda p: p.slot))

class FakeM2M:
    def __init__(self, mons):
        self._mons = mons
    def all(self):
        return FakeQuerySet(self._mons)

class DummyStorage:
    def __init__(self, mons):
        self.active_pokemon = FakeM2M(mons)
    def get_party(self):
        qs = self.active_pokemon.all()
        if hasattr(qs, "order_by"):
            qs = qs.order_by("active_slots__slot")
        return list(qs)

def test_get_party_orders_by_slot():
    mons = [FakePokemon("a", 3), FakePokemon("b", 1), FakePokemon("c", 2)]
    storage = DummyStorage(mons)
    party = storage.get_party()
    assert [p.slot for p in party] == [1, 2, 3]
