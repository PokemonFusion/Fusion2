"""Admin command to repair missing fusion records."""

from evennia import Command

from utils.fusion import record_fusion


class CmdFixFusion(Command):
    """Record a trainer's fusion if it was not stored correctly.

    Usage:
      @fixfusion <character>

    This searches the target's active party for a Pokémon matching their
    recorded fusion species and records a permanent fusion between the
    trainer and that Pokémon. Intended for repairing improperly stored
    fusions.
    """

    key = "@fixfusion"
    locks = "cmd:perm(Wizards)"
    help_category = "Admin"

    def func(self):
        """Execute the command."""
        if not self.args:
            self.caller.msg("Usage: @fixfusion <character>")
            return
        target = self.caller.search(self.args.strip(), global_search=True)
        if not target:
            return
        species = getattr(getattr(target, "db", None), "fusion_species", None)
        trainer = getattr(target, "trainer", None)
        storage = getattr(target, "storage", None)
        if not (species and trainer and storage):
            self.caller.msg("Target has no fusion data.")
            return
        party = storage.get_party() if hasattr(storage, "get_party") else list(
            getattr(storage, "active_pokemon", []))
        fused = None
        for mon in party:
            mon_species = getattr(mon, "species", None)
            name = getattr(mon_species, "name", mon_species)
            if name == species:
                fused = mon
                break
        if not fused:
            self.caller.msg("No matching fused Pokémon found in party.")
            return
        try:
            record_fusion(fused, trainer, fused, permanent=True)
        except Exception as err:  # pragma: no cover - defensive
            self.caller.msg(f"Error: {err}")
            return
        self.caller.msg(f"Recorded fusion for {target.key}.")
