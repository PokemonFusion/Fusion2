from __future__ import annotations

import random
from typing import List

from evennia import create_object

from typeclasses.battleroom import BattleRoom
from .battledata import BattleData, Team, Pokemon


def generate_wild_pokemon() -> Pokemon:
    """Placeholder that returns a simple Pikachu."""
    return Pokemon(name="Pikachu", level=5, hp=35)


def generate_trainer_pokemon() -> Pokemon:
    """Placeholder that returns a trainer's Charmander."""
    return Pokemon(name="Charmander", level=5, hp=39)


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
            opponent_poke = generate_wild_pokemon()
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
            player_pokemon.append(Pokemon(name=poke.name, level=poke.level, hp=100))

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
