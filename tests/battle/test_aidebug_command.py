import importlib
import sys
import types

from commands.admin import cmd_aidebug
from pokemon.battle.ai_profiles import AIDebugTrace


class DummyCaller:
    def __init__(self, *, battle=None, room_battles=None):
        self.key = "Staff"
        self.messages = []
        self.ndb = types.SimpleNamespace()
        self.db = types.SimpleNamespace()
        if battle is not None:
            self.ndb.battle_instance = battle
        self.location = types.SimpleNamespace(
            db=types.SimpleNamespace(),
            ndb=types.SimpleNamespace(battle_instances=room_battles or {}),
        )

    def msg(self, text):
        self.messages.append(text)


def _run_command(caller):
    cmd = cmd_aidebug.CmdAIDebugTrace()
    cmd.caller = caller
    cmd.args = ""
    cmd.func()
    return caller.messages[-1]


def _trace():
    trace = AIDebugTrace(
        profile_key="gym_leader",
        requested_profile_key="gym_leader",
        resolved_profile_key="gym_leader",
        actor_name="Squirtle",
        target_name="Charmander",
        chosen_intent="safe_damage",
    )
    trace.add_action(
        "Water Gun",
        72.5,
        "profile_weighted",
        "candidate_band_0.90",
    )
    trace.add_action("Tackle", 24.0, "neutral", "accuracy_100")
    trace.add_action("Tail Whip", 8.0, "status_baseline")
    trace.choose("Water Gun", intent="safe_damage")
    return trace


def test_aidebug_command_is_wizard_locked():
    assert cmd_aidebug.CmdAIDebugTrace.locks == "cmd:perm(Wizards)"
    assert "+aidebug/last" in cmd_aidebug.CmdAIDebugTrace.aliases


def test_aidebug_registered_in_battle_admin_cmdset(monkeypatch):
    fake_evennia = types.ModuleType("evennia")

    class BaseCommand:
        pass

    class BaseCmdSet:
        pass

    fake_evennia.Command = BaseCommand
    fake_evennia.CmdSet = BaseCmdSet
    fake_evennia.search_object = lambda *args, **kwargs: []
    monkeypatch.setitem(sys.modules, "evennia", fake_evennia)
    for name in (
        "commands.cmdsets.battle_admin",
        "commands.admin.cmd_adminbattle",
        "commands.admin.cmd_testbattle",
        "commands.admin.cmd_npcbattle",
    ):
        sys.modules.pop(name, None)

    try:
        battle_admin = importlib.import_module("commands.cmdsets.battle_admin")

        added = []
        dummy_cmdset = types.SimpleNamespace(add=lambda cmd: added.append(type(cmd)))

        battle_admin.BattleAdminCmdSet.at_cmdset_creation(dummy_cmdset)

        assert battle_admin.CmdAIDebugTrace in added
    finally:
        for name in (
            "commands.cmdsets.battle_admin",
            "commands.admin.cmd_adminbattle",
            "commands.admin.cmd_testbattle",
            "commands.admin.cmd_npcbattle",
        ):
            sys.modules.pop(name, None)


def test_aidebug_staff_can_view_last_trace_from_current_battle():
    trace = _trace()
    battle = types.SimpleNamespace(last_ai_debug_trace=trace)
    inst = types.SimpleNamespace(battle_id=88, battle=battle)
    caller = DummyCaller(battle=inst)

    text = _run_command(caller)

    assert "AI Debug Trace #88" in text
    assert "Profile: requested=`gym_leader`, resolved=`gym_leader`" in text
    assert "Actor: Squirtle" in text
    assert "Target: Charmander" in text
    assert "Intent: safe_damage" in text
    assert "Chosen Action: Water Gun" in text
    assert "Water Gun: 72.5 - profile_weighted, candidate_band_0.90" in text
    assert "candidate_band_0.90" in text
    assert "Tackle: 24.0 - neutral, accuracy_100" in text
    assert "Debug output is staff-only." in text


def test_aidebug_can_read_single_battle_in_current_room():
    trace = _trace()
    battle = types.SimpleNamespace(ai_debug_traces=[trace])
    inst = types.SimpleNamespace(battle_id=12, battle=battle)
    caller = DummyCaller(room_battles={12: inst})

    text = _run_command(caller)

    assert "AI Debug Trace #12" in text
    assert "Chosen Action: Water Gun" in text


def test_aidebug_reports_no_battle_cleanly():
    caller = DummyCaller()

    text = _run_command(caller)

    assert text == "No active battle found for you or this room."


def test_aidebug_reports_battle_without_trace_cleanly():
    inst = types.SimpleNamespace(battle_id=33, battle=types.SimpleNamespace())
    caller = DummyCaller(battle=inst)

    text = _run_command(caller)

    assert text == "No AI debug trace recorded yet for battle #33."


def test_aidebug_handles_missing_trace_fields_safely():
    battle = types.SimpleNamespace(
        last_ai_debug_trace={
            "profile_key": None,
            "chosen_action": None,
            "scores": [{"action": "Mystery", "score": None, "reasons": None}],
        }
    )
    inst = types.SimpleNamespace(battle_id=44, battle=battle)
    caller = DummyCaller(battle=inst)

    text = _run_command(caller)

    assert "Profile: requested=`none`, resolved=`unknown`" in text
    assert "Chosen Action: none" in text
    assert "Mystery: ?" in text


def test_aidebug_caps_considered_action_output():
    trace = AIDebugTrace(profile_key="trainer_basic")
    for index in range(10):
        trace.add_action(f"move_{index:02d}", float(index), "damage")
    trace.choose("move_09")
    inst = types.SimpleNamespace(
        battle_id=55,
        battle=types.SimpleNamespace(last_ai_debug_trace=trace),
    )
    caller = DummyCaller(battle=inst)

    text = _run_command(caller)

    assert "move_09: 9.0" in text
    assert "move_04: 4.0" in text
    assert "move_03: 3.0" not in text
    assert "... 4 more not shown." in text
