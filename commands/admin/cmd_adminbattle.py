from __future__ import annotations

import pprint
from dataclasses import dataclass
from dataclasses import field as dc_field
from typing import Any, Dict, List, Optional, Tuple

from evennia import Command, search_object

from pokemon.battle.battleinstance import BattleSession
from pokemon.battle.handler import battle_handler
from pokemon.battle.interface import display_battle_interface
from pokemon.battle.storage import BattleDataWrapper
from utils.battle_display import render_move_gui


def _resolve_battle_context(argument: str):
    """Return the battle instance, room and id for ``argument``."""

    arg = (argument or "").strip()
    inst = None
    room = None
    bid = None
    target = None

    if not arg:
        return inst, room, bid, target

    if arg.isdigit():
        bid = int(arg)
        inst = battle_handler.instances.get(bid)
        if inst:
            room = inst.room
    else:
        targets = search_object(arg)
        if targets:
            target = targets[0]
            inst = getattr(getattr(target, "ndb", None), "battle_instance", None)
            if inst:
                bid = inst.battle_id
                room = inst.room
            else:
                bid = getattr(getattr(target, "db", None), "battle_id", None)
                room = getattr(target, "location", None)

    return inst, room, bid, target


def _strip_empty(data: Dict[str, Any]) -> Dict[str, Any]:
    """Return ``data`` without ``None`` values or empty containers."""

    return {k: v for k, v in data.items() if v is not None and v != [] and v != {}}


def _summarize_obj(obj) -> str | None:
    """Return a short human-readable description for ``obj``."""

    if not obj:
        return None
    name = getattr(obj, "key", None) or getattr(obj, "name", None)
    ident = getattr(obj, "id", None)
    if name and ident is not None:
        return f"{name} (#{ident})"
    if name:
        return str(name)
    if ident is not None:
        return f"#{ident}"
    return str(obj)


def _summarize_pokemon(pokemon) -> Dict[str, Any] | None:
    """Return a snapshot of a Pokémon's key battle attributes."""

    if not pokemon:
        return None

    moves = []
    for move in getattr(pokemon, "moves", []) or []:
        name = getattr(move, "name", None) or getattr(move, "key", None)
        if not name:
            name = str(move)
        moves.append(str(name))

    info: Dict[str, Any] = {
        "name": getattr(pokemon, "name", getattr(pokemon, "species", None)),
        "hp": getattr(pokemon, "hp", None),
        "max_hp": getattr(pokemon, "max_hp", None),
        "status": getattr(pokemon, "status", None),
        "moves": moves,
        "model_id": getattr(pokemon, "model_id", None),
    }

    ability = getattr(pokemon, "ability", None)
    if ability:
        info["ability"] = getattr(ability, "name", str(ability))

    item = getattr(pokemon, "item", None)
    if item:
        info["item"] = getattr(item, "name", str(item))

    return _strip_empty(info)


def _summarize_action(action) -> Dict[str, Any] | None:
    """Return a readable representation of a queued battle action."""

    if not action:
        return None

    data: Dict[str, Any] = {}
    a_type = getattr(action, "action_type", None)
    if a_type is not None:
        data["type"] = getattr(a_type, "name", str(a_type))
    move = getattr(action, "move", None)
    if move:
        data["move"] = getattr(move, "name", str(move))
    target = getattr(action, "target", None)
    if target:
        data["target"] = _summarize_obj(target)
    priority = getattr(action, "priority", None)
    if priority is not None:
        data["priority"] = priority
    return _strip_empty(data)


def _summarize_participant(participant) -> Dict[str, Any] | None:
    """Summarize a :class:`BattleParticipant` for debugging output."""

    if not participant:
        return None

    pokemons = [
        snap
        for snap in (
            _summarize_pokemon(poke)
            for poke in getattr(participant, "pokemons", []) or []
        )
        if snap
    ]
    active = [
        snap
        for snap in (
            _summarize_pokemon(poke)
            for poke in getattr(participant, "active", []) or []
        )
        if snap
    ]

    data: Dict[str, Any] = {
        "name": getattr(participant, "name", None),
        "team": getattr(participant, "team", None),
        "player": _summarize_obj(getattr(participant, "player", None)),
        "is_ai": getattr(participant, "is_ai", None),
        "pokemons": pokemons,
        "active": active,
    }

    pending = _summarize_action(getattr(participant, "pending_action", None))
    if pending:
        data["pending_action"] = pending

    return _strip_empty(data)


def _summarize_trainer(trainer) -> Dict[str, Any] | None:
    """Return relevant battle state stored on a trainer."""

    if not trainer:
        return None

    info: Dict[str, Any] = {"object": _summarize_obj(trainer)}

    battle_id = getattr(getattr(trainer, "db", None), "battle_id", None)
    if battle_id is not None:
        info.setdefault("db", {})["battle_id"] = battle_id

    inst = getattr(getattr(trainer, "ndb", None), "battle_instance", None)
    if inst is not None or hasattr(getattr(trainer, "ndb", None), "battle_instance"):
        ref = getattr(inst, "battle_id", None) if inst else None
        info.setdefault("ndb", {})["battle_instance"] = ref

    active = _summarize_pokemon(getattr(trainer, "active_pokemon", None))
    if active:
        info["active_pokemon"] = active

    team_members = [
        snap
        for snap in (
            _summarize_pokemon(poke)
            for poke in getattr(trainer, "team", []) or []
        )
        if snap
    ]
    if team_members:
        info["team"] = team_members

    return _strip_empty(info)


def _room_snapshot(room, battle_id: int) -> Dict[str, Any]:
    """Capture stored battle data on ``room`` for ``battle_id``."""

    info: Dict[str, Any] = {"object": _summarize_obj(room)}

    battles = getattr(getattr(room, "db", None), "battles", None)
    if battles is not None:
        info.setdefault("db", {})["battles"] = list(battles)

    storage = BattleDataWrapper(room, battle_id)
    stored: Dict[str, Any] = {}
    for part in ("data", "state", "trainers", "temp_pokemon_ids", "logic"):
        value = storage.get(part)
        if value is not None:
            stored[part] = value
    if stored:
        info["stored"] = stored

    battle_map = getattr(getattr(room, "ndb", None), "battle_instances", None)
    if isinstance(battle_map, dict):
        info.setdefault("ndb", {})["battle_instances"] = {
            str(key): _summarize_obj(val) for key, val in battle_map.items()
        }
    elif battle_map is not None:
        info.setdefault("ndb", {})["battle_instances"] = str(battle_map)

    return _strip_empty(info)


def _session_snapshot(inst) -> Dict[str, Any]:
    """Return a consolidated view of live battle session data."""

    if not inst:
        return {"present": False}

    summary: Dict[str, Any] = {
        "present": True,
        "battle_id": getattr(inst, "battle_id", None),
        "captainA": _summarize_obj(getattr(inst, "captainA", None)),
        "captainB": _summarize_obj(getattr(inst, "captainB", None)),
        "teamA": [_summarize_obj(obj) for obj in getattr(inst, "teamA", []) if obj],
        "teamB": [_summarize_obj(obj) for obj in getattr(inst, "teamB", []) if obj],
        "observers": [_summarize_obj(obj) for obj in getattr(inst, "observers", []) if obj],
        "temp_pokemon_ids": list(getattr(inst, "temp_pokemon_ids", []) or []),
    }

    state = getattr(inst, "state", None)
    if state is not None:
        summary["state_turn"] = getattr(state, "turn", None)

    battle = getattr(inst, "battle", None)
    if battle is not None:
        summary["battle_turn"] = getattr(battle, "turn_count", None)

    inst_ndb = getattr(inst, "ndb", None)
    watchers_live = getattr(inst_ndb, "watchers_live", None)
    if watchers_live:
        summary["watchers_live"] = sorted(list(watchers_live))

    logic = getattr(inst, "logic", None)
    if logic is not None:
        logic_battle = getattr(logic, "battle", None)
        if logic_battle is not None:
            summary["logic_turn"] = getattr(logic_battle, "turn_count", None)
            participants = [
                snap
                for snap in (
                    _summarize_participant(part)
                    for part in getattr(logic_battle, "participants", []) or []
                )
                if snap
            ]
            if participants:
                summary["participants"] = participants

        logic_data = getattr(logic, "data", None)
        if logic_data is not None:
            teams = getattr(logic_data, "teams", {}) or {}
            team_info: Dict[str, Any] = {}
            for key in ("A", "B"):
                team = teams.get(key)
                if not team:
                    continue
                members = [
                    snap
                    for snap in (
                        _summarize_pokemon(poke)
                        for poke in getattr(team, "returnlist", lambda: [])()
                    )
                    if snap
                ]
                if members:
                    team_info[key] = members
            if team_info:
                summary["logic_team"] = team_info

    return _strip_empty(summary)


def _battle_snapshot(inst, room, battle_id: int) -> Dict[str, Any]:
    """Construct the full snapshot dictionary for output."""

    snapshot: Dict[str, Any] = {
        "room": _room_snapshot(room, battle_id),
        "session": _session_snapshot(inst),
    }

    trainers: List[Dict[str, Any]] = []
    seen: set[int] = set()
    if inst:
        for obj in list(getattr(inst, "teamA", []) or []) + list(getattr(inst, "teamB", []) or []):
            if not obj or id(obj) in seen:
                continue
            seen.add(id(obj))
            snapshot_info = _summarize_trainer(obj)
            if snapshot_info:
                trainers.append(snapshot_info)

    if trainers:
        snapshot["trainers"] = trainers

    return snapshot


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

        inst, room, bid, target = _resolve_battle_context(self.args)
        if bid is None or room is None:
            if target is None:
                self.caller.msg("No battle data found.")
            else:
                self.caller.msg("No battle data found for that target.")
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


class CmdBattleSnapshot(Command):
    """Display stored and live battle values for comparison.

    Usage:
      +battlecheck <character or battle id>
    """

    key = "+battlecheck"
    locks = "cmd:perm(Wizards)"
    help_category = "Admin"

    def func(self):
        if not self.args:
            self.caller.msg("Usage: +battlecheck <character or battle id>")
            return

        inst, room, bid, target = _resolve_battle_context(self.args)
        if bid is None or room is None:
            if target is None:
                self.caller.msg("No battle data found.")
            else:
                self.caller.msg("No battle data found for that target.")
            return

        snapshot = _battle_snapshot(inst, room, bid)
        formatted = pprint.pformat(snapshot, indent=2, width=78, sort_dicts=False)
        self.caller.msg(f"Battle {bid} snapshot:\n{formatted}")


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


class CmdToggleDamageNumbers(Command):
    """Toggle exact damage number announcements for a battle.

    Usage:
      +damage/toggle [<character or battle id>]

    Without an argument the caller's active battle will be toggled.
    """

    key = "+damage/toggle"
    aliases = ["+damagenumbers", "+damageexact"]
    locks = "cmd:perm(Builder)"
    help_category = "Admin"

    def func(self):
        arg = (self.args or "").strip()
        inst: Optional[BattleSession] = None

        if arg:
            inst, _, bid, target = _resolve_battle_context(arg)
            if not inst:
                if target is None and bid is None:
                    self.caller.msg("No battle data found.")
                else:
                    self.caller.msg("No battle found for that target.")
                return
        else:
            inst = getattr(getattr(self.caller, "ndb", None), "battle_instance", None)
            if not inst:
                self.caller.msg("You are not currently participating in a battle.")
                return

        battle = getattr(inst, "battle", None)
        if not battle:
            self.caller.msg("Battle data is not available.")
            return

        current = getattr(battle, "show_damage_numbers", False)
        battle.show_damage_numbers = not current
        state = "enabled" if battle.show_damage_numbers else "disabled"

        # Inform the caller and other battle participants of the new state.
        self.caller.msg(
            f"Exact damage numbers {state} for battle {inst.battle_id}."
        )
        try:
            inst.msg(f"Exact damage numbers have been {state}.")
        except Exception:
            pass


class CmdUiPreview(Command):
    """Admin: preview the battle UI with mock data."""

    key = "+ui/preview"
    aliases = ["+uiprev"]
    locks = "cmd:perm(Builder)"
    help_category = "Admin"

    def parse(self):
        """Normalize switches and extract optional /team and /waiting markers."""
        super().parse()
        switches = getattr(self, "switches", None) or []
        self.switches = {s.lower() for s in switches}
        self.viewer_team = None
        self.waiting_on = None
        args = (getattr(self, "args", "") or "").strip()
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
        captain_a, captain_b = state.captainA, state.captainB
        ui = display_battle_interface(
            captain_a,
            captain_b,
            state,
            viewer_team=self.viewer_team,
            waiting_on=self.waiting_on,
        )
        caller.msg(ui)
        view_team = self.viewer_team or "A"
        active = (
            captain_a.active_pokemon
            if view_team == "A"
            else captain_b.active_pokemon
        )
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
    captainA: MockTrainer
    captainB: MockTrainer
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
    captainA = MockTrainer(name="Red", team=[mon_a], active_pokemon=mon_a)
    captainB = MockTrainer(name="Blue", team=[mon_b], active_pokemon=mon_b)
    state = MockBattleState(captainA=captainA, captainB=captainB)
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
