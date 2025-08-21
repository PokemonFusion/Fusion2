"""Commands for learning moves and evolving Pokémon.

This module contains commands related to move teaching, learning and
evolution mechanics.
"""

from evennia import Command


class CmdChooseMoveset(Command):
    """Select which stored moveset a Pokémon should use.

    Usage:
      +moveset <slot>=<set#>
    """

    key = "+moveset"
    locks = "cmd:all()"
    help_category = "Pokemon"

    def parse(self):
        if "=" not in self.args:
            self.slot = self.index = None
            return
        left, right = [p.strip() for p in self.args.split("=", 1)]
        try:
            self.slot = int(left)
            self.index = int(right) - 1
        except ValueError:
            self.slot = self.index = None

    def func(self):
        if self.slot is None or self.index is None:
            self.caller.msg("Usage: +moveset <slot>=<set#>")
            return
        pokemon = self.caller.get_active_pokemon_by_slot(self.slot)
        if not pokemon:
            self.caller.msg("No Pokémon in that slot.")
            return
        sets = list(pokemon.movesets.order_by("index"))
        if self.index < 0 or self.index >= len(sets):
            self.caller.msg("Invalid moveset number.")
            return
        pokemon.swap_moveset(self.index)
        self.caller.msg(f"{pokemon.name} is now using moveset {self.index + 1}.")


class CmdTeachMove(Command):
    """Teach a move to one of your active Pokémon.

    Usage:
      +move <slot>=<move>
    """

    key = "+move"
    locks = "cmd:all()"
    help_category = "Pokemon"

    def parse(self):
        if "=" not in self.args:
            self.slot = None
            self.move_name = ""
            return
        left, right = [p.strip() for p in self.args.split("=", 1)]
        try:
            self.slot = int(left)
        except ValueError:
            self.slot = None
        self.move_name = right.strip()

    def func(self):
        if self.slot is None or not self.move_name:
            self.caller.msg("Usage: +move <slot>=<move>")
            return
        pokemon = self.caller.get_active_pokemon_by_slot(self.slot)
        if not pokemon:
            self.caller.msg("No Pokémon in that slot.")
            return
        from pokemon.data.generation import get_valid_moves
        from pokemon.models.moves import Move

        valid = [
            m.lower() for m in get_valid_moves(pokemon.species, pokemon.computed_level)
        ]
        if self.move_name.lower() not in valid:
            self.caller.msg(f"{pokemon.name} cannot learn {self.move_name}.")
            return
        if pokemon.learned_moves.filter(name__iexact=self.move_name).exists():
            self.caller.msg(f"{pokemon.name} already knows {self.move_name}.")
            return

        from pokemon.utils.move_learning import learn_move

        learn_move(pokemon, self.move_name, caller=self.caller, prompt=True)


class CmdLearn(Command):
    """Learn level-up moves for a Pokémon.

    Usage:
      +learn <slot>
    """

    key = "+learn"
    locks = "cmd:all()"
    help_category = "Pokemon"

    def parse(self):
        try:
            self.slot = int(self.args.strip())
        except (TypeError, ValueError):
            self.slot = None

    def func(self):
        from pokemon.utils.move_learning import get_learnable_levelup_moves

        if self.slot is None:
            lines = []
            for idx in range(1, 7):
                poke = self.caller.get_active_pokemon_by_slot(idx)
                if not poke:
                    continue
                moves, _ = get_learnable_levelup_moves(poke)
                if moves:
                    lines.append(
                        f"Slot {idx}: {poke.name} ({len(moves)} move{'s' if len(moves) != 1 else ''})"
                    )
            if lines:
                self.caller.msg("Pokémon with moves to learn:\n" + "\n".join(lines))
            else:
                self.caller.msg("None of your Pokémon have moves to learn.")
            return

        pokemon = self.caller.get_active_pokemon_by_slot(self.slot)
        if not pokemon:
            self.caller.msg("No Pokémon in that slot.")
            return

        moves, level_map = get_learnable_levelup_moves(pokemon)
        if not moves:
            self.caller.msg(f"{pokemon.name} has no moves to learn.")
            return

        from utils.enhanced_evmenu import EnhancedEvMenu
        from menus import learn_new_moves as learn_menu

        EnhancedEvMenu(
            self.caller,
            learn_menu,
            startnode="node_start",
            start_kwargs={"pokemon": pokemon, "moves": moves, "level_map": level_map},
            cmd_on_exit=None,
        )


class CmdEvolvePokemon(Command):
    """Evolve one of your Pokémon if possible.

    Usage:
      evolve <pokemon_id> [item]
    """

    key = "evolve"
    locks = "cmd:all()"
    help_category = "Pokemon"

    def func(self):
        """Attempt to evolve one of the player's Pokémon."""
        parts = self.args.split()
        if not parts:
            self.caller.msg("Usage: evolve <pokemon_id> [item]")
            return

        pid = parts[0]
        item = parts[1] if len(parts) > 1 else None
        pokemon = self.caller.get_pokemon_by_id(pid)
        if not pokemon:
            self.caller.msg("No such Pokémon.")
            return

        if item and not self.caller.has_item(item):
            self.caller.msg(f"You do not have a {item}.")
            return

        from pokemon.data.evolution import attempt_evolution

        new_species = attempt_evolution(pokemon, item=item)
        if not new_species:
            self.caller.msg("It doesn't seem to be able to evolve right now.")
            return

        if item:
            self.caller.trainer.remove_item(item)
        pokemon.save()
        self.caller.msg(f"{pokemon.name} evolved into {new_species}!")

