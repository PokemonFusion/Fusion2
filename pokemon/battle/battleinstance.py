from __future__ import annotations

import random
from typing import Any, Dict, List, Optional, Set, Tuple
from types import SimpleNamespace

from utils.safe_import import safe_import

from .actions import ActionType
from .battledata import BattleData, Pokemon, Team
from .engine import Battle, BattleParticipant, BattleType
from .messaging import MessagingMixin
from .state import BattleState
from .watchers import WatcherManager

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
from .interface import render_interfaces
from .turn import TurnManager

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


try:  # pragma: no cover - interface may be stubbed in tests
    send_interface_to = safe_import("pokemon.battle.interface").send_interface_to  # type: ignore[attr-defined]
except (ModuleNotFoundError, AttributeError):  # pragma: no cover - fallback implementation

    def send_interface_to(session, target, *, waiting_on=None):  # type: ignore[misc]
        if not target:
            return

        iface_a, iface_b, iface_w = render_interfaces(
            session.captainA, session.captainB, session.state, waiting_on=waiting_on
        )
        if target in getattr(session, "teamA", []):
            session._msg_to(target, iface_a)
        elif target in getattr(session, "teamB", []):
            session._msg_to(target, iface_b)
        elif target in getattr(session, "observers", []):
            session._msg_to(target, iface_w)
        else:
            session._msg_to(target, iface_w)


from utils.pokemon_utils import build_battle_pokemon_from_model
from utils.locks import clear_battle_lock, set_battle_lock

from .compat import (
    BattleLogic,
    _battle_norm_key,
    create_battle_pokemon,
    generate_trainer_pokemon,
    generate_wild_pokemon,
    log_err,
    log_info,
    log_warn,
    search_object,
)
from .compat import (
    ScriptBase as _ScriptBase,
)
from .handler import battle_handler
from .persistence import StatePersistenceMixin
from .setup import build_initial_state, create_participants, persist_initial_state
from .storage import BattleDataWrapper


try:  # pragma: no cover - optional import path during tests
    _select_ai_action = safe_import("pokemon.battle.engine")._select_ai_action  # type: ignore[attr-defined]
except (ModuleNotFoundError, AttributeError):  # pragma: no cover - fallback when engine unavailable
    _select_ai_action = None  # type: ignore[assignment]


class BattleInstance(_ScriptBase):
    """Legacy placeholder used to clean up obsolete script-based battles.

    Subclassing ``ScriptBase`` lets Evennia treat this as a valid script when
    loading old records, while the abstract ``Meta`` prevents Django from
    registering an additional model.
    """

    class Meta:
        abstract = True  # prevent Django from creating a new model

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

    def __init__(
        self,
        player,
        opponent: Optional[object] = None,
        *,
        rng: Optional[random.Random] = None,
    ) -> None:
        log_info(
            (
                f"Initializing BattleSession {getattr(player, 'id', '?')} between "
                f"{getattr(player, 'key', player)} and "
                f"{getattr(opponent, 'key', opponent) if opponent else '<wild>'}"
            )
        )
        self.teamA: List[object] = [player]
        self.teamB: List[object] = [opponent] if opponent else []
        self.rng = rng or random
        self.room = getattr(player, "location", None)
        if self.room is None:
            raise ValueError("BattleSession requires the player to have a location")

        self.trainers: List[object] = [t for t in self.teamA + self.teamB if t]
        self.observers: set[object] = set()
        self.turn_state: dict = {}

        self.battle_id = getattr(player, "id", 0)
        self._register_trainer(player)
        if opponent:
            self._register_trainer(opponent)

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
        self.ndb.rng = self.rng
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

    # ------------------------------------------------------------
    # Turn helpers
    # ------------------------------------------------------------

    def _position_for_pokemon(self, pokemon, positions: Dict[str, Any]) -> Tuple[str | None, Any | None]:
        """Return the position name and data for ``pokemon`` if present."""

        for name, pos in positions.items():
            if getattr(pos, "pokemon", None) is pokemon:
                return name, pos
        return None, None

    def _determine_target_position(self, action, positions: Dict[str, Any]) -> str:
        """Best-effort resolution of the target position for ``action``."""

        target_team = getattr(getattr(action, "target", None), "team", None)
        if target_team:
            active = list(getattr(getattr(action, "target", None), "active", []))
            for name, pos in positions.items():
                if not name.startswith(str(target_team)):
                    continue
                if getattr(pos, "pokemon", None) in active:
                    return name
            return f"{target_team}1"

        actor_team = getattr(getattr(action, "actor", None), "team", None)
        default_team = "A" if actor_team == "B" else "B"
        for name in sorted(positions.keys()):
            if name.startswith(default_team):
                return name
        return f"{default_team}1"

    def _auto_queue_ai_actions(self) -> bool:
        """Automatically queue actions for AI-controlled participants."""

        if not self.battle or not self.data or not _select_ai_action:
            return False

        positions: Dict[str, Any] = getattr(getattr(self.data, "turndata", None), "positions", {}) or {}
        if not positions:
            return False

        queued = False
        for participant in getattr(self.battle, "participants", []):
            if not getattr(participant, "is_ai", False):
                continue
            for pokemon in list(getattr(participant, "active", [])):
                pos_name, pos = self._position_for_pokemon(pokemon, positions)
                if not pos_name or not pos or pos.getAction():
                    continue
                try:
                    action = _select_ai_action(participant, pokemon, self.battle)  # type: ignore[misc]
                except Exception:
                    action = None
                if not action or getattr(action, "action_type", None) is not ActionType.MOVE:
                    continue
                move_obj = getattr(action, "move", None)
                move_key = getattr(move_obj, "key", None) or getattr(move_obj, "name", None)
                if not move_key:
                    continue
                target_pos = self._determine_target_position(action, positions)
                norm_key = _battle_norm_key(str(move_key))
                try:
                    pos.declareAttack(target_pos, norm_key)
                except Exception:
                    continue
                if self.state is not None:
                    self.state.declare[pos_name] = {"move": norm_key, "target": target_pos}
                participant.pending_action = action
                queued = True

        if queued and self.logic and getattr(self, "storage", None):
            try:
                compact = self._compact_state_for_persist(self.logic.state.to_dict())
                self.storage.set("state", compact)
            except Exception:
                log_warn("Failed to persist AI action selection", exc_info=True)

        return queued

    def _trainer_for_position(self, pos_name: str, pokemon) -> Any | None:
        """Return the trainer controlling ``pokemon`` at ``pos_name``."""

        if not pokemon:
            return None

        state = self.state
        if state:
            poke_id = getattr(pokemon, "model_id", None)
            if poke_id is not None:
                owner_id = state.pokemon_control.get(str(poke_id))
                if owner_id:
                    for trainer in list(self.teamA) + list(self.teamB):
                        if not trainer:
                            continue
                        tid = getattr(trainer, "id", None)
                        if tid is not None and str(tid) == str(owner_id):
                            return trainer

        if pos_name.startswith("A"):
            return self.captainA
        if pos_name.startswith("B"):
            return self.captainB
        return None

    @staticmethod
    def _format_pokemon_names(names: List[str]) -> str:
        """Return a human-friendly list for ``names``."""

        if not names:
            return ""
        if len(names) == 1:
            return names[0]
        if len(names) == 2:
            return f"{names[0]} and {names[1]}"
        return f"{', '.join(names[:-1])}, and {names[-1]}"

    def _prompt_active_pokemon(self) -> None:
        """Notify trainers which Pokémon require commands this turn."""

        if not self.data:
            return
        positions: Dict[str, Any] = getattr(getattr(self.data, "turndata", None), "positions", {}) or {}
        if not positions:
            return

        prompts: Dict[Any, List[str]] = {}
        for pos_name, pos in positions.items():
            pokemon = getattr(pos, "pokemon", None)
            if not pokemon:
                continue
            trainer = self._trainer_for_position(pos_name, pokemon)
            if not trainer or getattr(trainer, "is_wild", False) or getattr(trainer, "is_npc", False):
                continue
            name = getattr(pokemon, "name", None) or getattr(pokemon, "species", None)
            if not name:
                continue
            prompts.setdefault(trainer, []).append(str(name))

        for trainer, names in prompts.items():
            message = f"Choose an action for {self._format_pokemon_names(names)}."
            self._msg_to(trainer, message)
    def _register_trainer(self, trainer) -> None:
        """Record battle state and locks for ``trainer``."""

        if not trainer:
            return

        if hasattr(trainer, "db"):
            trainer.db.battle_id = self.battle_id
            set_battle_lock(trainer, self.battle_id)

        ndb = getattr(trainer, "ndb", None)
        if ndb is not None:
            ndb.battle_instance = self

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
        """Recreate an instance from a stored battle on a room.

        Missing team or moveset data in the persisted state is
        reconstructed from the stored :class:`BattleData`.
        """
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
        # Rebuild missing team or moveset data when restoring older saves
        if (
            not getattr(logic.state, "movesets", None)
            or not logic.state.movesets
            or not any(getattr(logic.state, "teams", {}).values())
        ):
            rebuilt_state = BattleState.from_battle_data(logic.data, ai_type=logic.state.ai_type)
            if not getattr(logic.state, "movesets", None) or not logic.state.movesets:
                logic.state.movesets = rebuilt_state.movesets
            if not any(getattr(logic.state, "teams", {}).values()):
                logic.state.teams = rebuilt_state.teams
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
                obj._register_trainer(member)
        team_b_objs = []
        for tid in teamB:
            targets = search_object(f"#{tid}")
            if targets:
                member = targets[0]
                team_b_objs.append(member)
                if obj.captainB is None:
                    obj.captainB = member
                obj._register_trainer(member)
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
                obj._register_trainer(watcher)
            elif wid in teamB:
                if obj.captainB is None:
                    obj.captainB = watcher
                if watcher not in team_b_objs:
                    team_b_objs.append(watcher)
                obj.trainers.append(watcher)
                obj._register_trainer(watcher)
            else:
                obj.observers.add(watcher)
        obj.ndb.watchers_live = set(obj.watchers)
        if obj.captainA or obj.captainB:
            obj.trainers = team_a_objs + team_b_objs
        else:
            obj.trainers = []
        for trainer in obj.trainers:
            obj._register_trainer(trainer)
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
        opponent_poke, opponent_name, battle_type, intro_message = self._select_opponent()
        if battle_type == BattleType.WILD and not self.captainB:
            shell_name = f"Wild {getattr(opponent_poke, 'name', 'Pokémon')}"
            opponent_shell = SimpleNamespace(
                name=shell_name,
                key=shell_name,
                team=[opponent_poke],
                active_pokemon=opponent_poke,
                is_wild=True,
                ndb=SimpleNamespace(),
                db=SimpleNamespace(),
            )
            self.captainB = opponent_shell
            self._register_trainer(self.captainB)
            self.trainers = [t for t in (self.captainA, self.captainB) if t]
            for trainer in self.trainers:
                self._register_trainer(trainer)
        player_pokemon = self._prepare_player_party(self.captainA)
        log_info(f"Prepared player party with {len(player_pokemon)} pokemon")
        self._init_battle_state(origin, player_pokemon, opponent_poke, opponent_name, battle_type)
        self._setup_battle_room(intro_message=intro_message)

    def start_pvp(self) -> None:
        """Start a battle between two players."""
        if not self.captainB:
            return

        origin = getattr(self.captainA, "location", None)

        log_info(f"Initializing PvP battle {self.battle_id} between {self.captainA.key} and {self.captainB.key}")

        player_pokemon = self._prepare_player_party(self.captainA)

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

        battle = Battle(
            BattleType.PVP,
            [player_participant, opponent_participant],
            rng=self.rng,
        )

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
    def _select_opponent(self) -> tuple[Pokemon, str, BattleType, str | None]:
        """Return the opponent details and introductory message."""
        opponent_kind = self.rng.choice(["pokemon", "trainer"])
        log_info(f"Selecting opponent: {opponent_kind}")
        if opponent_kind == "pokemon":
            opponent_poke = generate_wild_pokemon(self.captainA.location)
            if getattr(opponent_poke, "model_id", None):
                self.temp_pokemon_ids.append(opponent_poke.model_id)
            battle_type = BattleType.WILD
            opponent_name = "Wild"
            intro_message = f"A wild {opponent_poke.name} appears!"
            log_info(f"Wild opponent {opponent_poke.name} generated")
        else:
            opponent_poke = generate_trainer_pokemon()
            if getattr(opponent_poke, "model_id", None):
                self.temp_pokemon_ids.append(opponent_poke.model_id)
            battle_type = BattleType.TRAINER
            opponent_name = "Trainer"
            intro_message = f"A trainer challenges you with {opponent_poke.name}!"
            log_info(f"Trainer opponent {opponent_poke.name} generated")
        return opponent_poke, opponent_name, battle_type, intro_message

    def _prepare_player_party(self, trainer, full_heal: bool = False) -> List[Pokemon]:
        """Return a list of battle-ready Pokemon for a trainer.

        If ``full_heal`` is ``True`` the Pokémon start with full HP regardless
        of any stored current HP value. This is primarily useful for scripted
        encounters that override health when constructing temporary teams.
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
            rng=self.rng,
        )
        log_info(f"Battle logic created with {len(player_pokemon)} player pokemon")
        persist_initial_state(self, player_participant, player_pokemon)
        log_info(f"Saved battle data for id {self.battle_id}")

    def _setup_battle_room(self, intro_message: str | None = None) -> None:
        """Move players to the battle room and notify watchers."""
        log_info(f"Setting up battle room for {self.battle_id}")
        self.add_watcher(self.captainA)
        if self.captainB and getattr(self.captainB, "id", None) is not None:
            self.add_watcher(self.captainB)
        self.msg("Battle started!")
        self.msg(f"Battle ID: {self.battle_id}")
        self.notify(f"{getattr(self.captainA, 'key', 'Player')} has entered battle!")

        if self.battle and hasattr(self.battle, "start_turn"):
            self.battle.start_turn()

        if intro_message:
            self.msg(intro_message)

        self.prompt_next_turn()
        battle_handler.register(self)
        log_info(f"Battle {self.battle_id} registered with handler")

    def _sync_player_pokemon_state(self) -> None:
        """Persist battle results back to the owning player models.

        ``BattleSession`` creates temporary battle representations of a
        trainer's Pokémon. This helper mirrors the resulting HP and status back
        onto the owning :class:`~pokemon.models.core.OwnedPokemon` instances so
        that battles leave lasting effects on a player's party.
        """

        if not self.battle or not getattr(self.battle, "participants", None):
            return

        for participant in self.battle.participants:
            player = getattr(participant, "player", None)
            if not player:
                continue

            storage = getattr(player, "storage", None)
            if not storage:
                continue

            party: List[Any] = []
            if hasattr(storage, "get_party"):
                try:
                    party = list(storage.get_party())
                except Exception:
                    party = []
            if not party and hasattr(storage, "active_pokemon"):
                manager = storage.active_pokemon
                try:
                    party = list(manager.all())  # type: ignore[attr-defined]
                except Exception:
                    try:
                        party = list(manager)
                    except Exception:
                        party = []
            if not party:
                continue

            lookup: Dict[str, Any] = {}
            for mon in party:
                identifier = getattr(mon, "unique_id", None) or getattr(mon, "id", None)
                if identifier is not None:
                    lookup[str(identifier)] = mon

            for poke in getattr(participant, "pokemons", []):
                model_id = getattr(poke, "model_id", None)
                if not model_id:
                    continue

                mon = lookup.get(str(model_id))
                if not mon:
                    continue

                max_hp = getattr(mon, "current_hp", 0)
                get_max_hp = getattr(mon, "get_max_hp", None)
                if callable(get_max_hp):
                    try:
                        max_hp = int(get_max_hp())
                    except Exception:
                        max_hp = getattr(mon, "current_hp", 0)

                hp_val = int(getattr(poke, "hp", getattr(mon, "current_hp", 0)) or 0)
                hp_val = max(0, min(hp_val, max_hp if max_hp else hp_val))
                if hasattr(mon, "current_hp"):
                    mon.current_hp = hp_val

                status_val = getattr(poke, "status", "")
                if isinstance(status_val, int):
                    status_val = "" if status_val <= 0 else str(status_val)
                if hasattr(mon, "status"):
                    mon.status = status_val or ""

                if hasattr(mon, "save"):
                    try:
                        mon.save(update_fields=["current_hp", "status"])
                    except Exception:
                        try:
                            mon.save()
                        except Exception:
                            pass

    def end(self) -> None:
        """End the battle and clean up."""
        log_info(f"Ending battle {self.battle_id}")
        self._sync_player_pokemon_state()
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
            if not trainer:
                continue
            ndb = getattr(trainer, "ndb", None)
            if ndb and getattr(ndb, "battle_instance", None) == self:
                delattr(ndb, "battle_instance")
            if hasattr(trainer, "db"):
                clear_battle_lock(trainer)
                if hasattr(trainer.db, "battle_id"):
                    delattr(trainer.db, "battle_id")
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

    def maybe_run_turn(self, actor=None, *, notify_waiting: bool = True) -> None:
        if self.is_turn_ready():
            log_info(f"Turn ready for battle {self.battle_id}")
            self.run_turn()
            return

        if self._auto_queue_ai_actions() and self.is_turn_ready():
            log_info(f"Turn ready for battle {self.battle_id} after AI selection")
            self.run_turn()
            return

        log_info(f"Turn not ready for battle {self.battle_id}")
        waiting_poke = None
        if self.data:
            for name, pos in self.data.turndata.positions.items():
                if not pos.getAction() and pos.pokemon:
                    waiting_poke = pos.pokemon
                    break
        waiting_participant = None
        if waiting_poke and self.battle:
            try:
                waiting_participant = self.battle.participant_for(waiting_poke)
            except Exception:
                waiting_participant = None
        if waiting_poke and not bool(getattr(waiting_participant, "is_ai", False)):
            waiting_name = getattr(waiting_poke, "name", str(waiting_poke))
            try:
                if actor:
                    send_interface_to(self, actor, waiting_on=waiting_name)
                else:
                    broadcast_interfaces(self, waiting_on=waiting_name)
            except Exception:
                log_warn("Failed to display waiting interface", exc_info=True)
            if notify_waiting:
                message = f"Waiting on {waiting_name}..."
                if actor:
                    self._msg_to(actor, message)
                else:
                    self.msg(message)


__all__ = ["BattleSession", "BattleInstance", "create_battle_pokemon"]
