from types import SimpleNamespace

from commands.player import cmd_fusion
from utils import fusion as fusion_utils


class FakePokemon:
    def __init__(self, ident, species="Pikachu", *, bond=255, exp=8000, held_item=""):
        self.unique_id = ident
        self.species = species
        self.nickname = ""
        self.name = species
        self.friendship = bond
        self.total_exp = exp
        self.level = 20
        self.held_item = held_item
        self.is_egg = False
        self.flags = []
        self.party_slot = None
        self.current_hp = 20


class FakeStorage:
    def __init__(self, pokemon=()):
        self.party = []
        for idx, mon in enumerate(pokemon, 1):
            self.add_active_pokemon(mon, idx)

    def get_party(self):
        return list(self.party)

    def add_active_pokemon(self, pokemon, slot=None):
        if pokemon in self.party:
            return
        if len(self.party) >= 6:
            raise ValueError("Party already has six Pokemon.")
        if slot is None:
            slot = len(self.party) + 1
        pokemon.party_slot = slot
        insert_at = max(0, min(slot - 1, len(self.party)))
        self.party.insert(insert_at, pokemon)
        for idx, mon in enumerate(self.party, 1):
            mon.party_slot = idx

    def remove_active_pokemon(self, pokemon):
        if pokemon in self.party:
            self.party.remove(pokemon)
        pokemon.party_slot = None
        for idx, mon in enumerate(self.party, 1):
            mon.party_slot = idx


class FakeCaller:
    key = "Tester"
    id = 1

    def __init__(self, pokemon=()):
        self.db = SimpleNamespace()
        self.messages = []
        self.storage = FakeStorage(pokemon)
        self._owned = {str(mon.unique_id): mon for mon in pokemon}

    def msg(self, text):
        self.messages.append(text)

    def get_active_pokemon_by_slot(self, slot):
        party = self.storage.get_party()
        return party[slot - 1] if 0 <= slot - 1 < len(party) else None

    def get_pokemon_by_id(self, ident):
        return self._owned.get(str(ident))


def _run(command_cls, caller, args=""):
    command = command_cls()
    command.caller = caller
    command.args = args
    command.switches = []
    command.cmdstring = command_cls.key
    command.func()
    return caller.messages[-1]


def test_fusion_command_aliases_keep_pf1_names():
    assert cmd_fusion.CmdTempFuse.key == "+fuse/temp"
    assert "+tempfuse" in cmd_fusion.CmdTempFuse.aliases
    assert cmd_fusion.CmdPermFuse.key == "+fuse/permanent"
    assert "+permfuse" in cmd_fusion.CmdPermFuse.aliases
    assert cmd_fusion.CmdUnfuse.key == "+unfuse"
    assert "+fuse/off" in cmd_fusion.CmdUnfuse.aliases
    assert cmd_fusion.CmdFusionForms.key == "+fusion"
    assert "+forms" in cmd_fusion.CmdFusionForms.aliases
    assert "+mefirst" in cmd_fusion.CmdFusionOrder.aliases
    assert "+mefight" in cmd_fusion.CmdFusionFight.aliases


def test_tempfuse_removes_pokemon_until_unfuse(monkeypatch):
    monkeypatch.setattr(cmd_fusion, "require_no_battle_lock", lambda caller: True)
    mon = FakePokemon("mon-1", bond=140)
    caller = FakeCaller([mon])

    output = _run(cmd_fusion.CmdTempFuse, caller, "slot1")

    assert "temporarily fused" in output
    assert caller.db.fusion_id == "mon-1"
    assert caller.db.fusion_kind == fusion_utils.TEMPORARY
    assert caller.storage.get_party() == []

    output = _run(cmd_fusion.CmdUnfuse, caller)

    assert "returned" in output
    assert caller.storage.get_party() == [mon]
    assert getattr(caller.db, "fusion_id", None) is None


def test_permfuse_requires_confirm_and_records_unlocked_form(monkeypatch):
    monkeypatch.setattr(cmd_fusion, "require_no_battle_lock", lambda caller: True)
    mon = FakePokemon("mon-2", species="Raichu", bond=255, exp=9000)
    caller = FakeCaller([mon])

    output = _run(cmd_fusion.CmdPermFuse, caller, "slot1")
    assert "confirm" in output
    assert caller.storage.get_party() == [mon]

    output = _run(cmd_fusion.CmdPermFuse, caller, "slot1 confirm")

    assert "permanently fused" in output
    assert caller.db.fusion_id == "mon-2"
    assert caller.db.fusion_kind == fusion_utils.PERMANENT
    assert caller.db.fusion_forms == ["mon-2"]
    assert caller.db.total_exp == 3000
    assert caller.storage.get_party() == []


def test_fusion_forms_selects_permanent_form(monkeypatch):
    monkeypatch.setattr(cmd_fusion, "require_no_battle_lock", lambda caller: True)
    mon = FakePokemon("mon-3", species="Eevee")
    caller = FakeCaller([mon])
    caller.db.fusion_forms = ["mon-3"]

    output = _run(cmd_fusion.CmdFusionForms, caller, "1")

    assert "Eevee fusion form" in output
    assert caller.db.fusion_id == "mon-3"
    assert caller.db.fusion_kind == fusion_utils.PERMANENT


def test_battle_party_includes_active_fusion_by_order():
    mon = FakePokemon("mon-4", species="Lucario", exp=8000)
    reserve = FakePokemon("mon-5", species="Bulbasaur")
    caller = FakeCaller([reserve])
    caller._owned[str(mon.unique_id)] = mon
    caller.db.fusion_id = "mon-4"
    caller.db.fusion_kind = fusion_utils.PERMANENT
    caller.db.total_exp = 8000
    caller.db.fusion_battle_order = "first"

    party = fusion_utils.get_battle_party_with_fusion(caller)

    assert party == [mon, reserve]
    assert mon._pf2_active_fusion is True
    assert mon._pf2_fusion_level >= 1
