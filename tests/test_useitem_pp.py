import os
import sys
import types
import importlib.util

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)


def load_cmd_module():
    path = os.path.join(ROOT, "commands", "command.py")
    spec = importlib.util.spec_from_file_location("commands.command", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod

class FakeMove:
    objects = types.SimpleNamespace(filter=lambda **kw: [FakeMove('tackle')])

    def __init__(self, name):
        self.name = name


class FakeSlot:
    def __init__(self, move_name, slot):
        self.move = FakeMove(move_name)
        self.slot = slot
        self.current_pp = 10

    def save(self):
        pass


class FakeQS(list):
    def order_by(self, attr):
        return FakeQS(sorted(self, key=lambda s: getattr(s, attr)))

    def filter(self, **kwargs):
        if 'move' in kwargs:
            mv = kwargs['move']
            return FakeQS([s for s in self if s.move == mv])
        if 'move__name__iexact' in kwargs:
            name = kwargs['move__name__iexact'].lower()
            return FakeQS([s for s in self if s.move.name.lower() == name])
        return self

    def all(self):
        return self


class FakeBoost:
    def __init__(self, move):
        self.move = move
        self.bonus_pp = 0

    def save(self):
        pass


class BoostManager(list):
    def get_or_create(self, move, defaults=None):
        for b in self:
            if b.move.name.lower() == move.name.lower():
                return b, False
        b = FakeBoost(move)
        self.append(b)
        return b, True

    def filter(self, **kwargs):
        if 'move__name__iexact' in kwargs:
            name = kwargs['move__name__iexact'].lower()
            res = [b for b in self if b.move.name.lower() == name]
        elif 'move' in kwargs:
            mv = kwargs['move']
            res = [b for b in self if b.move == mv]
        else:
            res = list(self)
        class _QS(list):
            def first(self_inner):
                return self_inner[0] if self_inner else None
        return _QS(res)

    def all(self):
        return self


class FakePokemon:
    def __init__(self):
        self.name = 'Pika'
        self.activemoveslot_set = FakeQS([FakeSlot('tackle', 1)])
        self.pp_boosts = BoostManager()

    def get_max_pp(self, move_name):
        base = 10
        boost = next((b.bonus_pp for b in self.pp_boosts if b.move.name.lower() == move_name.lower()), 0)
        return base + boost

    def apply_pp_up(self, move_name):
        base = 10
        step = max(1, base // 5)
        max_bonus = (base * 3) // 5
        boost, _ = self.pp_boosts.get_or_create(FakeMove(move_name))
        if boost.bonus_pp >= max_bonus:
            return False
        new = min(boost.bonus_pp + step, max_bonus)
        delta = new - boost.bonus_pp
        boost.bonus_pp = new
        for s in self.activemoveslot_set.filter(move__name__iexact=move_name):
            s.current_pp += delta
        return True

    def apply_pp_max(self, move_name):
        base = 10
        max_bonus = (base * 3) // 5
        boost, _ = self.pp_boosts.get_or_create(FakeMove(move_name))
        if boost.bonus_pp >= max_bonus:
            return False
        delta = max_bonus - boost.bonus_pp
        boost.bonus_pp = max_bonus
        for s in self.activemoveslot_set.filter(move__name__iexact=move_name):
            s.current_pp += delta
        return True


class DummyTrainer:
    def __init__(self, counter):
        self.counter = counter

    def remove_item(self, name):
        self.counter[0] += 1
        return True


class DummyCaller:
    def __init__(self, poke, counter):
        self.poke = poke
        self.msgs = []
        self.ndb = types.SimpleNamespace()
        self.trainer = DummyTrainer(counter)

    def get_active_pokemon_by_slot(self, slot):
        return self.poke if slot == 1 else None

    def msg(self, text):
        self.msgs.append(text)


def setup_modules(remove_counter):
    orig_evennia = sys.modules.get('evennia')
    fake_evennia = types.ModuleType('evennia')
    fake_evennia.Command = type('Command', (), {})
    sys.modules['evennia'] = fake_evennia

    orig_core = sys.modules.get('pokemon.models.core')
    orig_moves = sys.modules.get('pokemon.models.moves')
    orig_trainer = sys.modules.get('pokemon.models.trainer')
    fake_core = types.ModuleType('pokemon.models.core')
    fake_core.OwnedPokemon = FakePokemon
    fake_moves = types.ModuleType('pokemon.models.moves')
    fake_moves.Move = FakeMove
    fake_trainer = types.ModuleType('pokemon.models.trainer')
    fake_trainer.InventoryEntry = type('InventoryEntry', (), {})
    sys.modules['pokemon.models.core'] = fake_core
    sys.modules['pokemon.models.moves'] = fake_moves
    sys.modules['pokemon.models.trainer'] = fake_trainer

    orig_inv = sys.modules.get('utils.inventory')
    fake_inv = types.ModuleType('utils.inventory')
    fake_inv.add_item = lambda *a, **k: None
    def rem(owner, name):
        remove_counter[0] += 1
        return True
    fake_inv.remove_item = rem
    sys.modules['utils.inventory'] = fake_inv

    orig_dex = sys.modules.get('pokemon.dex')
    fake_dex = types.ModuleType('pokemon.dex')
    fake_dex.ITEMDEX = {'ppup': {}, 'ppmax': {}}
    fake_dex.MOVEDEX = {'tackle': {'pp': 10}}
    sys.modules['pokemon.dex'] = fake_dex

    return orig_evennia, orig_core, orig_moves, orig_trainer, orig_inv, orig_dex


def restore_modules(orig_evennia, orig_core, orig_moves, orig_trainer, orig_inv, orig_dex):
    if orig_evennia is not None:
        sys.modules['evennia'] = orig_evennia
    else:
        sys.modules.pop('evennia', None)
    if orig_core is not None:
        sys.modules['pokemon.models.core'] = orig_core
    else:
        sys.modules.pop('pokemon.models.core', None)
    if orig_moves is not None:
        sys.modules['pokemon.models.moves'] = orig_moves
    else:
        sys.modules.pop('pokemon.models.moves', None)
    if orig_trainer is not None:
        sys.modules['pokemon.models.trainer'] = orig_trainer
    else:
        sys.modules.pop('pokemon.models.trainer', None)
    if orig_inv is not None:
        sys.modules['utils.inventory'] = orig_inv
    else:
        sys.modules.pop('utils.inventory', None)
    if orig_dex is not None:
        sys.modules['pokemon.dex'] = orig_dex
    else:
        sys.modules.pop('pokemon.dex', None)


def test_ppup_flow():
    remove_counter = [0]
    origs = setup_modules(remove_counter)
    cmd_mod = load_cmd_module()
    restore_modules(*origs)

    poke = FakePokemon()
    caller = DummyCaller(poke, remove_counter)

    cmd = cmd_mod.CmdUseItem()
    cmd.caller = caller
    cmd.args = "1=ppup"
    cmd.func()

    assert hasattr(caller.ndb, "pending_pp_item")
    assert "Choose a move" in caller.msgs[-1]

    cmd.args = "1"
    cmd.func()

    assert remove_counter[0] == 1
    boost = poke.pp_boosts.filter(move__name__iexact="tackle").first()
    assert boost and boost.bonus_pp > 0


def test_ppup_at_max():
    remove_counter = [0]
    origs = setup_modules(remove_counter)
    cmd_mod = load_cmd_module()
    restore_modules(*origs)

    poke = FakePokemon()
    # pre-boost to max
    poke.apply_pp_max("tackle")
    caller = DummyCaller(poke, remove_counter)

    cmd = cmd_mod.CmdUseItem()
    cmd.caller = caller
    cmd.args = "1=ppup"
    cmd.func()
    # choose move
    cmd.args = "1"
    cmd.func()

    # no additional removal since move already maxed
    assert remove_counter[0] == 0
    assert any("already" in m.lower() or "further" in m.lower() for m in caller.msgs)

