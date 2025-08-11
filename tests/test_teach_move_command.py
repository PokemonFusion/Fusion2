import os
import sys
import types
import importlib.util

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)


def load_cmd_module():
    path = os.path.join(ROOT, "commands", "player", "cmd_learn_evolve.py")
    spec = importlib.util.spec_from_file_location("commands.player.cmd_learn_evolve", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


class DummyQS(list):
    def filter(self, **kw):
        if "name__iexact" in kw:
            name = kw["name__iexact"].lower()
            return DummyQS([m for m in self if m.name.lower() == name])
        return self

    def exists(self):
        return bool(self)

    def add(self, obj):
        self.append(obj)


class FakePokemon:
    def __init__(self):
        self.species = "pika"
        self.level = 10
        self.learned_moves = DummyQS()
        class Slots(list):
            def order_by(self, field):
                return self
            def create(self, move, slot):
                obj = types.SimpleNamespace(move=move, slot=slot)
                self.append(obj)
                return obj

        class Moveset:
            def __init__(self, index):
                self.index = index
                self.slots = Slots()

        class Manager(list):
            def order_by(self, field):
                return sorted(self, key=lambda m: m.index)
            def exists(self):
                return bool(self)
            def create(self, index):
                ms = Moveset(index)
                self.append(ms)
                return ms
            def get_or_create(self, index):
                for m in self:
                    if m.index == index:
                        return m, False
                return self.create(index), True

        self.movesets = Manager()
        ms = self.movesets.create(0)
        self.active_moveset = ms
        self.name = "Pika"
        self.saved = False
        self.applied = False

    @property
    def computed_level(self):
        return self.level

    def save(self):
        self.saved = True

    def apply_active_moveset(self):
        self.applied = True


class DummyCaller:
    def __init__(self, poke):
        self.poke = poke
        self.msgs = []

    def get_active_pokemon_by_slot(self, slot):
        return self.poke if slot == 1 else None

    def msg(self, text):
        self.msgs.append(text)


def setup_modules():
    orig_evennia = sys.modules.get("evennia")
    fake_evennia = types.ModuleType("evennia")
    fake_evennia.Command = type("Command", (), {})
    sys.modules["evennia"] = fake_evennia

    orig_pokemon = sys.modules.get("pokemon")
    orig_gen = sys.modules.get("pokemon.generation")
    orig_models_pkg = sys.modules.get("pokemon.models")
    orig_models_moves = sys.modules.get("pokemon.models.moves")
    orig_models_trainer = sys.modules.get("pokemon.models.trainer")
    orig_stats = sys.modules.get("pokemon.stats")
    orig_dex = sys.modules.get("pokemon.dex")
    orig_breeding = sys.modules.get("pokemon.breeding")
    orig_learn = sys.modules.get("pokemon.utils.move_learning")

    pokemon_pkg = types.ModuleType("pokemon")
    gen_mod = types.ModuleType("pokemon.generation")
    gen_mod.generate_pokemon = lambda *a, **k: None
    gen_mod.get_valid_moves = lambda species, lvl: ["tackle", "growl"]
    models_pkg = types.ModuleType("pokemon.models")

    class FakeMove:
        def __init__(self, name):
            self.name = name

    class Manager:
        def get_or_create(self_inner, name):
            return FakeMove(name), True

    moves_mod = types.ModuleType("pokemon.models.moves")
    moves_mod.Move = type("Move", (), {"objects": Manager()})
    trainer_mod = types.ModuleType("pokemon.models.trainer")
    trainer_mod.InventoryEntry = type("InventoryEntry", (), {})
    stats_mod = types.ModuleType("pokemon.stats")
    stats_mod.calculate_stats = lambda *a, **k: {}
    dex_mod = types.ModuleType("pokemon.dex")
    dex_mod.ITEMDEX = {}
    breeding_mod = types.ModuleType("pokemon.breeding")

    pokemon_pkg.generation = gen_mod
    pokemon_pkg.models = models_pkg
    pokemon_pkg.stats = stats_mod
    pokemon_pkg.dex = dex_mod
    pokemon_pkg.breeding = breeding_mod

    sys.modules["pokemon"] = pokemon_pkg
    sys.modules["pokemon.generation"] = gen_mod
    sys.modules["pokemon.models"] = models_pkg
    sys.modules["pokemon.models.moves"] = moves_mod
    sys.modules["pokemon.models.trainer"] = trainer_mod
    sys.modules["pokemon.stats"] = stats_mod
    sys.modules["pokemon.dex"] = dex_mod
    sys.modules["pokemon.breeding"] = breeding_mod

    learn_mod = types.ModuleType("pokemon.utils.move_learning")

    def learn_move(pokemon, move_name, caller=None, prompt=False, on_exit=None):
        ms = pokemon.active_moveset
        if len(ms.slots) < 4:
            ms.slots.append(
                types.SimpleNamespace(move=FakeMove(move_name), slot=len(ms.slots) + 1)
            )
        pokemon.save()
        pokemon.apply_active_moveset()
        if caller:
            caller.msg(f"{pokemon.name} learned {move_name}.")

    learn_mod.learn_move = learn_move
    sys.modules["pokemon.utils.move_learning"] = learn_mod

    orig_inv = sys.modules.get("utils.inventory")
    fake_inv = types.ModuleType("utils.inventory")
    fake_inv.add_item = lambda *a, **k: None
    fake_inv.remove_item = lambda *a, **k: True
    sys.modules["utils.inventory"] = fake_inv

    return (
        orig_evennia,
        orig_pokemon,
        orig_gen,
        orig_models_pkg,
        orig_models_moves,
        orig_models_trainer,
        orig_stats,
        orig_dex,
        orig_breeding,
        orig_inv,
        orig_learn,
    )


def restore_modules(
    orig_evennia,
    orig_pokemon,
    orig_gen,
    orig_models_pkg,
    orig_models_moves,
    orig_models_trainer,
    orig_stats,
    orig_dex,
    orig_breeding,
    orig_inv,
    orig_learn,
):
    if orig_evennia is not None:
        sys.modules["evennia"] = orig_evennia
    else:
        sys.modules.pop("evennia", None)
    if orig_gen is not None:
        sys.modules["pokemon.generation"] = orig_gen
    else:
        sys.modules.pop("pokemon.generation", None)
    if orig_pokemon is not None:
        sys.modules["pokemon"] = orig_pokemon
    else:
        sys.modules.pop("pokemon", None)
    if orig_gen is not None:
        sys.modules["pokemon.generation"] = orig_gen
    else:
        sys.modules.pop("pokemon.generation", None)
    if orig_models_pkg is not None:
        sys.modules["pokemon.models"] = orig_models_pkg
    else:
        sys.modules.pop("pokemon.models", None)
    if orig_models_moves is not None:
        sys.modules["pokemon.models.moves"] = orig_models_moves
    else:
        sys.modules.pop("pokemon.models.moves", None)
    if orig_models_trainer is not None:
        sys.modules["pokemon.models.trainer"] = orig_models_trainer
    else:
        sys.modules.pop("pokemon.models.trainer", None)
    if orig_stats is not None:
        sys.modules["pokemon.stats"] = orig_stats
    else:
        sys.modules.pop("pokemon.stats", None)
    if orig_dex is not None:
        sys.modules["pokemon.dex"] = orig_dex
    else:
        sys.modules.pop("pokemon.dex", None)
    if orig_breeding is not None:
        sys.modules["pokemon.breeding"] = orig_breeding
    else:
        sys.modules.pop("pokemon.breeding", None)
    if orig_inv is not None:
        sys.modules["utils.inventory"] = orig_inv
    else:
        sys.modules.pop("utils.inventory", None)
    if orig_learn is not None:
        sys.modules["pokemon.utils.move_learning"] = orig_learn
    else:
        sys.modules.pop("pokemon.utils.move_learning", None)


def test_teach_move_command():
    origs = setup_modules()
    cmd_mod = load_cmd_module()

    poke = FakePokemon()
    caller = DummyCaller(poke)

    cmd = cmd_mod.CmdTeachMove()
    cmd.caller = caller
    cmd.args = "1=tackle"
    cmd.parse()
    cmd.func()

    restore_modules(*origs)

    assert poke.saved and poke.applied
    assert any(s.move.name == "tackle" for s in poke.movesets[0].slots)
    assert caller.msgs and "learned" in caller.msgs[-1].lower()
