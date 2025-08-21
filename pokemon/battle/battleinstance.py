from __future__ import annotations

import random
from typing import Any, Dict, List, Optional, Set, Tuple

from .battledata import BattleData, Team, Pokemon, Move
from .engine import Battle, BattleParticipant, BattleType
from .messaging import MessagingMixin
from .state import BattleState
from .watchers import WatcherManager
from utils.safe_import import safe_import

try:  # pragma: no cover - tests may stub watchers without helper
    normalize_watchers = safe_import("pokemon.battle.watchers").normalize_watchers  # type: ignore[attr-defined]
except (ModuleNotFoundError, AttributeError):  # pragma: no cover - fallback when helper unavailable

    def normalize_watchers(val: Any) -> List[int]:  # type: ignore[misc]
        """Normalize a stored watcher representation to a list of ints."""

        if isinstance(val, list):
            return [int(x) for x in val if isinstance(x, (int, str))]
        if isinstance(val, set):
            return [int(x) for x in val]
        if isinstance(val, str):
            s = val.strip()
            if s.startswith("{") and s.endswith("}"):
                s = s[1:-1]
            out: List[int] = []
            for part in s.split(","):
                part = part.strip()
                if not part:
                    continue
                try:
                    out.append(int(part))
                except Exception:
                    continue
            return out
        return []


from .actionqueue import ActionQueue
from .turn import TurnManager
from .interface import render_interfaces

try:  # pragma: no cover - interface may be stubbed in tests
    broadcast_interfaces = safe_import("pokemon.battle.interface").broadcast_interfaces  # type: ignore[attr-defined]
except (ModuleNotFoundError, AttributeError):  # pragma: no cover - fallback implementation

    def broadcast_interfaces(session, *, waiting_on=None):  # type: ignore[misc]
        iface_a, iface_b, iface_w = render_interfaces(
            session.captainA, session.captainB, session.state, waiting_on=waiting_on
        )
        for t in getattr(session, "teamA", []):
            session._msg_to(t, iface_a)
        for t in getattr(session, "teamB", []):
            session._msg_to(t, iface_b)
        for w in getattr(session, "observers", []):
            session._msg_to(w, iface_w)


from .handler import battle_handler
from .storage import BattleDataWrapper
from utils.pokemon_utils import build_battle_pokemon_from_model
from .setup import create_participants, build_initial_state, persist_initial_state
from .persistence import StatePersistenceMixin
from .compat import (
    log_info,
    log_warn,
    log_err,
    search_object,
    BattleLogic,
    generate_trainer_pokemon,
    generate_wild_pokemon,
    create_battle_pokemon,
    ScriptBase as _ScriptBase,
)


class BattleInstance(_ScriptBase):
    """Legacy placeholder kept to clean up old script-based battles."""

    def at_script_creation(self):
        self.persistent = False

    def at_server_start(self):
        try:
            self.stop()
        except Exception:
            pass


class BattleSession(TurnManager, MessagingMixin, WatcherManager, ActionQueue, StatePersistenceMixin):
    """Container representing an active battle in a room."""

    def __repr__(self) -> str:
        player = getattr(self.captainA, "key", getattr(self.captainA, "id", "?"))
        opp = getattr(self.captainB, "key", getattr(self.captainB, "id", "?")) if self.captainB else None
        return f"<BattleSession id={self.battle_id} captainA={player} captainB={opp}>"

    def __init__(self, player, opponent: Optional[object] = None):
        log_info(
            (
                f"Initializing BattleSession {getattr(player, 'id', '?')} between "
                f"{getattr(player, 'key', player)} and "
                f"{getattr(opponent, 'key', opponent) if opponent else '<wild>'}"
            )
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
        # keep a non-persistent watcher set on ndb
        self.ndb = type("NDB", (), {})()
        self.ndb.watchers_live = set()
        self.temp_pokemon_ids: List[int] = []

        log_info(f"BattleSession {self.battle_id} registered in room #{getattr(self.room, 'id', '?')}")
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
            log_info(f"Found existing instance {getattr(inst, 'battle_id', 'N/A')} on ndb")
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

    @classmethod
    def restore(cls, room, battle_id: int) -> "BattleSession | None":
        """Recreate an instance from a stored battle on a room."""
        log_info(f"Attempting restore of battle {battle_id} in room #{getattr(room, 'id', '?')}")
        # Import FusionRoom lazily to avoid circular dependency during module load.
        try:  # pragma: no cover - FusionRoom is optional at runtime
            FusionRoom = safe_import("typeclasses.rooms").FusionRoom  # type: ignore[attr-defined]
        except ModuleNotFoundError:
            FusionRoom = None  # type: ignore[assignment]
        except Exception as err:
            log_err(f"Room type import failed: {err}")
            FusionRoom = None  # type: ignore[assignment]
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
        obj.ndb = type("NDB", (), {})()
        logic = BattleLogic.from_dict({"data": data, "state": state})
        obj.logic = logic
        obj.logic.battle.log_action = obj.notify
        # Rehydrate any queued-but-unresolved declarations from state -> positions.
        # This avoids needing to persist turndata.turninit snapshots on input.
        try:
            decls: Dict[str, Any] = getattr(obj.logic.state, "declare", {}) or {}
            positions: Dict[str, Any] = getattr(obj.logic.data.turndata, "positions", {}) or {}
            for pos_name, d in decls.items():
                pos = positions.get(pos_name)
                if not pos or not isinstance(d, dict):
                    continue
                # d may contain one of: {"move","target"}, {"switch"}, {"item"}, {"run"}
                if "move" in d:
                    # default target if missing
                    tgt = d.get("target", "B1")
                    pos.declareAttack(tgt, d["move"])
                elif "switch" in d:
                    try:
                        pos.declareSwitch(int(d["switch"]))
                    except Exception:
                        pos.declareSwitch(d["switch"])
                elif "item" in d:
                    pos.declareItem(d["item"])
                elif "run" in d:
                    pos.declareRun()
        except Exception:
            log_warn("Failed to rehydrate queued declarations during restore", exc_info=True)
        obj.temp_pokemon_ids = list(storage.get("temp_pokemon_ids") or [])
        # Ensure state turn matches data since we drop it during compaction
        obj.logic.state.turn = getattr(obj.logic.data.battle, "turn", 1)
        log_info("Restored logic and temp Pokemon ids")

        # Watchers: keep a live, non-persistent copy on ndb; normalize any persisted list
        try:
            raw_watchers: Any = storage.get("state", {}).get("watchers") or storage.get("watchers") or []
            watchers_live: Set[int] = set(normalize_watchers(raw_watchers))
            obj.ndb.watchers_live = watchers_live
        except Exception:
            obj.ndb.watchers_live = set()
        # Keep existing 'watchers' attribute aligned to live set for code using obj.watchers
        obj.watchers = set(getattr(obj.ndb, "watchers_live", set()))

        trainer_info = storage.get("trainers", {}) or {}
        teamA = trainer_info.get("teamA", [])
        teamB = trainer_info.get("teamB", [])

        watcher_ids = set(getattr(obj.ndb, "watchers_live", set()))
        watcher_ids.update(teamA)
        watcher_ids.update(teamB)
        obj.ndb.watchers_live = set(watcher_ids)
        obj.watchers = set(watcher_ids)
        if getattr(obj.state, "watchers", None) is not None:
            obj.state.watchers = set(watcher_ids)

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

        # Reattach participant -> player references based on team membership
        try:
            parts = getattr(obj.logic.battle, "participants", [])
            team_map = {"A": obj.teamA, "B": obj.teamB}
            team_idx = {"A": 0, "B": 0}
            for part in parts:
                t = getattr(part, "team", None)
                if t in team_map:
                    idx = team_idx.get(t, 0)
                    if idx < len(team_map[t]):
                        part.player = team_map[t][idx]
                    team_idx[t] = idx + 1
        except Exception:
            pass

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

        for wid in obj.watchers:
            log_info(f"Restoring watcher {wid}")
            if wid in teamA and team_a_objs:
                watcher = next((w for w in team_a_objs if getattr(w, "id", 0) == wid), None)
            elif wid in teamB and team_b_objs:
                watcher = next((w for w in team_b_objs if getattr(w, "id", 0) == wid), None)
            else:
                targets = search_object(f"#{wid}")
                if not targets:
                    log_info(f"Could not find watcher {wid}")
                    continue
                watcher = targets[0]
            obj.add_watcher(watcher)
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
        obj.ndb.watchers_live = set(obj.watchers)
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
        log_info(f"Starting battle {self.battle_id} in room #{getattr(self.room, 'id', '?')}")
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
        self._init_battle_state(origin, player_pokemon, opponent_poke, opponent_name, battle_type)
        self._setup_battle_room()

    def start_pvp(self) -> None:
        """Start a battle between two players."""
        if not self.captainB:
            return

        origin = getattr(self.captainA, "location", None)

        log_info(f"Initializing PvP battle {self.battle_id} between {self.captainA.key} and {self.captainB.key}")

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
                player_participant = BattleParticipant(self.captainA.key, player_pokemon, team="A")
            except TypeError:
                player_participant = BattleParticipant(self.captainA.key, player_pokemon)
        try:
            opponent_participant = BattleParticipant(
                self.captainB.key,
                opp_pokemon,
                player=self.captainB,
                team="B",
            )
        except TypeError:
            try:
                opponent_participant = BattleParticipant(self.captainB.key, opp_pokemon, team="B")
            except TypeError:
                opponent_participant = BattleParticipant(self.captainB.key, opp_pokemon)

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
        trainer_ids = {"teamA": []}
        if hasattr(self.captainA, "id"):
            trainer_ids["teamA"].append(self.captainA.id)
        if self.captainB:
            trainer_ids["teamB"] = []
            if hasattr(self.captainB, "id"):
                trainer_ids["teamB"].append(self.captainB.id)
        self.storage.set("trainers", trainer_ids)
        log_info("Saved PvP battle data to room")

        self.add_watcher(self.captainA)
        self.add_watcher(self.captainB)
        self.msg("PVP battle started!")
        self.msg(f"Battle ID: {self.battle_id}")
        log_info(f"PvP battle {self.battle_id} started")
        self.notify(f"{self.captainA.key} and {self.captainB.key} begin a battle!")

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
        log_info(f"Preparing party for {getattr(trainer, 'key', trainer)} (full_heal={full_heal})")
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
        log_info(f"Prepared {len(pokemons)} pokemons for {getattr(trainer, 'key', trainer)}")
        return pokemons

    def _init_battle_state(
        self,
        origin,
        player_pokemon: List[Pokemon],
        opponent_poke: Pokemon,
        opponent_name: str,
        battle_type: BattleType,
    ) -> None:
        """Wrapper coordinating helper functions to set up a battle."""
        log_info(f"Initializing battle state for {self.captainA.key} vs {opponent_name}")
        player_participant, opponent_participant = create_participants(
            self.captainA, player_pokemon, opponent_poke, opponent_name
        )
        self.logic = build_initial_state(
            origin,
            battle_type,
            player_participant,
            opponent_participant,
            player_pokemon,
            opponent_poke,
            self.captainA,
            self.notify,
            self.captainB,
        )
        log_info(f"Battle logic created with {len(player_pokemon)} player pokemon")
        persist_initial_state(self, player_participant, player_pokemon)
        log_info(f"Saved battle data for id {self.battle_id}")

    def _setup_battle_room(self) -> None:
        """Move players to the battle room and notify watchers."""
        log_info(f"Setting up battle room for {self.battle_id}")
        self.add_watcher(self.captainA)
        self.msg("Battle started!")
        self.msg(f"Battle ID: {self.battle_id}")
        self.notify(f"{getattr(self.captainA, 'key', 'Player')} has entered battle!")

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
            self.notify("The battle has ended.")
        self.watchers.clear()
        if hasattr(self.ndb, "watchers_live"):
            self.ndb.watchers_live.clear()
        battle_handler.unregister(self)
        for seg in ("data", "state", "meta", "field", "active"):
            self.storage.delete(seg)
        log_info(f"Cleared battle data for {self.battle_id}")
        self.msg("The battle has ended.")
        log_info(f"Battle {self.battle_id} fully cleaned up")

    # ---- Persistence helpers ------------------------------------------------

    def is_turn_ready(self) -> bool:
        if self.data:
            if self.state:
                missing = [name for name in self.data.turndata.positions if name not in self.state.declare]
            else:
                missing = [name for name, pos in self.data.turndata.positions.items() if not pos.getAction()]
            if missing:
                log_info(f"Waiting for actions from positions {missing} in battle {self.battle_id}")
                return False
        if self.battle and getattr(self.battle, "participants", None):
            if self.state:
                return True
            incomplete = [
                getattr(p, "name", str(p)) for p in self.battle.participants if not getattr(p, "pending_action", None)
            ]
            if incomplete:
                log_info(f"Waiting for pending actions from {incomplete} in battle {self.battle_id}")
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
                    broadcast_interfaces(self, waiting_on=waiting_poke)
                except Exception:
                    log_warn("Failed to display waiting interface", exc_info=True)


__all__ = ["BattleSession", "BattleInstance", "create_battle_pokemon"]
