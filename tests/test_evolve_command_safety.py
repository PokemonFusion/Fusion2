import importlib.util
import os
import sys
import types


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def load_cmd_learn_evolve(monkeypatch):
    fake_evennia = types.ModuleType("evennia")
    fake_evennia.Command = type("Command", (), {})
    monkeypatch.setitem(sys.modules, "evennia", fake_evennia)

    fake_suggestions = types.ModuleType("utils.dex_suggestions")
    fake_suggestions.item_not_found_message = lambda item, fallback: fallback
    fake_suggestions.suggest_name = lambda name, choices: None
    monkeypatch.setitem(sys.modules, "utils.dex_suggestions", fake_suggestions)

    fake_locks = types.ModuleType("utils.locks")
    fake_locks.require_no_battle_lock = lambda caller: True
    monkeypatch.setitem(sys.modules, "utils.locks", fake_locks)

    path = os.path.join(ROOT, "commands", "player", "cmd_learn_evolve.py")
    spec = importlib.util.spec_from_file_location("commands.player.cmd_learn_evolve", path)
    mod = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, mod)
    spec.loader.exec_module(mod)
    return mod


def install_transaction(monkeypatch, snapshotters):
    class FakeAtomic:
        def __enter__(self):
            self._restore = [snapshotter() for snapshotter in snapshotters]
            return self

        def __exit__(self, exc_type, exc, tb):
            if exc_type:
                for restore in reversed(self._restore):
                    restore()
            return False

    fake_django = types.ModuleType("django")
    fake_db = types.ModuleType("django.db")
    fake_db.transaction = types.SimpleNamespace(atomic=lambda: FakeAtomic())
    fake_django.db = fake_db
    monkeypatch.setitem(sys.modules, "django", fake_django)
    monkeypatch.setitem(sys.modules, "django.db", fake_db)


def install_evolution(monkeypatch):
    fake_evolution = types.ModuleType("pokemon.data.evolution")

    def attempt_evolution(pokemon, *, item=None):
        pokemon.species = "Ivysaur"
        pokemon.name = "Ivysaur"
        pokemon.type_ = "Grass, Poison"
        return "Ivysaur"

    fake_evolution.attempt_evolution = attempt_evolution
    monkeypatch.setitem(sys.modules, "pokemon.data.evolution", fake_evolution)


class FakePokemon:
    def __init__(self, *, fail_save=False):
        self.unique_id = "mon-1"
        self.species = "Bulbasaur"
        self.name = "Bulbasaur"
        self.type_ = "Grass"
        self.fail_save = fail_save
        self.save_calls = 0

    def save(self):
        self.save_calls += 1
        if self.fail_save:
            raise RuntimeError("pokemon save failed")


class FakeTrainer:
    def __init__(self, *, remove_result=True):
        self.items = {"stone": 1}
        self.remove_result = remove_result
        self.remove_calls = 0

    def has_item(self, item):
        return self.items.get(item, 0) > 0

    def remove_item(self, item):
        self.remove_calls += 1
        if not self.remove_result or self.items.get(item, 0) <= 0:
            return False
        self.items[item] -= 1
        return True


class FakeCaller:
    def __init__(self, pokemon, trainer):
        self.pokemon = pokemon
        self.trainer = trainer
        self.messages = []

    def msg(self, text):
        self.messages.append(text)

    def get_pokemon_by_id(self, ident):
        return self.pokemon if ident == self.pokemon.unique_id else None

    def has_item(self, item):
        return self.trainer.has_item(item)


def snapshot_pokemon(pokemon):
    species = pokemon.species
    name = pokemon.name
    type_ = pokemon.type_
    return lambda: (
        setattr(pokemon, "species", species),
        setattr(pokemon, "name", name),
        setattr(pokemon, "type_", type_),
    )


def snapshot_trainer(trainer):
    items = dict(trainer.items)
    return lambda: setattr(trainer, "items", dict(items))


def test_evolve_rolls_back_species_when_item_removal_fails(monkeypatch):
    mod = load_cmd_learn_evolve(monkeypatch)
    install_evolution(monkeypatch)
    pokemon = FakePokemon()
    trainer = FakeTrainer(remove_result=False)
    caller = FakeCaller(pokemon, trainer)
    install_transaction(monkeypatch, [lambda: snapshot_pokemon(pokemon), lambda: snapshot_trainer(trainer)])

    command = mod.CmdEvolvePokemon()
    command.caller = caller
    command.args = "mon-1 stone"
    command.func()

    assert trainer.remove_calls == 1
    assert trainer.items == {"stone": 1}
    assert pokemon.species == "Bulbasaur"
    assert pokemon.name == "Bulbasaur"
    assert pokemon.type_ == "Grass"
    assert pokemon.save_calls == 0
    assert caller.messages == ["Evolution failed; no item was consumed and the Pokemon was unchanged."]


def test_evolve_rolls_back_item_consumption_when_save_fails(monkeypatch):
    mod = load_cmd_learn_evolve(monkeypatch)
    install_evolution(monkeypatch)
    pokemon = FakePokemon(fail_save=True)
    trainer = FakeTrainer(remove_result=True)
    caller = FakeCaller(pokemon, trainer)
    install_transaction(monkeypatch, [lambda: snapshot_pokemon(pokemon), lambda: snapshot_trainer(trainer)])

    command = mod.CmdEvolvePokemon()
    command.caller = caller
    command.args = "mon-1 stone"
    command.func()

    assert trainer.remove_calls == 1
    assert trainer.items == {"stone": 1}
    assert pokemon.species == "Bulbasaur"
    assert pokemon.name == "Bulbasaur"
    assert pokemon.type_ == "Grass"
    assert pokemon.save_calls == 1
    assert caller.messages == ["Evolution failed; no item was consumed and the Pokemon was unchanged."]
