from __future__ import annotations

import random
from typing import List

from evennia import create_object

from typeclasses.battleroom import BattleRoom
from .battledata import BattleData, Team, Pokemon, Move
from .engine import Battle, BattleParticipant, BattleType
from .state import BattleState
from .interface import add_watcher, notify_watchers, remove_watcher
from ..generation import generate_pokemon
from world.pokemon_spawn import get_spawn


def generate_wild_pokemon(location=None) -> Pokemon:
    """Generate a wild Pokémon based on the supplied location."""

    if location:
        inst = get_spawn(location)
    else:
        inst = None
    if not inst:
        inst = generate_pokemon("Pikachu", level=5)
    moves = [Move(name=m) for m in inst.moves]
    return Pokemon(name=inst.species.name, level=inst.level, hp=inst.stats.hp, moves=moves)


def generate_trainer_pokemon() -> Pokemon:
    """Placeholder that returns a trainer's Charmander."""
    inst = generate_pokemon("Charmander", level=5)
    moves = [Move(name=m) for m in inst.moves]
    return Pokemon(name=inst.species.name, level=inst.level, hp=inst.stats.hp, moves=moves)


class BattleInstance:
    """Simple container for a temporary battle."""

    def __init__(self, player):
        self.player = player
        self.room = create_object(BattleRoom, key=f"Battle-{player.key}")
        self.room.db.instance = self
        self.data: BattleData | None = None
        self.battle: Battle | None = None
        self.state: BattleState | None = None
        self.watchers: set[int] = set()

    def start(self) -> None:
        """Start a battle against a wild Pokémon or a trainer."""
        opponent_kind = random.choice(["pokemon", "trainer"])
        if opponent_kind == "pokemon":
            opponent_poke = generate_wild_pokemon(self.player.location)
            battle_type = BattleType.WILD
            opponent_name = "Wild"
            self.player.msg(f"A wild {opponent_poke.name} appears!")
        else:
            opponent_poke = generate_trainer_pokemon()
            battle_type = BattleType.TRAINER
            opponent_name = "Trainer"
            self.player.msg(
                f"A trainer challenges you with {opponent_poke.name}!"
            )

        opponent_participant = BattleParticipant(
            opponent_name, [opponent_poke], is_ai=True
        )

        player_pokemon: List[Pokemon] = []
        for poke in self.player.storage.active_pokemon.all():
            inst = generate_pokemon(poke.name, level=poke.level)
            moves = [Move(name=m) for m in inst.moves]
            player_pokemon.append(
                Pokemon(
                    name=inst.species.name,
                    level=inst.level,
                    hp=inst.stats.hp,
                    moves=moves,
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
        self.room.db.battle_state = self.state.to_dict()
        add_watcher(self.state, self.player)
        self.watchers.add(self.player.id)

        self.player.ndb.battle_instance = self
        self.player.move_to(self.room, quiet=True)
        self.player.msg("Battle started!")
        notify_watchers(self.state, f"{self.player.key} has entered battle!", room=self.room)

        # Run the opening turn immediately for demonstration
        self.battle.run_turn()

    def end(self) -> None:
        """End the battle and clean up."""
        if self.room:
            self.room.delete()
        if self.player.ndb.get("battle_instance"):
            del self.player.ndb.battle_instance
        self.battle = None
        if self.state:
            notify_watchers(self.state, "The battle has ended.", room=self.room)
        self.watchers.clear()
        self.state = None
        self.player.msg("The battle has ended.")

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
