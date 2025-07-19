from __future__ import annotations

import random
from typing import List, Optional

from evennia import search_object

from typeclasses.rooms import BattleRoom
from .battledata import BattleData, Team, Pokemon, Move
from .engine import Battle, BattleParticipant, BattleType
from .state import BattleState
from .interface import add_watcher, notify_watchers, remove_watcher
from .handler import battle_handler
from ..generation import generate_pokemon
from world.pokemon_spawn import get_spawn


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


class BattleInstance:
    """Container representing an active battle in a room."""

    def __repr__(self) -> str:
        player = getattr(self.player, "key", getattr(self.player, "id", "?"))
        opp = getattr(self.opponent, "key", getattr(self.opponent, "id", "?")) if self.opponent else None
        return f"<BattleInstance id={self.battle_id} player={player} opponent={opp}>"

    def __init__(self, player, opponent: Optional[object] = None):
        self.player = player
        self.opponent = opponent
        self.room = getattr(player, "location", None)
        if self.room is None:
            raise ValueError("BattleInstance requires the player to have a location")

        self.trainers: List[object] = [player] if opponent is None else [player, opponent]
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
        if not isinstance(battle_instances, dict):
            battle_instances = {}
            self.room.ndb.battle_instances = battle_instances
        battle_instances[self.battle_id] = self

        battles = getattr(self.room.db, "battles", None)
        if not isinstance(battles, list):
            battles = []
            setattr(self.room.db, "battles", battles)
        if self.battle_id not in battles:
            battles.append(self.battle_id)

        self.data: BattleData | None = None
        self.battle: Battle | None = None
        self.state: BattleState | None = None
        self.watchers: set[int] = set()
        self.temp_pokemon_ids: List[int] = []

    # ------------------------------------------------------------
    # Helper utilities
    # ------------------------------------------------------------

    @staticmethod
    def ensure_for_player(player) -> "BattleInstance | None":
        """Return the active battle instance for ``player`` if possible.

        This checks ``player.ndb.battle_instance`` first, then tries to
        rebuild it from persistent data on the player's room. It returns
        the instance if found, otherwise ``None``.
        """

        inst = getattr(player.ndb, "battle_instance", None)
        if inst:
            return inst

        room = getattr(player, "location", None)
        if not room:
            return None

        bid = getattr(player.db, "battle_id", None)
        if bid is None:
            return None

        bmap = getattr(getattr(room, "ndb", None), "battle_instances", None)
        if isinstance(bmap, dict):
            inst = bmap.get(bid)
            if inst:
                player.ndb.battle_instance = inst
                return inst

        # try restoring from persistent room data
        inst = BattleInstance.restore(room, bid)
        if inst:
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
    def restore(cls, room, battle_id: int) -> "BattleInstance | None":
        """Recreate an instance from a stored battle on a room."""
        data = getattr(room.db, f"battle_data_{battle_id}", None)
        state = getattr(room.db, f"battle_state_{battle_id}", None)
        if not data or not state:
            return None
        obj = cls.__new__(cls)
        obj.player = None
        obj.opponent = None
        obj.room = room
        obj.battle_id = battle_id
        obj.trainers = []
        obj.observers = set()
        obj.turn_state = {}
        if not hasattr(room.ndb, "battle_instances"):
            room.ndb.battle_instances = {}
        room.ndb.battle_instances[battle_id] = obj
        battles = getattr(room.db, "battles", None)
        if not isinstance(battles, list):
            battles = []
            setattr(room.db, "battles", battles)
        if battle_id not in battles:
            battles.append(battle_id)
        obj.data = BattleData.from_dict(data)
        obj.battle = obj.data.battle
        obj.state = BattleState.from_dict(state)
        obj.watchers = set(obj.state.watchers.keys())
        obj.temp_pokemon_ids = list(getattr(room.db, f"temp_pokemon_ids_{battle_id}", []))
        for wid in obj.watchers:
            targets = search_object(wid)
            if not targets:
                continue
            watcher = targets[0]
            watcher.ndb.battle_instance = obj
            if hasattr(watcher, "db"):
                watcher.db.battle_id = battle_id
            if obj.player is None:
                obj.player = watcher
            elif obj.opponent is None:
                obj.opponent = watcher
        obj.trainers = [t for t in (obj.player, obj.opponent) if t]
        return obj

    def start(self) -> None:
        """Start a battle against a wild Pokémon, trainer or another player."""
        if self.opponent:
            self.start_pvp()
            return

        origin = getattr(self.player, "location", None)
        opponent_poke, opponent_name, battle_type = self._select_opponent()
        player_pokemon = self._prepare_player_party(self.player)
        self._init_battle_state(origin, player_pokemon, opponent_poke, opponent_name, battle_type)
        self._setup_battle_room()

    def start_pvp(self) -> None:
        """Start a battle between two players."""
        if not self.opponent:
            return

        origin = getattr(self.player, "location", None)

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

        self.battle = Battle(BattleType.PVP, [player_participant, opponent_participant])

        team_a = Team(trainer=self.player.key, pokemon_list=player_pokemon)
        team_b = Team(trainer=self.opponent.key, pokemon_list=opp_pokemon)
        self.data = BattleData(team_a, team_b)

        setattr(self.room.db, f"battle_data_{self.battle_id}", self.data.to_dict())
        self.state = BattleState.from_battle_data(self.data, ai_type="Player")
        self.state.roomweather = getattr(getattr(origin, "db", {}), "weather", "clear")
        setattr(self.room.db, f"battle_state_{self.battle_id}", self.state.to_dict())

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
        notify_watchers(
            self.state,
            f"{self.player.key} and {self.opponent.key} begin a battle!",
            room=self.room,
        )

        self.prompt_first_turn()
        battle_handler.register(self)

    # ------------------------------------------------------------------
    # Helper methods extracted from ``start``
    # ------------------------------------------------------------------
    def _select_opponent(self) -> tuple[Pokemon, str, BattleType]:
        """Return the opponent Pokemon, its name and the battle type."""
        opponent_kind = random.choice(["pokemon", "trainer"])
        if opponent_kind == "pokemon":
            opponent_poke = generate_wild_pokemon(self.player.location)
            if getattr(opponent_poke, "model_id", None):
                self.temp_pokemon_ids.append(opponent_poke.model_id)
            battle_type = BattleType.WILD
            opponent_name = "Wild"
            self.msg(f"A wild {opponent_poke.name} appears!")
        else:
            opponent_poke = generate_trainer_pokemon()
            if getattr(opponent_poke, "model_id", None):
                self.temp_pokemon_ids.append(opponent_poke.model_id)
            battle_type = BattleType.TRAINER
            opponent_name = "Trainer"
            self.msg(
                f"A trainer challenges you with {opponent_poke.name}!"
            )
        return opponent_poke, opponent_name, battle_type

    def _prepare_player_party(self, trainer, full_heal: bool = False) -> List[Pokemon]:
        """Return a list of battle-ready Pokemon for a trainer.

        If ``full_heal`` is ``True`` the Pokémon start with full HP regardless
        of any stored current HP value. This mirrors the behaviour used when
        starting PvP battles where all participant Pokémon begin at full health.
        """
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
            move_names = getattr(poke, "moves", [])
            if not move_names:
                move_names = ["Flail"]
            moves = [Move(name=m) for m in move_names[:4]]
            current_hp = (
                stats.get("hp", level)
                if full_heal
                else getattr(poke, "current_hp", stats.get("hp", level))
            )
            pokemons.append(
                Pokemon(
                    name=name,
                    level=level,
                    hp=current_hp,
                    max_hp=stats.get("hp", level),
                    moves=moves,
                    ability=getattr(poke, "ability", None),
                    data=getattr(poke, "data", {}),
                )
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

        self.battle = Battle(battle_type, [player_participant, opponent_participant])

        player_team = Team(trainer=self.player.key, pokemon_list=player_pokemon)
        opponent_team = Team(trainer=opponent_name, pokemon_list=[opponent_poke])
        self.data = BattleData(player_team, opponent_team)

        setattr(self.room.db, f"battle_data_{self.battle_id}", self.data.to_dict())
        self.state = BattleState.from_battle_data(self.data, ai_type=battle_type.name)
        self.state.roomweather = getattr(getattr(origin, "db", {}), "weather", "clear")
        setattr(self.room.db, f"battle_state_{self.battle_id}", self.state.to_dict())
        setattr(self.room.db, f"temp_pokemon_ids_{self.battle_id}", list(self.temp_pokemon_ids))

    def _setup_battle_room(self) -> None:
        """Move players to the battle room and notify watchers."""
        add_watcher(self.state, self.player)
        if hasattr(self.player, "id"):
            self.watchers.add(self.player.id)
        self.player.ndb.battle_instance = self
        if hasattr(self.player, "db"):
            self.player.db.battle_id = self.battle_id
        self.msg("Battle started!")
        self.msg(f"Battle ID: {self.battle_id}")
        notify_watchers(
            self.state, f"{getattr(self.player, 'key', 'Player')} has entered battle!", room=self.room
        )

        self.prompt_first_turn()
        battle_handler.register(self)

    def end(self) -> None:
        """End the battle and clean up."""
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
                battle_slot__fainted=True,
            ).delete()
        self.temp_pokemon_ids.clear()
        if self.room:
            if hasattr(self.room.ndb, "battle_instances"):
                self.room.ndb.battle_instances.pop(self.battle_id, None)
                if not self.room.ndb.battle_instances:
                    del self.room.ndb.battle_instances
            if hasattr(self.room.db, f"battle_data_{self.battle_id}"):
                delattr(self.room.db, f"battle_data_{self.battle_id}")
            if hasattr(self.room.db, f"battle_state_{self.battle_id}"):
                delattr(self.room.db, f"battle_state_{self.battle_id}")
            if hasattr(self.room.db, f"temp_pokemon_ids_{self.battle_id}"):
                delattr(self.room.db, f"temp_pokemon_ids_{self.battle_id}")
            battles = getattr(self.room.db, "battles", None)
            if isinstance(battles, list) and self.battle_id in battles:
                battles.remove(self.battle_id)
                if not battles:
                    delattr(self.room.db, "battles")
        if getattr(self.player.ndb, "battle_instance", None):
            del self.player.ndb.battle_instance
        if hasattr(self.player, "db"):
            if hasattr(self.player.db, "battle_id"):
                del self.player.db.battle_id
        if self.opponent and getattr(self.opponent.ndb, "battle_instance", None):
            del self.opponent.ndb.battle_instance
        if self.opponent and hasattr(self.opponent, "db"):
            if hasattr(self.opponent.db, "battle_id"):
                del self.opponent.db.battle_id
        self.battle = None
        if self.state:
            notify_watchers(self.state, "The battle has ended.", room=self.room)
        self.watchers.clear()
        self.state = None
        battle_handler.unregister(self)
        self.msg("The battle has ended.")

    # ------------------------------------------------------------------
    # Battle helpers
    # ------------------------------------------------------------------
    def prompt_first_turn(self) -> None:
        """Notify the player that the battle is ready to begin."""
        self.msg("The battle awaits your move.")

    def run_turn(self) -> None:
        """Advance the battle by one turn."""
        if self.battle:
            self.battle.run_turn()

    def queue_move(self, move_name: str, target: str = "B1") -> None:
        """Queue a move and run the turn if ready."""
        if not self.data or not self.battle:
            return
        pos = self.data.turndata.teamPositions("A").get("A1")
        if not pos:
            return
        pos.declareAttack(target, Move(name=move_name))
        setattr(self.room.db, f"battle_data_{self.battle_id}", self.data.to_dict())
        self.maybe_run_turn()

    def is_turn_ready(self) -> bool:
        if not self.data:
            return False
        return all(p.getAction() for p in self.data.turndata.positions.values())

    def maybe_run_turn(self) -> None:
        if self.is_turn_ready():
            self.run_turn()

    # ------------------------------------------------------------------
    # Watcher helpers
    # ------------------------------------------------------------------
    def add_watcher(self, watcher) -> None:
        if not self.state:
            return
        add_watcher(self.state, watcher)
        self.watchers.add(watcher.id)

    def remove_watcher(self, watcher) -> None:
        if not self.state:
            return
        remove_watcher(self.state, watcher)
        self.watchers.discard(watcher.id)

    def notify(self, message: str) -> None:
        if not self.state:
            return
        notify_watchers(self.state, message, room=self.room)

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

    def remove_observer(self, watcher) -> None:
        if watcher in self.observers:
            self.observers.discard(watcher)
            if getattr(watcher.ndb, "battle_instance", None) == self:
                del watcher.ndb.battle_instance
            if self.state:
                remove_watcher(self.state, watcher)
                self.watchers.discard(getattr(watcher, "id", 0))
