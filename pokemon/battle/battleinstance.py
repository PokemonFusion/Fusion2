from __future__ import annotations

try:
    from evennia.utils.logger import log_info, log_warn, log_err
except Exception:  # pragma: no cover - fallback if Evennia not available
    import logging

    _log = logging.getLogger(__name__)

    def log_info(*args, **kwargs):
        _log.info(*args, **kwargs)

    def log_warn(*args, **kwargs):
        _log.warning(*args, **kwargs)

    def log_err(*args, **kwargs):
        _log.error(*args, **kwargs)


import random
import traceback
from typing import List, Optional

try:
    from evennia import search_object
except Exception:  # pragma: no cover - fallback for tests without Evennia

    def search_object(dbref):
        return []


from .battledata import BattleData, Team, Pokemon, Move
from .engine import Battle, BattleParticipant, BattleType
from .state import BattleState
try:
    from .interface import (
        add_watcher,
        notify_watchers,
        remove_watcher,
        display_battle_interface,
        format_turn_banner,
    )
except Exception:  # pragma: no cover - allow partial stubs in tests
    from .interface import add_watcher, notify_watchers, remove_watcher

    def display_battle_interface(*_a, **_k):
        return ""

    def format_turn_banner(turn: int) -> str:
        return f"Turn {turn}"
from .handler import battle_handler
from .storage import BattleDataWrapper
from ..generation import generate_pokemon
from world.pokemon_spawn import get_spawn
from utils.pokemon_utils import build_battle_pokemon_from_model

try:
    from typeclasses.rooms import FusionRoom
except Exception:  # pragma: no cover - allow restore in tests without module
    FusionRoom = None

try:
    from evennia import DefaultScript as _ScriptBase  # type: ignore

    if _ScriptBase is None:  # handle stubs defining this as None
        raise Exception
except Exception:  # pragma: no cover - fallback for tests without Evennia

    class _ScriptBase:
        """Minimal stand-in for Evennia's DefaultScript used in tests."""

        def stop(self):
            pass


class BattleInstance(_ScriptBase):
    """Legacy placeholder kept to clean up old script-based battles."""

    def at_script_creation(self):
        self.persistent = False

    def at_server_start(self):
        try:
            self.stop()
        except Exception:
            pass


def _calc_stats_from_model(poke):
    """Return calculated stats for a stored Pokemon model."""
    try:
        from ..stats import calculate_stats
    except Exception:  # pragma: no cover
        calculate_stats = None
    ivs = getattr(poke, "ivs", [0, 0, 0, 0, 0, 0])
    evs = getattr(poke, "evs", [0, 0, 0, 0, 0, 0])
    nature = getattr(poke, "nature", "Hardy")
    name = getattr(poke, "name", getattr(poke, "species", "Pikachu"))
    level = getattr(poke, "level", 1)
    if isinstance(ivs, list):
        ivs = {
            "hp": ivs[0],
            "atk": ivs[1],
            "def": ivs[2],
            "spa": ivs[3],
            "spd": ivs[4],
            "spe": ivs[5],
        }
    if isinstance(evs, list):
        evs = {
            "hp": evs[0],
            "atk": evs[1],
            "def": evs[2],
            "spa": evs[3],
            "spd": evs[4],
            "spe": evs[5],
        }
    try:
        if calculate_stats:
            return calculate_stats(name, level, ivs, evs, nature)
        raise Exception
    except Exception:
        inst = generate_pokemon(name, level=level)
        st = getattr(inst, "stats", inst)
        return {
            "hp": getattr(st, "hp", 100),
            "atk": getattr(st, "atk", 0),
            "def": getattr(st, "def_", 0),
            "spa": getattr(st, "spa", 0),
            "spd": getattr(st, "spd", 0),
            "spe": getattr(st, "spe", 0),
        }


def create_battle_pokemon(
    species: str,
    level: int,
    *,
    trainer: object | None = None,
    is_wild: bool = False,
) -> Pokemon:
    """Return a ``Pokemon`` battle object for the given species/level."""

    try:
        from pokemon.utils.pokemon_helpers import create_owned_pokemon
    except Exception:  # pragma: no cover - optional in tests
        create_owned_pokemon = None

    inst = generate_pokemon(species, level=level)
    move_names = getattr(inst, "moves", [])
    if not move_names:
        move_names = ["Flail"]
    moves = [Move(name=m) for m in move_names]

    ivs_list = [
        getattr(getattr(inst, "ivs", None), "hp", 0),
        getattr(getattr(inst, "ivs", None), "atk", 0),
        getattr(getattr(inst, "ivs", None), "def_", 0),
        getattr(getattr(inst, "ivs", None), "spa", 0),
        getattr(getattr(inst, "ivs", None), "spd", 0),
        getattr(getattr(inst, "ivs", None), "spe", 0),
    ]
    evs_list = [0, 0, 0, 0, 0, 0]
    nature = getattr(inst, "nature", "Hardy")

    db_obj = None
    if create_owned_pokemon:
        try:
            db_obj = create_owned_pokemon(
                inst.species.name,
                None,
                inst.level,
                gender=getattr(inst, "gender", "N"),
                nature=getattr(inst, "nature", ""),
                ability=getattr(inst, "ability", ""),
                ivs=[
                    getattr(getattr(inst, "ivs", None), "hp", 0),
                    getattr(getattr(inst, "ivs", None), "atk", 0),
                    getattr(getattr(inst, "ivs", None), "def_", 0),
                    getattr(getattr(inst, "ivs", None), "spa", 0),
                    getattr(getattr(inst, "ivs", None), "spd", 0),
                    getattr(getattr(inst, "ivs", None), "spe", 0),
                ],
                evs=[0, 0, 0, 0, 0, 0],
                ai_trainer=trainer,
                is_wild=is_wild,
            )
        except Exception:
            db_obj = None

    return Pokemon(
        name=inst.species.name,
        level=inst.level,
        hp=getattr(db_obj, "current_hp", getattr(inst.stats, "hp", level)),
        max_hp=getattr(inst.stats, "hp", level),
        moves=moves,
        ability=getattr(inst, "ability", None),
        ivs=ivs_list,
        evs=evs_list,
        nature=nature,
        model_id=str(getattr(db_obj, "unique_id", "")) if db_obj else None,
    )


def generate_wild_pokemon(location=None) -> Pokemon:
    """Generate a wild Pokémon based on the supplied location."""

    if location:
        inst = get_spawn(location)
    else:
        inst = None

    if not inst:
        species = "Pikachu"
        level = 5
    else:
        species = inst.species.name
        level = inst.level

    return create_battle_pokemon(species, level, is_wild=True)


def generate_trainer_pokemon(trainer=None) -> Pokemon:
    """Return a simple trainer-owned Charmander."""
    return create_battle_pokemon("Charmander", 5, trainer=trainer, is_wild=False)


class BattleLogic:
    """Live battle logic stored only in ``ndb``."""

    def __init__(self, battle, data, state):
        self.battle = battle
        self.data = data
        self.state = state
        battle.debug = getattr(state, "debug", False)

    def to_dict(self):
        return {
            "data": self.data.to_dict(),
            "state": self.state.to_dict(),
        }

    @classmethod
    def from_dict(cls, info):
        from .battledata import BattleData
        from .state import BattleState
        from .engine import Battle, BattleParticipant, BattleType

        data = BattleData.from_dict(info.get("data", {}))
        state = BattleState.from_dict(info.get("state", {}))

        teamA = data.teams.get("A")
        teamB = data.teams.get("B")
        try:
            part_a = BattleParticipant(
                teamA.trainer,
                [p for p in teamA.returnlist() if p],
                is_ai=False,
                team="A",
            )
        except TypeError:
            part_a = BattleParticipant(
                teamA.trainer,
                [p for p in teamA.returnlist() if p],
                is_ai=False,
            )
        try:
            part_b = BattleParticipant(
                teamB.trainer,
                [p for p in teamB.returnlist() if p],
                team="B",
            )
        except TypeError:
            part_b = BattleParticipant(
                teamB.trainer,
                [p for p in teamB.returnlist() if p],
            )
        part_b.is_ai = state.ai_type != "Player"
        pos_a = data.turndata.teamPositions("A").get("A1")
        if pos_a and pos_a.pokemon:
            part_a.active = [pos_a.pokemon]
        pos_b = data.turndata.teamPositions("B").get("B1")
        if pos_b and pos_b.pokemon:
            part_b.active = [pos_b.pokemon]
        try:
            btype = BattleType[state.ai_type.upper()]
        except KeyError:
            btype = BattleType.WILD
        battle = Battle(btype, [part_a, part_b])
        battle.turn_count = data.battle.turn
        battle.debug = getattr(state, "debug", False)
        return cls(battle, data, state)


class BattleSession:
    """Container representing an active battle in a room."""

    def __repr__(self) -> str:
        player = getattr(self.captainA, "key", getattr(self.captainA, "id", "?"))
        opp = (
            getattr(self.captainB, "key", getattr(self.captainB, "id", "?"))
            if self.captainB
            else None
        )
        return (
            f"<BattleSession id={self.battle_id} captainA={player} captainB={opp}>"
        )

    def __init__(self, player, opponent: Optional[object] = None):
        log_info(
            f"Initializing BattleSession {getattr(player, 'id', '?')} between {getattr(player, 'key', player)} and {getattr(opponent, 'key', opponent) if opponent else '<wild>'}"
        )
        self.teamA: List[object] = [player]
        self.teamB: List[object] = [opponent] if opponent else []
        self.room = getattr(player, "location", None)
        if self.room is None:
            raise ValueError("BattleSession requires the player to have a location")

        self.trainers: List[object] = self.teamA + self.teamB
        self.observers: set[object] = set()
        self.turn_state: dict = {}

        self.battle_id = getattr(player, "id", 0)
        if hasattr(player, "db"):
            player.db.battle_id = self.battle_id
        player.ndb.battle_instance = self
        if opponent:
            if hasattr(opponent, "db"):
                opponent.db.battle_id = self.battle_id
            opponent.ndb.battle_instance = self

        battle_instances = getattr(self.room.ndb, "battle_instances", None)
        if not battle_instances:
            battle_instances = {}
            self.room.ndb.battle_instances = battle_instances
        battle_instances[self.battle_id] = self

        battles = getattr(self.room.db, "battles", None) or []
        if self.battle_id not in battles:
            battles.append(self.battle_id)
        self.room.db.battles = battles

        # helper for accessing persistent battle data
        self.storage = BattleDataWrapper(self.room, self.battle_id)

        self.logic: BattleLogic | None = None
        self.watchers: set[int] = set()
        self.temp_pokemon_ids: List[int] = []

        log_info(
            f"BattleSession {self.battle_id} registered in room #{getattr(self.room, 'id', '?')}"
        )
        self._set_player_control(False)

    # ------------------------------------------------------------
    # Convenience accessors
    # ------------------------------------------------------------

    @property
    def captainA(self):
        return self.teamA[0] if self.teamA else None

    @captainA.setter
    def captainA(self, value) -> None:
        if self.teamA:
            self.teamA[0] = value
        elif value is not None:
            self.teamA.append(value)

    @property
    def captainB(self):
        return self.teamB[0] if self.teamB else None

    @captainB.setter
    def captainB(self, value) -> None:
        if self.teamB:
            if value is None:
                self.teamB = []
            else:
                self.teamB[0] = value
        elif value is not None:
            self.teamB.append(value)

    @property
    def data(self) -> BattleData | None:
        return self.logic.data if self.logic else None

    @property
    def state(self) -> BattleState | None:
        return self.logic.state if self.logic else None

    @property
    def battle(self) -> Battle | None:
        return self.logic.battle if self.logic else None

    # ------------------------------------------------------------
    # Helper utilities
    # ------------------------------------------------------------

    def _set_player_control(self, value: bool) -> None:
        """Enable or disable battle commands for all trainers."""
        for trainer in self.trainers:
            if hasattr(trainer, "db"):
                trainer.db.battle_control = value

    @staticmethod
    def ensure_for_player(player) -> "BattleSession | None":
        """Return the active battle instance for ``player`` if possible.

        This checks ``player.ndb.battle_instance`` first, then tries to
        rebuild it from persistent data on the player's room. It returns
        the instance if found, otherwise ``None``.
        """

        log_info(f"ensure_for_player called for {getattr(player, 'key', player)}")

        inst = getattr(player.ndb, "battle_instance", None)
        if inst:
            log_info(
                f"Found existing instance {getattr(inst, 'battle_id', 'N/A')} on ndb"
            )
            return inst

        room = getattr(player, "location", None)
        if not room:
            log_info(f"Player {getattr(player, 'key', player)} has no location")
            return None

        bid = getattr(player.db, "battle_id", None)
        if bid is None:
            log_info(f"Player {getattr(player, 'key', player)} has no battle_id")
            return None

        bmap = getattr(getattr(room, "ndb", None), "battle_instances", None)
        if bmap and hasattr(bmap, "get"):
            inst = bmap.get(bid)
            if inst:
                log_info(f"Reusing instance {bid} from room ndb")
                player.ndb.battle_instance = inst
                return inst

        # try restoring from persistent room data
        inst = BattleSession.restore(room, bid)
        if inst:
            log_info(f"Restored instance {bid} from room data")
            player.ndb.battle_instance = inst
        return inst

    # ------------------------------------------------------------
    # Messaging helpers
    # ------------------------------------------------------------

    def msg(self, text: str) -> None:
        """Send `text` to trainers and observers with a battle prefix."""
        if not self.trainers:
            trainers = [t for t in (self.captainA, self.captainB) if t]
        else:
            trainers = self.trainers
        names = [getattr(t, "key", str(t)) for t in trainers]
        prefix = f"[Battle: {' vs. '.join(names)}]"
        msg = f"{prefix} {text}"
        for obj in trainers + list(self.observers):
            if hasattr(obj, "msg"):
                obj.msg(msg)

    def _msg_to(self, obj, text: str) -> None:
        """Send `text` to a single object with battle prefix."""
        names = [
            getattr(self.captainA, "key", str(self.captainA)),
            getattr(self.captainB, "key", str(self.captainB))
            if self.captainB
            else None,
        ]
        names = [n for n in names if n]
        prefix = f"[Battle: {' vs. '.join(names)}]"
        if hasattr(obj, "msg"):
            obj.msg(f"{prefix} {text}")

    @classmethod
    def restore(cls, room, battle_id: int) -> "BattleSession | None":
        """Recreate an instance from a stored battle on a room."""
        log_info(
            f"Attempting restore of battle {battle_id} in room #{getattr(room, 'id', '?')}"
        )
        try:
            if FusionRoom and not isinstance(room, FusionRoom):
                log_info("Room is not a FusionRoom; skipping restore")
                return None
        except Exception as err:
            log_err(f"Room type check failed: {err}")
        storage = BattleDataWrapper(room, battle_id)
        data = storage.get("data")
        state = storage.get("state")
        if data is None and state is None and storage.get("logic") is None:
            log_info(f"No stored entry for battle {battle_id}")
            return None
        log_info("Loaded battle data and state for restore")
        if data is None or state is None:
            logic_info = storage.get("logic", {}) or {}
            data = data or logic_info.get("data")
            state = state or logic_info.get("state")
        obj = cls.__new__(cls)
        obj.teamA = []
        obj.teamB = []
        obj.room = room
        obj.battle_id = battle_id
        obj.storage = storage
        obj.trainers = []
        obj.observers = set()
        obj.turn_state = {}
        logic = BattleLogic.from_dict({"data": data, "state": state})
        obj.logic = logic
        obj.logic.battle.log_action = obj.notify
        obj.temp_pokemon_ids = list(storage.get("temp_pokemon_ids") or [])
        log_info("Restored logic and temp Pokemon ids")

        trainer_info = storage.get("trainers", {}) or {}
        teamA = trainer_info.get("teamA", [])
        teamB = trainer_info.get("teamB", [])
        player_id = teamA[0] if teamA else None
        opponent_id = teamB[0] if teamB else None

        watcher_data = getattr(obj.state, "watchers", None) or set()
        if player_id:
            watcher_data.add(player_id)
        if opponent_id:
            watcher_data.add(opponent_id)
        obj.state.watchers = watcher_data

        team_a_objs = []
        for tid in teamA:
            targets = search_object(f"#{tid}")
            if targets:
                member = targets[0]
                team_a_objs.append(member)
                if obj.captainA is None:
                    obj.captainA = member
        team_b_objs = []
        for tid in teamB:
            targets = search_object(f"#{tid}")
            if targets:
                member = targets[0]
                team_b_objs.append(member)
                if obj.captainB is None:
                    obj.captainB = member
        obj.teamA = team_a_objs
        obj.teamB = team_b_objs

        # expose battle info on trainers for the interface
        try:
            if obj.captainA:
                obj.captainA.team = [p for p in obj.logic.data.teams["A"].returnlist() if p]
                part_a = obj.logic.battle.participants[0]
                if part_a.active:
                    obj.captainA.active_pokemon = part_a.active[0]
            if obj.captainB:
                obj.captainB.team = [p for p in obj.logic.data.teams["B"].returnlist() if p]
                if len(obj.logic.battle.participants) > 1:
                    part_b = obj.logic.battle.participants[1]
                    if part_b.active:
                        obj.captainB.active_pokemon = part_b.active[0]
        except Exception:
            pass

        watcher_data = getattr(obj.state, "watchers", None) or set()
        obj.watchers = set(watcher_data)
        obj.watchers.update(teamA)
        obj.watchers.update(teamB)
        for wid in obj.watchers:
            log_info(f"Restoring watcher {wid}")
            if wid in teamA and team_a_objs:
                watcher = next((w for w in team_a_objs if getattr(w, 'id', 0) == wid), None)
            elif wid in teamB and team_b_objs:
                watcher = next((w for w in team_b_objs if getattr(w, 'id', 0) == wid), None)
            else:
                targets = search_object(f"#{wid}")
                if not targets:
                    log_info(f"Could not find watcher {wid}")
                    continue
                watcher = targets[0]
            watcher.ndb.battle_instance = obj
            if hasattr(watcher, "db"):
                watcher.db.battle_id = battle_id
            if wid in teamA:
                if obj.captainA is None:
                    obj.captainA = watcher
                if watcher not in team_a_objs:
                    team_a_objs.append(watcher)
                obj.trainers.append(watcher)
            elif wid in teamB:
                if obj.captainB is None:
                    obj.captainB = watcher
                if watcher not in team_b_objs:
                    team_b_objs.append(watcher)
                obj.trainers.append(watcher)
            else:
                obj.observers.add(watcher)
        if obj.captainA or obj.captainB:
            obj.trainers = team_a_objs + team_b_objs
        else:
            obj.trainers = []
        obj.teamA = team_a_objs
        obj.teamB = team_b_objs

        log_info(
            f"Restore complete: player={getattr(obj.captainA, 'key', obj.captainA)} "
            f"opponent={getattr(obj.captainB, 'key', obj.captainB) if obj.captainB else None} "
            f"observers={len(obj.observers)}"
        )

        battle_instances = getattr(room.ndb, "battle_instances", None)
        if not battle_instances or not hasattr(battle_instances, "__setitem__"):
            battle_instances = {}
            room.ndb.battle_instances = battle_instances
        battle_instances[battle_id] = obj
        log_info("Registered restored instance in room ndb")
        battles = getattr(room.db, "battles", None) or []
        if battle_id not in battles:
            battles.append(battle_id)
        room.db.battles = battles
        log_info(f"Recorded battle {battle_id} in room.db.battles")

        # ensure restored battles remain tracked across further reloads
        try:
            from .handler import battle_handler

            battle_handler.register(obj)
        except Exception:
            pass

        return obj

    def start(self) -> None:
        """Start a battle against a wild Pokémon, trainer or another player."""
        log_info(
            f"Starting battle {self.battle_id} in room #{getattr(self.room, 'id', '?')}"
        )
        # make sure this battle's ID is tracked on the room
        room = self.captainA.location
        battle_id = self.battle_id
        existing_ids = getattr(room.db, "battles", None) or []
        if battle_id not in existing_ids:
            existing_ids.append(battle_id)
            room.db.battles = existing_ids

        if self.captainB:
            log_info("Opponent present, starting PvP")
            self.start_pvp()
            return

        origin = getattr(self.captainA, "location", None)
        opponent_poke, opponent_name, battle_type = self._select_opponent()
        player_pokemon = self._prepare_player_party(self.captainA)
        log_info(f"Prepared player party with {len(player_pokemon)} pokemon")
        self._init_battle_state(
            origin, player_pokemon, opponent_poke, opponent_name, battle_type
        )
        self._setup_battle_room()

    def start_pvp(self) -> None:
        """Start a battle between two players."""
        if not self.captainB:
            return

        origin = getattr(self.captainA, "location", None)

        log_info(
            f"Initializing PvP battle {self.battle_id} between {self.captainA.key} and {self.captainB.key}"
        )

        player_pokemon = self._prepare_player_party(self.captainA, full_heal=True)

        opp_pokemon = self._prepare_player_party(self.captainB)

        try:
            player_participant = BattleParticipant(
                self.captainA.key,
                player_pokemon,
                player=self.captainA,
                team="A",
            )
        except TypeError:
            try:
                player_participant = BattleParticipant(
                    self.captainA.key, player_pokemon, team="A"
                )
            except TypeError:
                player_participant = BattleParticipant(
                    self.captainA.key, player_pokemon
                )
        try:
            opponent_participant = BattleParticipant(
                self.captainB.key,
                opp_pokemon,
                player=self.captainB,
                team="B",
            )
        except TypeError:
            try:
                opponent_participant = BattleParticipant(
                    self.captainB.key, opp_pokemon, team="B"
                )
            except TypeError:
                opponent_participant = BattleParticipant(
                    self.captainB.key, opp_pokemon
                )

        if player_participant.pokemons:
            player_participant.active = [player_participant.pokemons[0]]
        if opponent_participant.pokemons:
            opponent_participant.active = [opponent_participant.pokemons[0]]

        battle = Battle(BattleType.PVP, [player_participant, opponent_participant])

        teamA = Team(trainer=self.captainA.key, pokemon_list=player_pokemon)
        teamB = Team(trainer=self.captainB.key, pokemon_list=opp_pokemon)
        data = BattleData(teamA, teamB)

        state = BattleState.from_battle_data(data, ai_type=BattleType.PVP.name)
        state.roomweather = getattr(getattr(origin, "db", {}), "weather", "clear")
        state.pokemon_control = {}
        for poke in player_pokemon:
            if getattr(poke, "model_id", None):
                state.pokemon_control[str(poke.model_id)] = str(self.captainA.id)
        for poke in opp_pokemon:
            if getattr(poke, "model_id", None) and self.captainB:
                state.pokemon_control[str(poke.model_id)] = str(self.captainB.id)

        self.logic = BattleLogic(battle, data, state)
        self.logic.battle.log_action = self.notify
        log_info("PvP battle objects created")

        # expose battle info on trainers for the interface
        try:
            self.captainA.team = player_pokemon
            self.captainB.team = opp_pokemon
            if player_participant.active:
                self.captainA.active_pokemon = player_participant.active[0]
            if opponent_participant.active:
                self.captainB.active_pokemon = opponent_participant.active[0]
        except Exception:
            pass

        # persist battle info on the room
        self.storage.set("data", self.logic.data.to_dict())
        self.storage.set("state", self.logic.state.to_dict())
        self.storage.set("temp_pokemon_ids", list(self.temp_pokemon_ids))
        trainer_ids = {}
        if hasattr(self.captainA, "id"):
            trainer_ids.setdefault("teamA", []).append(self.captainA.id)
        if self.captainB and hasattr(self.captainB, "id"):
            trainer_ids.setdefault("teamB", []).append(self.captainB.id)
        if trainer_ids:
            self.storage.set("trainers", trainer_ids)
        log_info("Saved PvP battle data to room")

        add_watcher(self.state, self.captainA)
        add_watcher(self.state, self.captainB)
        self.watchers.update({self.captainA.id, self.captainB.id})
        self.captainA.ndb.battle_instance = self
        self.captainB.ndb.battle_instance = self
        if hasattr(self.captainA, "db"):
            self.captainA.db.battle_id = self.battle_id
        if hasattr(self.captainB, "db"):
            self.captainB.db.battle_id = self.battle_id
        self.msg("PVP battle started!")
        self.msg(f"Battle ID: {self.battle_id}")
        log_info(f"PvP battle {self.battle_id} started")
        notify_watchers(
            self.state,
            f"{self.captainA.key} and {self.captainB.key} begin a battle!",
            room=self.room,
        )

        if self.battle and hasattr(self.battle, "start_turn"):
            self.battle.start_turn()

        self.prompt_next_turn()
        battle_handler.register(self)
        log_info(f"PvP battle {self.battle_id} registered with handler")

    # ------------------------------------------------------------------
    # Helper methods extracted from ``start``
    # ------------------------------------------------------------------
    def _select_opponent(self) -> tuple[Pokemon, str, BattleType]:
        """Return the opponent Pokemon, its name and the battle type."""
        opponent_kind = random.choice(["pokemon", "trainer"])
        log_info(f"Selecting opponent: {opponent_kind}")
        if opponent_kind == "pokemon":
            opponent_poke = generate_wild_pokemon(self.captainA.location)
            if getattr(opponent_poke, "model_id", None):
                self.temp_pokemon_ids.append(opponent_poke.model_id)
            battle_type = BattleType.WILD
            opponent_name = "Wild"
            self.msg(f"A wild {opponent_poke.name} appears!")
            log_info(f"Wild opponent {opponent_poke.name} generated")
        else:
            opponent_poke = generate_trainer_pokemon()
            if getattr(opponent_poke, "model_id", None):
                self.temp_pokemon_ids.append(opponent_poke.model_id)
            battle_type = BattleType.TRAINER
            opponent_name = "Trainer"
            self.msg(f"A trainer challenges you with {opponent_poke.name}!")
            log_info(f"Trainer opponent {opponent_poke.name} generated")
        return opponent_poke, opponent_name, battle_type

    def _prepare_player_party(self, trainer, full_heal: bool = False) -> List[Pokemon]:
        """Return a list of battle-ready Pokemon for a trainer.

        If ``full_heal`` is ``True`` the Pokémon start with full HP regardless
        of any stored current HP value. This mirrors the behaviour used when
        starting PvP battles where all participant Pokémon begin at full health.
        """
        log_info(
            f"Preparing party for {getattr(trainer, 'key', trainer)} (full_heal={full_heal})"
        )
        party = (
            trainer.storage.get_party()
            if hasattr(trainer.storage, "get_party")
            else list(trainer.storage.active_pokemon.all())
        )
        pokemons: List[Pokemon] = []
        for poke in party:
            battle_poke = build_battle_pokemon_from_model(poke, full_heal=full_heal)
            pokemons.append(battle_poke)
            log_info(f"Prepared {battle_poke.name} lvl {battle_poke.level}")
        log_info(
            f"Prepared {len(pokemons)} pokemons for {getattr(trainer, 'key', trainer)}"
        )
        return pokemons

    def _init_battle_state(
        self,
        origin,
        player_pokemon: List[Pokemon],
        opponent_poke: Pokemon,
        opponent_name: str,
        battle_type: BattleType,
    ) -> None:
        """Create battle objects and state."""
        log_info(f"Initializing battle state for {self.captainA.key} vs {opponent_name}")
        # ``BattleParticipant`` may not accept ``team`` or ``player`` in stub
        # implementations used by tests. Attempt to pass these keyword
        # arguments when available and gracefully fall back otherwise.
        try:
            opponent_participant = BattleParticipant(
                opponent_name, [opponent_poke], is_ai=True, team="B"
            )
        except TypeError:
            opponent_participant = BattleParticipant(
                opponent_name, [opponent_poke], is_ai=True
            )
        try:
            player_participant = BattleParticipant(
                self.captainA.key,
                player_pokemon,
                player=self.captainA,
                team="A",
            )
        except TypeError:
            try:
                player_participant = BattleParticipant(
                    self.captainA.key, player_pokemon, team="A"
                )
            except TypeError:
                player_participant = BattleParticipant(
                    self.captainA.key, player_pokemon
                )

        if player_participant.pokemons:
            player_participant.active = [player_participant.pokemons[0]]
        if opponent_participant.pokemons:
            opponent_participant.active = [opponent_participant.pokemons[0]]

        battle = Battle(battle_type, [player_participant, opponent_participant])

        player_team = Team(trainer=self.captainA.key, pokemon_list=player_pokemon)
        opponent_team = Team(trainer=opponent_name, pokemon_list=[opponent_poke])
        data = BattleData(player_team, opponent_team)

        state = BattleState.from_battle_data(data, ai_type=battle_type.name)
        state.roomweather = getattr(getattr(origin, "db", {}), "weather", "clear")
        state.pokemon_control = {}
        for poke in player_pokemon:
            if getattr(poke, "model_id", None):
                owner_id = getattr(self.captainA, "id", getattr(self.captainA, "key", None))
                if owner_id is not None:
                    state.pokemon_control[str(poke.model_id)] = str(owner_id)
        if getattr(opponent_poke, "model_id", None) and self.captainB:
            owner_id = getattr(self.captainB, "id", getattr(self.captainB, "key", None))
            if owner_id is not None:
                state.pokemon_control[str(opponent_poke.model_id)] = str(owner_id)

        self.logic = BattleLogic(battle, data, state)
        self.logic.battle.log_action = self.notify
        log_info(f"Battle logic created with {len(player_pokemon)} player pokemon")

        # expose battle info on trainers for the interface
        try:
            self.captainA.team = player_pokemon
            if player_participant.active:
                self.captainA.active_pokemon = player_participant.active[0]
        except Exception:
            pass

        # store battle info for restoration
        self.storage.set("data", self.logic.data.to_dict())
        self.storage.set("state", self.logic.state.to_dict())
        self.storage.set("temp_pokemon_ids", list(self.temp_pokemon_ids))
        trainer_ids = {}
        if hasattr(self.captainA, "id"):
            trainer_ids.setdefault("teamA", []).append(self.captainA.id)
        if self.captainB and hasattr(self.captainB, "id"):
            trainer_ids.setdefault("teamB", []).append(self.captainB.id)
        if trainer_ids:
            self.storage.set("trainers", trainer_ids)
        log_info(f"Saved battle data for id {self.battle_id}")

    def _setup_battle_room(self) -> None:
        """Move players to the battle room and notify watchers."""
        log_info(f"Setting up battle room for {self.battle_id}")
        add_watcher(self.state, self.captainA)
        if hasattr(self.captainA, "id"):
            self.watchers.add(self.captainA.id)
        self.captainA.ndb.battle_instance = self
        if hasattr(self.captainA, "db"):
            self.captainA.db.battle_id = self.battle_id
        self.msg("Battle started!")
        self.msg(f"Battle ID: {self.battle_id}")
        notify_watchers(
            self.state,
            f"{getattr(self.captainA, 'key', 'Player')} has entered battle!",
            room=self.room,
        )

        if self.battle and hasattr(self.battle, "start_turn"):
            self.battle.start_turn()

        self.prompt_next_turn()
        battle_handler.register(self)
        log_info(f"Battle {self.battle_id} registered with handler")

    def end(self) -> None:
        """End the battle and clean up."""
        log_info(f"Ending battle {self.battle_id}")
        self._set_player_control(False)
        try:
            from ..models import OwnedPokemon
        except Exception:  # pragma: no cover
            OwnedPokemon = None
        for pid in getattr(self, "temp_pokemon_ids", []):
            try:
                if OwnedPokemon:
                    poke = OwnedPokemon.objects.get(unique_id=pid)
                    poke.delete_if_wild()
            except Exception:
                pass
        if OwnedPokemon:
            OwnedPokemon.objects.filter(
                is_battle_instance=True,
                battleslot__fainted=True,
            ).delete()
        self.temp_pokemon_ids.clear()
        if self.room:
            if hasattr(self.room.ndb, "battle_instances"):
                self.room.ndb.battle_instances.pop(self.battle_id, None)
                if not self.room.ndb.battle_instances:
                    del self.room.ndb.battle_instances
                log_info("Removed battle_instances map from room")
            for part in ["logic", "trainers", "temp_pokemon_ids"]:
                self.storage.delete(part)
            battles = getattr(self.room.db, "battles", None)
            if battles and self.battle_id in battles:
                battles.remove(self.battle_id)
                if battles:
                    self.room.db.battles = battles
                else:
                    delattr(self.room.db, "battles")
        for trainer in list(self.teamA) + list(self.teamB):
            if getattr(getattr(trainer, "ndb", None), "battle_instance", None):
                del trainer.ndb.battle_instance
            if hasattr(trainer, "db") and hasattr(trainer.db, "battle_id"):
                del trainer.db.battle_id
        self.logic = None
        if self.state:
            notify_watchers(self.state, "The battle has ended.", room=self.room)
        self.watchers.clear()
        battle_handler.unregister(self)
        for seg in ("data", "state", "meta", "field", "active"):
            self.storage.delete(seg)
        log_info(f"Cleared battle data for {self.battle_id}")
        self.msg("The battle has ended.")
        log_info(f"Battle {self.battle_id} fully cleaned up")

    # ------------------------------------------------------------------
    # Battle helpers
    # ------------------------------------------------------------------
    def prompt_next_turn(self) -> None:
        """Prompt the player to issue a command for the next turn."""
        self._set_player_control(True)
        if self.state and self.battle:
            notify_watchers(
                self.state,
                format_turn_banner(getattr(self.battle, "turn_count", 1)),
                room=self.room,
            )
        if self.captainA and self.state and self.captainB is not None:
            try:
                iface_a = display_battle_interface(
                    self.captainA,
                    self.captainB,
                    self.state,
                    viewer_team="A",
                )
                iface_b = display_battle_interface(
                    self.captainB,
                    self.captainA,
                    self.state,
                    viewer_team="B",
                )
                iface_w = display_battle_interface(
                    self.captainA,
                    self.captainB,
                    self.state,
                    viewer_team=None,
                )
                for t in self.teamA:
                    self._msg_to(t, iface_a)
                for t in self.teamB:
                    self._msg_to(t, iface_b)
                for w in self.observers:
                    self._msg_to(w, iface_w)
            except Exception:
                log_warn("Failed to display battle interface", exc_info=True)
        self.msg("The battle awaits your move.")
        if self.battle and getattr(self.battle, "turn_count", 0) == 1:
            log_info(f"Prompted first turn for battle {self.battle_id}")

    def run_turn(self) -> None:
        """Advance the battle by one turn."""
        if not self.battle:
            return
        if self.state:
            notify_watchers(
                self.state,
                format_turn_banner(getattr(self.battle, "turn_count", 1)),
                room=self.room,
            )
        log_info(f"Running turn for battle {self.battle_id}")
        self._set_player_control(False)
        try:
            self.battle.run_turn()
        except Exception:
            err_txt = traceback.format_exc()
            self.turn_state["error"] = err_txt
            log_err(
                f"Error while running turn for battle {self.battle_id}:\n{err_txt}",
                exc_info=False,
            )
            self.notify(f"Battle error:\n{err_txt}")
        else:
            log_info(
                f"Finished turn {getattr(self.battle, 'turn_count', '?')} for battle {self.battle_id}"
            )
            if self.state:
                notify_watchers(
                    self.state,
                    format_turn_banner(getattr(self.battle, "turn_count", 1)),
                    room=self.room,
                )
        if self.state:
            self.state.declare.clear()
        if self.data:
            for pos in self.data.turndata.positions.values():
                pos.removeDeclare()
        if getattr(self, "storage", None):
            try:
                self.storage.set("data", self.logic.data.to_dict())
                self.storage.set("state", self.logic.state.to_dict())
            except Exception:
                log_warn("Failed to persist battle state", exc_info=True)
        self.prompt_next_turn()

    def _get_position_for_trainer(self, trainer):
        """Return the battle position and key associated with ``trainer``.

        Parameters
        ----------
        trainer : object
            Trainer for which to locate the position.

        Returns
        -------
        tuple[str | None, PositionData | None]
            A tuple of the position name (e.g. ``"A1"``) and the
            :class:`~pokemon.battle.battledata.PositionData` for that
            trainer.  If no position can be found, ``(None, None)`` is
            returned.
        """

        if not self.data:
            return None, None
        team = None
        if trainer in self.teamA:
            team = "A"
        elif trainer in self.teamB:
            team = "B"
        else:
            for idx, part in enumerate(getattr(self.battle, "participants", [])):
                if getattr(part, "player", None) is trainer:
                    team = "A" if idx == 0 else "B"
                    break
        if not team:
            return None, None
        pos_name = f"{team}1"
        return pos_name, self.data.turndata.positions.get(pos_name)

    def _already_queued(self, pos_name, pos, caller, action_desc: str) -> bool:
        """Check if a position already has an action queued.

        Parameters
        ----------
        pos_name : str
            Name of the position (e.g. ``"A1"``).
        pos : PositionData
            Position data object for the active Pokémon.
        caller : object | None
            Trainer attempting the action. Used for notifications.
        action_desc : str
            Description of the attempted action for logging.

        Returns
        -------
        bool
            ``True`` if an action was already queued and the new request should
            be ignored, otherwise ``False``.
        """

        pokemon_name = getattr(getattr(pos, "pokemon", None), "name", "Unknown")
        if pos.getAction() or (self.state and pos_name in self.state.declare):
            self._msg_to(
                caller or self.captainA,
                f"{pokemon_name} already has an action queued this turn.",
            )
            log_info(
                f"Ignored {action_desc} for {pokemon_name} at {pos_name}: action already queued"
            )
            self.maybe_run_turn()
            return True
        return False

    def queue_move(self, move_name: str, target: str = "B1", caller=None) -> None:
        """Queue a move and run the turn if ready."""
        if not self.data or not self.battle:
            return
        pos_name, pos = self._get_position_for_trainer(caller or self.captainA)
        if not pos:
            return
        pokemon_name = getattr(getattr(pos, "pokemon", None), "name", "Unknown")
        if self._already_queued(pos_name, pos, caller, f"move {move_name}"):
            return
        pos.declareAttack(target, move_name)
        log_info(
            f"Queued move {move_name} targeting {target} from {pokemon_name} at {pos_name}"
        )
        if self.state:
            actor_id = str(getattr(caller or self.captainA, "id", ""))
            poke_id = str(getattr(getattr(pos, "pokemon", None), "model_id", ""))
            self.state.declare[pos_name] = {
                "move": move_name,
                "target": target,
                "trainer": actor_id,
                "pokemon": poke_id,
            }
        self.storage.set("data", self.logic.data.to_dict())
        self.storage.set("state", self.logic.state.to_dict())
        log_info(
            f"Saved queued move for {pokemon_name} at {pos_name} to room data"
        )
        self.maybe_run_turn()

    def queue_switch(self, slot: int, caller=None) -> None:
        """Queue a Pokémon switch and run the turn if ready."""
        if not self.data or not self.battle:
            return
        pos_name, pos = self._get_position_for_trainer(caller or self.captainA)
        if not pos:
            return
        pokemon_name = getattr(getattr(pos, "pokemon", None), "name", "Unknown")
        if self._already_queued(pos_name, pos, caller, "switch"):
            return
        pos.declareSwitch(slot)
        log_info(f"Queued switch to slot {slot} for {pokemon_name} at {pos_name}")
        if self.state:
            actor_id = str(getattr(caller or self.captainA, "id", ""))
            poke_id = str(getattr(getattr(pos, "pokemon", None), "model_id", ""))
            self.state.declare[pos_name] = {
                "switch": slot,
                "trainer": actor_id,
                "pokemon": poke_id,
            }
        self.storage.set("data", self.logic.data.to_dict())
        self.storage.set("state", self.logic.state.to_dict())
        log_info(
            f"Saved queued switch for {pokemon_name} at {pos_name} to room data"
        )
        self.maybe_run_turn()

    def queue_item(self, item_name: str, target: str = "B1", caller=None) -> None:
        """Queue an item use and run the turn if ready."""
        if not self.data or not self.battle:
            return
        pos_name, pos = self._get_position_for_trainer(caller or self.captainA)
        if not pos:
            return
        pokemon_name = getattr(getattr(pos, "pokemon", None), "name", "Unknown")
        if self._already_queued(pos_name, pos, caller, f"item {item_name}"):
            return
        pos.declareItem(item_name)
        log_info(
            f"Queued item {item_name} targeting {target} from {pokemon_name} at {pos_name}"
        )
        if self.state:
            actor_id = str(getattr(caller or self.captainA, "id", ""))
            poke_id = str(getattr(getattr(pos, "pokemon", None), "model_id", ""))
            self.state.declare[pos_name] = {
                "item": item_name,
                "target": target,
                "trainer": actor_id,
                "pokemon": poke_id,
            }
        self.storage.set("data", self.logic.data.to_dict())
        self.storage.set("state", self.logic.state.to_dict())
        log_info(
            f"Saved queued item for {pokemon_name} at {pos_name} to room data"
        )
        self.maybe_run_turn()

    def queue_run(self, caller=None) -> None:
        """Queue a flee attempt and run the turn if ready."""
        if not self.data or not self.battle:
            return
        pos_name, pos = self._get_position_for_trainer(caller or self.captainA)
        if not pos:
            return
        pokemon_name = getattr(getattr(pos, "pokemon", None), "name", "Unknown")
        if self._already_queued(pos_name, pos, caller, "flee attempt"):
            return
        pos.declareRun()
        log_info(f"Queued attempt to flee by {pokemon_name} at {pos_name}")
        if self.state:
            actor_id = str(getattr(caller or self.captainA, "id", ""))
            poke_id = str(getattr(getattr(pos, "pokemon", None), "model_id", ""))
            self.state.declare[pos_name] = {
                "run": "1",
                "trainer": actor_id,
                "pokemon": poke_id,
            }
        self.storage.set("data", self.logic.data.to_dict())
        self.storage.set("state", self.logic.state.to_dict())
        log_info(
            f"Saved flee attempt for {pokemon_name} at {pos_name} to room data"
        )
        self.maybe_run_turn()

    def is_turn_ready(self) -> bool:
        if self.data:
            if self.state:
                missing = [
                    name
                    for name in self.data.turndata.positions
                    if name not in self.state.declare
                ]
            else:
                missing = [
                    name
                    for name, pos in self.data.turndata.positions.items()
                    if not pos.getAction()
                ]
            if missing:
                log_info(
                    f"Waiting for actions from positions {missing} in battle {self.battle_id}"
                )
                return False
        if self.battle and getattr(self.battle, "participants", None):
            if self.state:
                return True
            incomplete = [
                getattr(p, "name", str(p))
                for p in self.battle.participants
                if not getattr(p, "pending_action", None)
            ]
            if incomplete:
                log_info(
                    f"Waiting for pending actions from {incomplete} in battle {self.battle_id}"
                )
                return False
            return True
        return False

    def maybe_run_turn(self) -> None:
        if self.is_turn_ready():
            log_info(f"Turn ready for battle {self.battle_id}")
            self.run_turn()
        else:
            log_info(f"Turn not ready for battle {self.battle_id}")
            waiting_poke = None
            if self.data:
                for name, pos in self.data.turndata.positions.items():
                    if not pos.getAction() and pos.pokemon:
                        waiting_poke = pos.pokemon
                        break
            if waiting_poke:
                self.msg(f"Waiting on {getattr(waiting_poke, 'name', str(waiting_poke))}...")
                try:
                    iface_a = display_battle_interface(
                        self.captainA,
                        self.captainB,
                        self.state,
                        viewer_team="A",
                        waiting_on=waiting_poke,
                    )
                    iface_b = display_battle_interface(
                        self.captainB,
                        self.captainA,
                        self.state,
                        viewer_team="B",
                        waiting_on=waiting_poke,
                    )
                    iface_w = display_battle_interface(
                        self.captainA,
                        self.captainB,
                        self.state,
                        viewer_team=None,
                        waiting_on=waiting_poke,
                    )
                    for t in self.teamA:
                        self._msg_to(t, iface_a)
                    for t in self.teamB:
                        self._msg_to(t, iface_b)
                    for w in self.observers:
                        self._msg_to(w, iface_w)
                except Exception:
                    log_warn("Failed to display waiting interface", exc_info=True)

    # ------------------------------------------------------------------
    # Watcher helpers
    # ------------------------------------------------------------------
    def add_watcher(self, watcher) -> None:
        if not self.state:
            return
        add_watcher(self.state, watcher)
        self.watchers.add(watcher.id)
        log_info(f"Watcher {getattr(watcher, 'key', watcher)} added")

    def remove_watcher(self, watcher) -> None:
        if not self.state:
            return
        remove_watcher(self.state, watcher)
        self.watchers.discard(watcher.id)
        log_info(f"Watcher {getattr(watcher, 'key', watcher)} removed")

    def notify(self, message: str) -> None:
        if not self.state:
            return
        notify_watchers(self.state, message, room=self.room)
        log_info(f"Notified watchers: {message}")

    # ------------------------------------------------------------
    # Observer helpers
    # ------------------------------------------------------------

    def add_observer(self, watcher) -> None:
        """Register an observer to receive battle messages."""
        if watcher not in self.observers:
            self.observers.add(watcher)
            watcher.ndb.battle_instance = self
            if self.state:
                add_watcher(self.state, watcher)
                self.watchers.add(getattr(watcher, "id", 0))
            self.msg(f"{watcher.key} is now watching the battle.")
            log_info(f"Observer {getattr(watcher, 'key', watcher)} added")

    def remove_observer(self, watcher) -> None:
        if watcher in self.observers:
            self.observers.discard(watcher)
            if getattr(watcher.ndb, "battle_instance", None) == self:
                del watcher.ndb.battle_instance
            if self.state:
                remove_watcher(self.state, watcher)
        self.watchers.discard(getattr(watcher, "id", 0))
        log_info(f"Observer {getattr(watcher, 'key', watcher)} removed")


__all__ = ["BattleSession", "BattleInstance"]
