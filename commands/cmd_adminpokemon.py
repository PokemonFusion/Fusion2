from evennia import Command
from pokemon.models import OwnedPokemon


class CmdListPokemon(Command):
    """List a character's Pokémon.

    Usage:
      @listpokemon <character>
    """

    key = "@listpokemon"
    locks = "cmd:perm(Wizards)"
    help_category = "Admin"

    def func(self):
        if not self.args:
            self.caller.msg("Usage: @listpokemon <character>")
            return
        target = self.caller.search(self.args.strip(), global_search=True)
        if not target:
            return
        storage = getattr(target, "storage", None)
        if not storage:
            self.caller.msg("Target has no Pokémon storage.")
            return
        party = storage.get_party() if hasattr(storage, "get_party") else list(storage.active_pokemon.all())
        stored = list(storage.stored_pokemon.all())
        lines = [f"Pokémon for {target.key}:"]
        if party:
            lines.append(" Active party:")
            for idx, mon in enumerate(party, start=1):
                lines.append(f"  {idx}. {mon.name} Lv{mon.level} ID:{mon.unique_id}")
        else:
            lines.append(" No active Pokémon.")
        if stored:
            lines.append(" Stored Pokémon:")
            for mon in stored:
                lines.append(f"  {mon.name} Lv{mon.level} ID:{mon.unique_id}")
        else:
            lines.append(" No stored Pokémon.")
        self.caller.msg("\n".join(lines))


class CmdRemovePokemon(Command):
    """Delete a Pokémon by its ID.

    Usage:
      @removepokemon <pokemon_id>
    """

    key = "@removepokemon"
    locks = "cmd:perm(Wizards)"
    help_category = "Admin"

    def func(self):
        pid = self.args.strip()
        if not pid:
            self.caller.msg("Usage: @removepokemon <pokemon_id>")
            return
        pokemon = OwnedPokemon.objects.filter(unique_id=pid).first()
        if not pokemon:
            self.caller.msg("No Pokémon found with that ID.")
            return
        name = pokemon.name
        # Clear many-to-many relations to avoid orphaned slots
        pokemon.active_users.clear()
        pokemon.stored_users.clear()
        pokemon.boxes.clear()
        pokemon.delete()
        self.caller.msg(f"Removed {name} ({pid}).")
