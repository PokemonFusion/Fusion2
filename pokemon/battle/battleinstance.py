from __future__ import annotations

import random
from typing import List

from evennia import create_object

from typeclasses.battleroom import BattleRoom
from .battledata import BattleData, Team, Pokemon
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
    return Pokemon(
        name=inst.species.name,
        level=inst.level,
        hp=inst.stats.hp,
        moves=list(inst.moves),
    )


def generate_trainer_pokemon() -> Pokemon:
    """Placeholder that returns a trainer's Charmander."""
    inst = generate_pokemon("Charmander", level=5)
    return Pokemon(
        name="Charmander",
        level=inst.level,
        hp=inst.stats.hp,
        moves=list(inst.moves),
    )


class BattleInstance:
    """Simple container for a temporary battle."""

    def __init__(self, player):
        self.player = player
        self.room = create_object(BattleRoom, key=f"Battle-{player.key}")
        self.room.db.instance = self
        self.data: BattleData | None = None

    def start(self) -> None:
        """Start a battle against a wild Pokémon or a trainer."""
        opponent_kind = random.choice(["pokemon", "trainer"])
        if opponent_kind == "pokemon":
            opponent_poke = generate_wild_pokemon(self.player.location)
            opponent_team = Team(trainer="Wild", pokemon_list=[opponent_poke])
            self.player.msg(f"A wild {opponent_poke.name} appears!")
        else:
            opponent_poke = generate_trainer_pokemon()
            opponent_team = Team(trainer="Trainer", pokemon_list=[opponent_poke])
            self.player.msg(
                f"A trainer challenges you with {opponent_poke.name}!"
            )

        player_pokemon: List[Pokemon] = []
        for poke in self.player.storage.active_pokemon.all():
            inst = generate_pokemon(poke.name, level=poke.level)
            player_pokemon.append(
                Pokemon(
                    name=inst.species.name,
                    level=inst.level,
                    hp=inst.stats.hp,
                    moves=list(inst.moves),
                )
            )

        player_team = Team(trainer=self.player.key, pokemon_list=player_pokemon)
        self.data = BattleData(player_team, opponent_team)

        self.player.ndb.battle_instance = self
        self.player.move_to(self.room, quiet=True)
        self.player.msg("Battle started!")

    def end(self) -> None:
        """End the battle and clean up."""
        if self.room:
            self.room.delete()
        if self.player.ndb.get("battle_instance"):
            del self.player.ndb.battle_instance
        self.player.msg("The battle has ended.")
