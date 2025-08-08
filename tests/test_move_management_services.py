import sys
import types


def test_learn_level_up_moves_invokes_learn_move(monkeypatch):
    calls = []

    ml_mod = types.ModuleType("pokemon.utils.move_learning")

    def fake_get_moves(poke):
        return ["tackle", "growl"], {}

    def fake_learn_move(poke, name, caller=None, prompt=False):
        calls.append((poke, name, caller, prompt))

    ml_mod.get_learnable_levelup_moves = fake_get_moves
    ml_mod.learn_move = fake_learn_move
    monkeypatch.setitem(sys.modules, "pokemon.utils.move_learning", ml_mod)

    from pokemon.services.move_management import learn_level_up_moves

    poke = object()
    learn_level_up_moves(poke, caller="ash", prompt=True)

    assert calls == [(poke, "tackle", "ash", True), (poke, "growl", "ash", True)]


def test_apply_active_moveset_populates_slots(monkeypatch):
    dex_mod = types.ModuleType("pokemon.dex")
    dex_mod.MOVEDEX = {"tackle": {"pp": 35}, "growl": {"pp": 40}}
    monkeypatch.setitem(sys.modules, "pokemon.dex", dex_mod)

    tackle = types.SimpleNamespace(name="tackle")
    growl = types.SimpleNamespace(name="growl")

    class Slot:
        def __init__(self, move, slot):
            self.move = move
            self.slot = slot

    class SlotManager(list):
        def order_by(self, field):
            return sorted(self, key=lambda s: s.slot)

    class Moveset:
        def __init__(self):
            self.slots = SlotManager()

    class Boost:
        def __init__(self, move, bonus_pp):
            self.move = move
            self.bonus_pp = bonus_pp

    class BoostManager(list):
        def all(self):
            return self

    class ActiveSlotManager(list):
        def all(self):
            return self

        def delete(self):
            self.clear()

        def create(self, move, slot, current_pp=None):
            obj = types.SimpleNamespace(move=move, slot=slot, current_pp=current_pp)
            self.append(obj)
            return obj

    ms = Moveset()
    ms.slots.append(Slot(tackle, 1))
    ms.slots.append(Slot(growl, 2))

    pokemon = types.SimpleNamespace(
        active_moveset=ms,
        activemoveslot_set=ActiveSlotManager(),
        pp_boosts=BoostManager([Boost(tackle, 5)]),
        save=lambda: None,
    )

    from pokemon.services.move_management import apply_active_moveset

    apply_active_moveset(pokemon)

    assert [
        (s.move.name, s.slot, s.current_pp) for s in pokemon.activemoveslot_set
    ] == [("tackle", 1, 40), ("growl", 2, 40)]

