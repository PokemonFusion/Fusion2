from __future__ import annotations

import random
from typing import List

from evennia import create_object

from typeclasses.battleroom import BattleRoom
from .battledata import BattleData, Team, Pokemon, Move
from .engine import Battle, BattleParticipant, BattleType
from ..generation import generate_pokemon
from fusion2.world.pokemon_spawn import get_spawn


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

        self.player.ndb.battle_instance = self
        self.player.move_to(self.room, quiet=True)
        self.player.msg("Battle started!")

        # Run the opening turn immediately for demonstration
        self.battle.run_turn()

    def end(self) -> None:
        """End the battle and clean up."""
        if self.room:
            self.room.delete()
        if self.player.ndb.get("battle_instance"):
            del self.player.ndb.battle_instance
        self.battle = None
        self.player.msg("The battle has ended.")
