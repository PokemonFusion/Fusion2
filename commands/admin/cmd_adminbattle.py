from __future__ import annotations

from evennia import Command, search_object
import pprint

from pokemon.battle.battleinstance import BattleSession
from pokemon.battle.storage import BattleDataWrapper

from pokemon.battle.handler import battle_handler
from pokemon.battle.interface import display_battle_interface
from utils.battle_display import render_move_gui
from dataclasses import dataclass, field as dc_field
from typing import Any, Dict, List, Tuple


class CmdAbortBattle(Command):
    """Force end an ongoing battle.

    Usage:
      +abortbattle <character or battle id>
    """

    key = "+abortbattle"
    locks = "cmd:perm(Wizards)"
    help_category = "Admin"

    def func(self):
        if not self.args:
            self.caller.msg("Usage: +abortbattle <character or battle id>")
            return
        arg = self.args.strip()
        inst = None
        if arg.isdigit():
            inst = battle_handler.instances.get(int(arg))
            if not inst:
                self.caller.msg("No battle with that ID found.")
                return
        else:
            targets = search_object(arg)
            if not targets:
                self.caller.msg("No such character.")
                return
            target = targets[0]
            inst = getattr(target.ndb, "battle_instance", None)
            if not inst:
                self.caller.msg("They are not currently in battle.")
                return
        bid = inst.battle_id
        inst.end()
        self.caller.msg(f"Battle #{bid} aborted.")


class CmdRestoreBattle(Command):
    """Restore a saved battle in the current room for debugging.

    Usage:
      +restorebattle <battle_id>
    """

    key = "+restorebattle"
    locks = "cmd:perm(Wizards)"
    help_category = "Admin"

    def func(self):
        if not self.args:
            self.caller.msg("Usage: +restorebattle <battle_id>")
            return

        arg = self.args.strip()
        if not arg.isdigit():
            self.caller.msg("Battle ID must be numeric.")
            return

        battle_id = int(arg)
        inst = BattleSession.restore(self.caller.location, battle_id)
        if not inst:
            self.caller.msg(f"Could not restore battle {battle_id}.")
        else:
            self.caller.msg(f"Restored battle {battle_id}.")


class CmdBattleInfo(Command):
    """Display stored battle data for debugging.

    Usage:
      +battleinfo <character or battle id>
    """

    key = "+battleinfo"
    locks = "cmd:perm(Wizards)"
    help_category = "Admin"

    def func(self):
        if not self.args:
            self.caller.msg("Usage: +battleinfo <character or battle id>")
            return

        arg = self.args.strip()
        inst = None
        room = None
        bid = None

        if arg.isdigit():
            bid = int(arg)
            inst = battle_handler.instances.get(bid)
            if inst:
                room = inst.room
        else:
            targets = search_object(arg)
            if not targets:
                self.caller.msg("No such character.")
                return
            target = targets[0]
            inst = getattr(target.ndb, "battle_instance", None)
            if inst:
                bid = inst.battle_id
                room = inst.room
            else:
                bid = getattr(target.db, "battle_id", None)
                room = target.location

        if bid is None or room is None:
            self.caller.msg("No battle data found.")
            return

        storage = BattleDataWrapper(room, bid)
        parts = {
            "data": storage.get("data"),
            "state": storage.get("state"),
            "trainers": storage.get("trainers"),
            "temp_pokemon_ids": storage.get("temp_pokemon_ids"),
        }

        lines = [f"Battle {bid} info:"]
        for key, value in parts.items():
            if value is not None:
                formatted = pprint.pformat(value, indent=2, width=78)
                lines.append(f"{key.capitalize()}:\n{formatted}")

        if len(lines) == 1:
            self.caller.msg("No stored data for that battle.")
        else:
            self.caller.msg("\n".join(lines))


class CmdRetryTurn(Command):
    """Retry the current turn of a battle."""

    key = "+retryturn"
    locks = "cmd:perm(Wizards)"
    help_category = "Admin"

    def func(self):
        if not self.args:
            self.caller.msg("Usage: +retryturn <character or battle id>")
            return

        arg = self.args.strip()
        inst = None
        if arg.isdigit():
            inst = battle_handler.instances.get(int(arg))
            if not inst:
                self.caller.msg("No battle with that ID found.")
                return
        else:
            targets = search_object(arg)
            if not targets:
                self.caller.msg("No such character.")
                return
            target = targets[0]
            inst = getattr(target.ndb, "battle_instance", None)
            if not inst:
                self.caller.msg("They are not currently in battle.")
                return

        inst.run_turn()
        self.caller.msg(f"Turn retried for battle {inst.battle_id}.")


class CmdUiPreview(Command):
    """Admin: preview the battle UI with mock data."""

    key = "+ui/preview"
    aliases = ["+uiprev"]
    locks = "cmd:perm(Builder)"
    help_category = "Admin"

    def parse(self):
        self.switches = {s.lower() for s in self.switches}
        self.viewer_team = None
        self.waiting_on = None
        args = self.args.strip()
        if "/team " in args:
            part = args.split("/team ", 1)[1]
            val = (part.split(None, 1)[0] or "").upper()
            if val in ("A", "B"):
                self.viewer_team = val
        if "/waiting " in args:
            self.waiting_on = args.split("/waiting ", 1)[1].strip() or None

    def func(self):
        caller = self.caller
        state = make_mock_battle_state()
        trainerA, trainerB = state.trainerA, state.trainerB
        ui = display_battle_interface(
            trainerA,
            trainerB,
            state,
            viewer_team=self.viewer_team,
            waiting_on=self.waiting_on,
        )
        caller.msg(ui)
        view_team = self.viewer_team or "A"
        active = trainerA.active_pokemon if view_team == "A" else trainerB.active_pokemon
        slots, pp_overrides = build_moves_dict_from_active(active)
        gui = render_move_gui(slots, pp_overrides=pp_overrides)
        caller.msg("\n" + gui)


@dataclass
class MockPokemon:
    name: str
    level: int = 5
    hp: int = 20
    max_hp: int = 20
    status: str = ""
    moves: list = dc_field(default_factory=list)
    is_fainted: bool = False


@dataclass
class MockTrainer:
    name: str
    team: list
    active_pokemon: MockPokemon


@dataclass
class MockBattleState:
    trainerA: MockTrainer
    trainerB: MockTrainer
    weather: str = "Hail"
    field: str = "Electric Terrain"
    round: int = 5
    declare: dict = dc_field(default_factory=dict)
    watchers: set = dc_field(default_factory=set)


def make_mock_battle_state() -> MockBattleState:
    move_a = {"name": "Tackle", "type": "Normal", "category": "Physical", "pp": (35, 35), "power": 40, "accuracy": 100}
    move_b = {"name": "Ember", "type": "Fire", "category": "Special", "pp": (25, 25), "power": 40, "accuracy": 100}
    mon_a = MockPokemon(name="Eevee", hp=39, max_hp=55, moves=[move_a])
    mon_b = MockPokemon(name="Charmander", hp=39, max_hp=39, moves=[move_b])
    trainerA = MockTrainer(name="Red", team=[mon_a], active_pokemon=mon_a)
    trainerB = MockTrainer(name="Blue", team=[mon_b], active_pokemon=mon_b)
    state = MockBattleState(trainerA=trainerA, trainerB=trainerB)
    state.declare = {"A1": {"move": "Tackle", "target": "B1"}, "B1": {"move": "Ember", "target": "A1"}}
    return state


def build_moves_dict_from_active(active: Any) -> Tuple[List[Any], Dict[int, int]]:
    """Return move slots and PP overrides for an active Pokémon."""

    slots: List[Any] = []
    pp_overrides: Dict[int, int] = {}
    for idx, move in enumerate(getattr(active, "moves", [])[:4]):
        if isinstance(move, dict):
            pp_val = move.get("pp")
            if isinstance(pp_val, (tuple, list)):
                current, maximum = pp_val
                move = {**move, "pp": maximum}
                pp_overrides[idx] = current
            else:
                cur = move.get("current_pp")
                if cur is not None:
                    pp_overrides[idx] = cur
        else:
            cur = getattr(move, "current_pp", None)
            if cur is not None:
                pp_overrides[idx] = cur
        slots.append(move)
    return slots, pp_overrides
