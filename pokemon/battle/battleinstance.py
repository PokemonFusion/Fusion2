from __future__ import annotations

import random
from typing import List, Optional

from evennia import create_object, search_object

from typeclasses.battleroom import BattleRoom
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
    try:
        if calculate_stats:
            return calculate_stats(poke.name, poke.level, ivs, evs, nature)
        raise Exception
    except Exception:
        inst = generate_pokemon(poke.name, level=poke.level)
        st = getattr(inst, "stats", inst)
        return {
            "hp": getattr(st, "hp", 100),
            "atk": getattr(st, "atk", 0),
            "def": getattr(st, "def_", 0),
            "spa": getattr(st, "spa", 0),
            "spd": getattr(st, "spd", 0),
            "spe": getattr(st, "spe", 0),
        }


def generate_wild_pokemon(location=None) -> Pokemon:
    """Generate a wild Pokémon based on the supplied location."""

    try:
        from ..models import Pokemon as PokemonModel
    except Exception:  # pragma: no cover - optional in tests
        PokemonModel = None

    if location:
        inst = get_spawn(location)
    else:
        inst = None
    if not inst:
        inst = generate_pokemon("Pikachu", level=5)
    moves = [Move(name=m) for m in inst.moves]
    data = {}
    if hasattr(inst, "ivs"):
        data.update(
            {
                "ivs": {
                    "hp": inst.ivs.hp,
                    "atk": inst.ivs.atk,
                    "def": inst.ivs.def_,
                    "spa": inst.ivs.spa,
                    "spd": inst.ivs.spd,
                    "spe": inst.ivs.spe,
                },
                "evs": {stat: 0 for stat in ["hp", "atk", "def", "spa", "spd", "spe"]},
                "nature": getattr(inst, "nature", "Hardy"),
                "gender": getattr(inst, "gender", "N"),
            }
        )
    db_obj = None
    if PokemonModel:
        db_obj = PokemonModel.objects.create(
            name=inst.species.name,
            level=inst.level,
            type_=", ".join(getattr(inst.species, "types", [])),
            ability=getattr(inst, "ability", ""),
            data=data,
            temporary=True,
        )
    return Pokemon(
        name=inst.species.name,
        level=inst.level,
        hp=inst.stats.hp,
        max_hp=inst.stats.hp,
        moves=moves,
        ability=inst.ability,
        data=data,
        model_id=db_obj.id if db_obj else None,
    )


def generate_trainer_pokemon() -> Pokemon:
    """Placeholder that returns a trainer's Charmander."""
    try:
        from ..models import Pokemon as PokemonModel
    except Exception:  # pragma: no cover
        PokemonModel = None
    inst = generate_pokemon("Charmander", level=5)
    moves = [Move(name=m) for m in inst.moves]
    data = {}
    if hasattr(inst, "ivs"):
        data.update(
            {
                "ivs": {
                    "hp": inst.ivs.hp,
                    "atk": inst.ivs.atk,
                    "def": inst.ivs.def_,
                    "spa": inst.ivs.spa,
                    "spd": inst.ivs.spd,
                    "spe": inst.ivs.spe,
                },
                "evs": {stat: 0 for stat in ["hp", "atk", "def", "spa", "spd", "spe"]},
                "nature": getattr(inst, "nature", "Hardy"),
                "gender": getattr(inst, "gender", "N"),
            }
        )
    db_obj = None
    if PokemonModel:
        db_obj = PokemonModel.objects.create(
            name=inst.species.name,
            level=inst.level,
            type_=", ".join(getattr(inst.species, "types", [])),
            ability=getattr(inst, "ability", ""),
            data=data,
            temporary=True,
        )
    return Pokemon(
        name=inst.species.name,
        level=inst.level,
        hp=inst.stats.hp,
        max_hp=inst.stats.hp,
        moves=moves,
        ability=inst.ability,
        data=data,
        model_id=db_obj.id if db_obj else None,
    )


class BattleInstance:
    """Simple container for a temporary battle."""

    def __init__(self, player, opponent: Optional[object] = None):
        self.player = player
        self.opponent = opponent
        self.room = create_object(BattleRoom, key=f"Battle-{player.key}")
        self.room.db.instance = self
        self.data: BattleData | None = None
        self.battle: Battle | None = None
        self.state: BattleState | None = None
        self.watchers: set[int] = set()
        self.temp_pokemon_ids: List[int] = []

    @classmethod
    def restore(cls, room) -> "BattleInstance | None":
        """Recreate an instance from a stored battle room."""
        data = getattr(room.db, "battle_data", None)
        state = getattr(room.db, "battle_state", None)
        if not data or not state:
            return None
        obj = cls.__new__(cls)
        obj.player = None
        obj.opponent = None
        obj.room = room
        room.db.instance = obj
        obj.data = BattleData.from_dict(data)
        obj.battle = obj.data.battle
        obj.state = BattleState.from_dict(state)
        obj.watchers = set(obj.state.watchers.keys())
        obj.temp_pokemon_ids = list(getattr(room.db, "temp_pokemon_ids", []))
        for wid in obj.watchers:
            targets = search_object(wid)
            if targets:
                targets[0].ndb.battle_instance = obj
        return obj

    def start(self) -> None:
        """Start a battle against a wild Pokémon, trainer or another player."""
        if self.opponent:
            self.start_pvp()
            return

        origin = self.player.location

        opponent_kind = random.choice(["pokemon", "trainer"])
        if opponent_kind == "pokemon":
            opponent_poke = generate_wild_pokemon(self.player.location)
            if getattr(opponent_poke, "model_id", None):
                self.temp_pokemon_ids.append(opponent_poke.model_id)
            battle_type = BattleType.WILD
            opponent_name = "Wild"
            self.player.msg(f"A wild {opponent_poke.name} appears!")
        else:
            opponent_poke = generate_trainer_pokemon()
            if getattr(opponent_poke, "model_id", None):
                self.temp_pokemon_ids.append(opponent_poke.model_id)
            battle_type = BattleType.TRAINER
            opponent_name = "Trainer"
            self.player.msg(
                f"A trainer challenges you with {opponent_poke.name}!"
            )

        opponent_participant = BattleParticipant(
            opponent_name, [opponent_poke], is_ai=True
        )

        player_pokemon: List[Pokemon] = []
        party = (
            self.player.storage.get_party()
            if hasattr(self.player.storage, "get_party")
            else list(self.player.storage.active_pokemon.all())
        )
        for poke in party:
            stats = _calc_stats_from_model(poke)
            moves = [Move(name=m) for m in getattr(poke, "moves", [])[:4]]
            player_pokemon.append(
                Pokemon(
                    name=poke.name,
                    level=poke.level,
                    hp=stats.get("hp", poke.level),
                    max_hp=stats.get("hp", poke.level),
                    moves=moves,
                    ability=getattr(poke, "ability", None),
                    data=getattr(poke, "data", {}),
                )
            )

        player_participant = BattleParticipant(self.player.key, player_pokemon)

        # Set the first Pokémon of each side as active
        if player_participant.pokemons:
            player_participant.active = [player_participant.pokemons[0]]
        if opponent_participant.pokemons:
            opponent_participant.active = [opponent_participant.pokemons[0]]

        self.battle = Battle(battle_type, [player_participant, opponent_participant])

        player_team = Team(trainer=self.player.key, pokemon_list=player_pokemon)
        opponent_team = Team(trainer=opponent_name, pokemon_list=[opponent_poke])
        self.data = BattleData(player_team, opponent_team)
        # Store a serialisable snapshot on the room for later use
        self.room.db.battle_data = self.data.to_dict()
        self.state = BattleState.from_battle_data(self.data, ai_type=battle_type.name)
        self.state.roomweather = getattr(getattr(origin, "db", {}), "weather", "clear")
        self.room.db.battle_state = self.state.to_dict()
        self.room.db.temp_pokemon_ids = list(self.temp_pokemon_ids)
        add_watcher(self.state, self.player)
        self.watchers.add(self.player.id)

        self.player.ndb.battle_instance = self
        self.player.move_to(self.room, quiet=True)
        self.player.msg("Battle started!")
        bid = getattr(self.room, "id", 0)
        self.player.msg(f"Battle ID: {bid}")
        notify_watchers(self.state, f"{self.player.key} has entered battle!", room=self.room)

        # Let the player know the battle is ready for input
        self.prompt_first_turn()
        battle_handler.register(self)

    def start_pvp(self) -> None:
        """Start a battle between two players."""
        if not self.opponent:
            return

        origin = self.player.location

        player_pokemon: List[Pokemon] = []
        party = (
            self.player.storage.get_party()
            if hasattr(self.player.storage, "get_party")
            else list(self.player.storage.active_pokemon.all())
        )
        for poke in party:
            stats = _calc_stats_from_model(poke)
            moves = [Move(name=m) for m in getattr(poke, "moves", [])[:4]]
            player_pokemon.append(
                Pokemon(
                    name=poke.name,
                    level=poke.level,
                    hp=stats.get("hp", poke.level),
                    max_hp=stats.get("hp", poke.level),
                    moves=moves,
                    ability=getattr(poke, "ability", None),
                    data=getattr(poke, "data", {}),
                )
            )

        opp_pokemon: List[Pokemon] = []
        party = (
            self.opponent.storage.get_party()
            if hasattr(self.opponent.storage, "get_party")
            else list(self.opponent.storage.active_pokemon.all())
        )
        for poke in party:
            stats = _calc_stats_from_model(poke)
            moves = [Move(name=m) for m in getattr(poke, "moves", [])[:4]]
            opp_pokemon.append(
                Pokemon(
                    name=poke.name,
                    level=poke.level,
                    hp=stats.get("hp", poke.level),
                    max_hp=stats.get("hp", poke.level),
                    moves=moves,
                    ability=getattr(poke, "ability", None),
                    data=getattr(poke, "data", {}),
                )
            )

        player_participant = BattleParticipant(self.player.key, player_pokemon)
        opponent_participant = BattleParticipant(self.opponent.key, opp_pokemon)

        if player_participant.pokemons:
            player_participant.active = [player_participant.pokemons[0]]
        if opponent_participant.pokemons:
            opponent_participant.active = [opponent_participant.pokemons[0]]

        self.battle = Battle(BattleType.PVP, [player_participant, opponent_participant])

        team_a = Team(trainer=self.player.key, pokemon_list=player_pokemon)
        team_b = Team(trainer=self.opponent.key, pokemon_list=opp_pokemon)
        self.data = BattleData(team_a, team_b)

        self.room.db.battle_data = self.data.to_dict()
        self.state = BattleState.from_battle_data(self.data, ai_type="Player")
        self.state.roomweather = getattr(getattr(origin, "db", {}), "weather", "clear")
        self.room.db.battle_state = self.state.to_dict()

        add_watcher(self.state, self.player)
        add_watcher(self.state, self.opponent)
        self.watchers.update({self.player.id, self.opponent.id})

        self.player.ndb.battle_instance = self
        self.opponent.ndb.battle_instance = self
        self.player.move_to(self.room, quiet=True)
        self.opponent.move_to(self.room, quiet=True)
        self.player.msg("PVP battle started!")
        self.opponent.msg("PVP battle started!")
        bid = getattr(self.room, "id", 0)
        self.player.msg(f"Battle ID: {bid}")
        self.opponent.msg(f"Battle ID: {bid}")
        notify_watchers(
            self.state,
            f"{self.player.key} and {self.opponent.key} begin a battle!",
            room=self.room,
        )

        self.prompt_first_turn()
        battle_handler.register(self)

    def end(self) -> None:
        """End the battle and clean up."""
        try:
            from ..models import Pokemon as PokemonModel
        except Exception:  # pragma: no cover
            PokemonModel = None
        for pid in getattr(self, "temp_pokemon_ids", []):
            try:
                if PokemonModel:
                    poke = PokemonModel.objects.get(id=pid)
                    if getattr(poke, "temporary", False):
                        poke.delete()
            except Exception:
                pass
        self.temp_pokemon_ids.clear()
        if self.room:
            if hasattr(self.room.db, "instance"):
                del self.room.db.instance
            if hasattr(self.room.db, "battle_data"):
                del self.room.db.battle_data
            if hasattr(self.room.db, "battle_state"):
                del self.room.db.battle_state
            if hasattr(self.room.db, "temp_pokemon_ids"):
                del self.room.db.temp_pokemon_ids
            self.room.delete()
        if self.player.ndb.get("battle_instance"):
            del self.player.ndb.battle_instance
        if self.opponent and self.opponent.ndb.get("battle_instance"):
            del self.opponent.ndb.battle_instance
        self.battle = None
        if self.state:
            notify_watchers(self.state, "The battle has ended.", room=self.room)
        self.watchers.clear()
        self.state = None
        battle_handler.unregister(self)
        self.player.msg("The battle has ended.")
        if self.opponent:
            self.opponent.msg("The battle has ended.")

    # ------------------------------------------------------------------
    # Battle helpers
    # ------------------------------------------------------------------
    def prompt_first_turn(self) -> None:
        """Notify the player that the battle is ready to begin."""
        self.player.msg("The battle awaits your move.")

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
        self.room.db.battle_data = self.data.to_dict()
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
