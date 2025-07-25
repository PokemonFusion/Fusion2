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
from typing import List, Optional

try:
    from evennia import search_object
except Exception:  # pragma: no cover - fallback for tests without Evennia

    def search_object(dbref):
        return []


from .battledata import BattleData, Team, Pokemon, Move
from .engine import Battle, BattleParticipant, BattleType
from .state import BattleState
from .interface import add_watcher, notify_watchers, remove_watcher
from .handler import battle_handler
from .storage import BattleDataWrapper
from ..generation import generate_pokemon
from world.pokemon_spawn import get_spawn

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
    data = getattr(poke, "data", {}) or {}
    ivs = data.get("ivs", {})
    evs = data.get("evs", {})
    nature = data.get("nature", "Hardy")
    name = getattr(poke, "name", "Pikachu")
    level = getattr(poke, "level", 1)
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
        from ..models import OwnedPokemon
    except Exception:  # pragma: no cover - optional in tests
        OwnedPokemon = None

    inst = generate_pokemon(species, level=level)
    move_names = getattr(inst, "moves", [])
    if not move_names:
        move_names = ["Flail"]
    moves = [Move(name=m) for m in move_names]

    data = {}
    if hasattr(inst, "ivs"):
        data.update(
            {
                "ivs": {
                    "hp": getattr(inst.ivs, "hp", 0),
                    "atk": getattr(inst.ivs, "atk", 0),
                    "def": getattr(inst.ivs, "def_", 0),
                    "spa": getattr(inst.ivs, "spa", 0),
                    "spd": getattr(inst.ivs, "spd", 0),
                    "spe": getattr(inst.ivs, "spe", 0),
                },
                "evs": {stat: 0 for stat in ["hp", "atk", "def", "spa", "spd", "spe"]},
                "nature": getattr(inst, "nature", "Hardy"),
                "gender": getattr(inst, "gender", "N"),
            }
        )

    db_obj = None
    if OwnedPokemon:
        try:
            db_obj = OwnedPokemon.objects.create(
                species=inst.species.name,
                ability=getattr(inst, "ability", ""),
                nature=getattr(inst, "nature", ""),
                gender=getattr(inst, "gender", "N"),
                ivs=[
                    getattr(getattr(inst, "ivs", None), "hp", 0),
                    getattr(getattr(inst, "ivs", None), "atk", 0),
                    getattr(getattr(inst, "ivs", None), "def_", 0),
                    getattr(getattr(inst, "ivs", None), "spa", 0),
                    getattr(getattr(inst, "ivs", None), "spd", 0),
                    getattr(getattr(inst, "ivs", None), "spe", 0),
                ],
                evs=[0, 0, 0, 0, 0, 0],
                current_hp=getattr(inst.stats, "hp", level),
                ai_trainer=trainer,
                is_wild=is_wild,
            )
            db_obj.set_level(inst.level)
            db_obj.save()
        except Exception:
            db_obj = None

    return Pokemon(
        name=inst.species.name,
        level=inst.level,
        hp=getattr(db_obj, "current_hp", getattr(inst.stats, "hp", level)),
        max_hp=getattr(inst.stats, "hp", level),
        moves=moves,
        ability=getattr(inst, "ability", None),
        data=data,
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

        team_a = data.teams.get("A")
        team_b = data.teams.get("B")
        part_a = BattleParticipant(
            team_a.trainer, [p for p in team_a.returnlist() if p], is_ai=False
        )
        part_b = BattleParticipant(
            team_b.trainer, [p for p in team_b.returnlist() if p]
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
        return cls(battle, data, state)


class BattleSession:
    """Container representing an active battle in a room."""

    def __repr__(self) -> str:
        player = getattr(self.player, "key", getattr(self.player, "id", "?"))
        opp = (
            getattr(self.opponent, "key", getattr(self.opponent, "id", "?"))
            if self.opponent
            else None
        )
        return f"<BattleSession id={self.battle_id} player={player} opponent={opp}>"

    def __init__(self, player, opponent: Optional[object] = None):
        log_info(
            f"Initializing BattleSession {getattr(player, 'id', '?')} between {getattr(player, 'key', player)} and {getattr(opponent, 'key', opponent) if opponent else '<wild>'}"
        )
        self.player = player
        self.opponent = opponent
        self.room = getattr(player, "location", None)
        if self.room is None:
            raise ValueError("BattleSession requires the player to have a location")

        self.trainers: List[object] = (
            [player] if opponent is None else [player, opponent]
        )
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
            trainers = [t for t in (self.player, self.opponent) if t]
        else:
            trainers = self.trainers
        names = [getattr(t, "key", str(t)) for t in trainers]
        prefix = f"[Battle: {' vs. '.join(names)}]"
        msg = f"{prefix} {text}"
        for obj in trainers + list(self.observers):
            if hasattr(obj, "msg"):
                obj.msg(msg)

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
        obj.player = None
        obj.opponent = None
        obj.room = room
        obj.battle_id = battle_id
        obj.storage = storage
        obj.trainers = []
        obj.observers = set()
        obj.turn_state = {}
        logic = BattleLogic.from_dict({"data": data, "state": state})
        obj.logic = logic
        obj.temp_pokemon_ids = list(storage.get("temp_pokemon_ids") or [])
        log_info("Restored logic and temp Pokemon ids")

        trainer_info = storage.get("trainers", {}) or {}
        team_a = trainer_info.get("teamA", [])
        team_b = trainer_info.get("teamB", [])
        player_id = team_a[0] if team_a else None
        opponent_id = team_b[0] if team_b else None

        watcher_data = getattr(obj.state, "watchers", None) or {}
        if player_id and player_id not in watcher_data:
            watcher_data[player_id] = 1
        if opponent_id and opponent_id not in watcher_data:
            watcher_data[opponent_id] = 1
        obj.state.watchers = watcher_data

        team_a_objs = []
        for tid in team_a:
            targets = search_object(f"#{tid}")
            if targets:
                member = targets[0]
                team_a_objs.append(member)
                if obj.player is None:
                    obj.player = member
        team_b_objs = []
        for tid in team_b:
            targets = search_object(f"#{tid}")
            if targets:
                member = targets[0]
                team_b_objs.append(member)
                if obj.opponent is None:
                    obj.opponent = member

        watcher_data = getattr(obj.state, "watchers", None) or {}
        obj.watchers = set(watcher_data.keys())
        obj.watchers.update(team_a)
        obj.watchers.update(team_b)
        for wid in obj.watchers:
            log_info(f"Restoring watcher {wid}")
            if wid in team_a and team_a_objs:
                watcher = next((w for w in team_a_objs if getattr(w, 'id', 0) == wid), None)
            elif wid in team_b and team_b_objs:
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
            if wid in team_a:
                if obj.player is None:
                    obj.player = watcher
                if watcher not in team_a_objs:
                    team_a_objs.append(watcher)
                obj.trainers.append(watcher)
            elif wid in team_b:
                if obj.opponent is None:
                    obj.opponent = watcher
                if watcher not in team_b_objs:
                    team_b_objs.append(watcher)
                obj.trainers.append(watcher)
            else:
                obj.observers.add(watcher)
        if obj.player or obj.opponent:
            obj.trainers = team_a_objs + team_b_objs
        else:
            obj.trainers = []

        log_info(
            f"Restore complete: player={getattr(obj.player, 'key', obj.player)} "
            f"opponent={getattr(obj.opponent, 'key', obj.opponent) if obj.opponent else None} "
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
        room = self.player.location
        battle_id = self.battle_id
        existing_ids = getattr(room.db, "battles", None) or []
        if battle_id not in existing_ids:
            existing_ids.append(battle_id)
            room.db.battles = existing_ids

        if self.opponent:
            log_info("Opponent present, starting PvP")
            self.start_pvp()
            return

        origin = getattr(self.player, "location", None)
        opponent_poke, opponent_name, battle_type = self._select_opponent()
        player_pokemon = self._prepare_player_party(self.player)
        log_info(f"Prepared player party with {len(player_pokemon)} pokemon")
        self._init_battle_state(
            origin, player_pokemon, opponent_poke, opponent_name, battle_type
        )
        self._setup_battle_room()

    def start_pvp(self) -> None:
        """Start a battle between two players."""
        if not self.opponent:
            return

        origin = getattr(self.player, "location", None)

        log_info(
            f"Initializing PvP battle {self.battle_id} between {self.player.key} and {self.opponent.key}"
        )

        player_pokemon = self._prepare_player_party(self.player, full_heal=True)

        opp_pokemon = self._prepare_player_party(self.opponent)

        try:
            player_participant = BattleParticipant(
                self.player.key, player_pokemon, player=self.player
            )
        except TypeError:
            player_participant = BattleParticipant(self.player.key, player_pokemon)
        try:
            opponent_participant = BattleParticipant(
                self.opponent.key, opp_pokemon, player=self.opponent
            )
        except TypeError:
            opponent_participant = BattleParticipant(self.opponent.key, opp_pokemon)

        if player_participant.pokemons:
            player_participant.active = [player_participant.pokemons[0]]
        if opponent_participant.pokemons:
            opponent_participant.active = [opponent_participant.pokemons[0]]

        battle = Battle(BattleType.PVP, [player_participant, opponent_participant])

        team_a = Team(trainer=self.player.key, pokemon_list=player_pokemon)
        team_b = Team(trainer=self.opponent.key, pokemon_list=opp_pokemon)
        data = BattleData(team_a, team_b)

        state = BattleState.from_battle_data(data, ai_type="Player")
        state.roomweather = getattr(getattr(origin, "db", {}), "weather", "clear")
        state.pokemon_control = {}
        for poke in player_pokemon:
            if getattr(poke, "model_id", None):
                state.pokemon_control[str(poke.model_id)] = str(self.player.id)
        for poke in opp_pokemon:
            if getattr(poke, "model_id", None) and self.opponent:
                state.pokemon_control[str(poke.model_id)] = str(self.opponent.id)

        self.logic = BattleLogic(battle, data, state)
        log_info("PvP battle objects created")

        # persist battle info on the room
        self.storage.set("data", self.logic.data.to_dict())
        self.storage.set("state", self.logic.state.to_dict())
        self.storage.set("temp_pokemon_ids", list(self.temp_pokemon_ids))
        trainer_ids = {}
        if hasattr(self.player, "id"):
            trainer_ids.setdefault("teamA", []).append(self.player.id)
        if self.opponent and hasattr(self.opponent, "id"):
            trainer_ids.setdefault("teamB", []).append(self.opponent.id)
        if trainer_ids:
            self.storage.set("trainers", trainer_ids)
        log_info("Saved PvP battle data to room")

        add_watcher(self.state, self.player)
        add_watcher(self.state, self.opponent)
        self.watchers.update({self.player.id, self.opponent.id})
        self.player.ndb.battle_instance = self
        self.opponent.ndb.battle_instance = self
        if hasattr(self.player, "db"):
            self.player.db.battle_id = self.battle_id
        if hasattr(self.opponent, "db"):
            self.opponent.db.battle_id = self.battle_id
        self.msg("PVP battle started!")
        self.msg(f"Battle ID: {self.battle_id}")
        log_info(f"PvP battle {self.battle_id} started")
        notify_watchers(
            self.state,
            f"{self.player.key} and {self.opponent.key} begin a battle!",
            room=self.room,
        )

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
            opponent_poke = generate_wild_pokemon(self.player.location)
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
            level = getattr(poke, "level", 1)
            name = getattr(poke, "name", "Poke")
            stats = _calc_stats_from_model(poke)
            move_names = getattr(poke, "moves", None)
            slots = getattr(poke, "activemoveslot_set", None)
            if slots is None:
                active_ms = getattr(poke, "active_moveset", None)
                if active_ms is not None:
                    slots = getattr(active_ms, "slots", None)
            if not move_names and slots is not None:
                try:
                    iterable = slots.all().order_by("slot")
                except Exception:
                    try:
                        iterable = slots.order_by("slot")
                    except Exception:
                        iterable = slots
                move_names = [getattr(s.move, "name", "") for s in iterable]
            if not move_names:
                move_names = ["Flail"]
            moves = [Move(name=m) for m in move_names[:4]]
            current_hp = (
                stats.get("hp", level)
                if full_heal
                else getattr(poke, "current_hp", stats.get("hp", level))
            )
            battle_poke = Pokemon(
                    name=name,
                    level=level,
                    hp=current_hp,
                    max_hp=stats.get("hp", level),
                    moves=moves,
                    ability=getattr(poke, "ability", None),
                    data=getattr(poke, "data", {}),
                    model_id=(
                        str(getattr(poke, "unique_id", getattr(poke, "model_id", "")))
                        or None
                    ),
            )
            if slots is not None:
                battle_poke.activemoveslot_set = slots
            pokemons.append(battle_poke)
            log_info(f"Prepared {name} lvl {level}")
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
        log_info(f"Initializing battle state for {self.player.key} vs {opponent_name}")
        opponent_participant = BattleParticipant(
            opponent_name, [opponent_poke], is_ai=True
        )
        try:
            player_participant = BattleParticipant(
                self.player.key, player_pokemon, player=self.player
            )
        except TypeError:
            player_participant = BattleParticipant(self.player.key, player_pokemon)

        if player_participant.pokemons:
            player_participant.active = [player_participant.pokemons[0]]
        if opponent_participant.pokemons:
            opponent_participant.active = [opponent_participant.pokemons[0]]

        battle = Battle(battle_type, [player_participant, opponent_participant])

        player_team = Team(trainer=self.player.key, pokemon_list=player_pokemon)
        opponent_team = Team(trainer=opponent_name, pokemon_list=[opponent_poke])
        data = BattleData(player_team, opponent_team)

        state = BattleState.from_battle_data(data, ai_type=battle_type.name)
        state.roomweather = getattr(getattr(origin, "db", {}), "weather", "clear")
        state.pokemon_control = {}
        for poke in player_pokemon:
            if getattr(poke, "model_id", None):
                state.pokemon_control[str(poke.model_id)] = str(self.player.id)
        if getattr(opponent_poke, "model_id", None) and self.opponent:
            state.pokemon_control[str(opponent_poke.model_id)] = str(self.opponent.id)

        self.logic = BattleLogic(battle, data, state)
        log_info(f"Battle logic created with {len(player_pokemon)} player pokemon")

        # store battle info for restoration
        self.storage.set("data", self.logic.data.to_dict())
        self.storage.set("state", self.logic.state.to_dict())
        self.storage.set("temp_pokemon_ids", list(self.temp_pokemon_ids))
        trainer_ids = {}
        if hasattr(self.player, "id"):
            trainer_ids.setdefault("teamA", []).append(self.player.id)
        if self.opponent and hasattr(self.opponent, "id"):
            trainer_ids.setdefault("teamB", []).append(self.opponent.id)
        if trainer_ids:
            self.storage.set("trainers", trainer_ids)
        log_info(f"Saved battle data for id {self.battle_id}")

    def _setup_battle_room(self) -> None:
        """Move players to the battle room and notify watchers."""
        log_info(f"Setting up battle room for {self.battle_id}")
        add_watcher(self.state, self.player)
        if hasattr(self.player, "id"):
            self.watchers.add(self.player.id)
        self.player.ndb.battle_instance = self
        if hasattr(self.player, "db"):
            self.player.db.battle_id = self.battle_id
        self.msg("Battle started!")
        self.msg(f"Battle ID: {self.battle_id}")
        notify_watchers(
            self.state,
            f"{getattr(self.player, 'key', 'Player')} has entered battle!",
            room=self.room,
        )

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
        if self.player:
            if getattr(getattr(self.player, "ndb", None), "battle_instance", None):
                del self.player.ndb.battle_instance
            if hasattr(self.player, "db") and hasattr(self.player.db, "battle_id"):
                del self.player.db.battle_id
        if self.opponent:
            if getattr(getattr(self.opponent, "ndb", None), "battle_instance", None):
                del self.opponent.ndb.battle_instance
            if hasattr(self.opponent, "db") and hasattr(self.opponent.db, "battle_id"):
                del self.opponent.db.battle_id
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
        self.msg("The battle awaits your move.")
        if self.battle and getattr(self.battle, "turn_count", 0) == 1:
            log_info(f"Prompted first turn for battle {self.battle_id}")

    def run_turn(self) -> None:
        """Advance the battle by one turn."""
        if self.battle:
            log_info(f"Running turn for battle {self.battle_id}")
            self._set_player_control(False)
            self.battle.run_turn()
            self.prompt_next_turn()

    def queue_move(self, move_name: str, target: str = "B1") -> None:
        """Queue a move and run the turn if ready."""
        if not self.data or not self.battle:
            return
        pos = self.data.turndata.teamPositions("A").get("A1")
        if not pos:
            return
        pos.declareAttack(target, Move(name=move_name))
        log_info(f"Queued move {move_name} targeting {target}")
        self.storage.set("data", self.logic.data.to_dict())
        self.storage.set("state", self.logic.state.to_dict())
        log_info("Saved queued move to room data")
        self.maybe_run_turn()

    def is_turn_ready(self) -> bool:
        if not self.data:
            return False
        return all(p.getAction() for p in self.data.turndata.positions.values())

    def maybe_run_turn(self) -> None:
        if self.is_turn_ready():
            log_info(f"Turn ready for battle {self.battle_id}")
            self.run_turn()

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
