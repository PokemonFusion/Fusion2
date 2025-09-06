"""Admin command to repair missing fusion records."""

from evennia import Command
from django.core.exceptions import ValidationError
from utils.fusion import record_fusion
from pokemon.models.core import OwnedPokemon
from pokemon.models.storage import ActivePokemonSlot


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

        # Locate the fused Pokémon: check party, then boxes, then all owned
        party = storage.get_party() if hasattr(storage, "get_party") else list(
            getattr(storage, "active_pokemon", []))
        fused = next(
            (
                mon
                for mon in party
                if getattr(getattr(mon, "species", None), "name", getattr(mon, "species", None))
                == species
            ),
            None,
        )
        if not fused:
            boxes = getattr(storage, "stored_pokemon", None)
            if hasattr(boxes, "filter"):
                fused = boxes.filter(species__iexact=species).first()
        if not fused and trainer:
            fused = OwnedPokemon.objects.filter(trainer=trainer, species__iexact=species).first()
        if not fused:
            self.caller.msg("No matching fused Pokémon owned by target.")
            return

        # Ensure the fused Pokémon is in the active party
        if not getattr(fused, "in_party", False):
            try:
                storage.add_active_pokemon(fused)
            except (ValidationError, ValueError) as err:
                self.caller.msg(f"Couldn't add to party: {err}")
                return
            slot_rel = ActivePokemonSlot.objects.filter(storage=storage, pokemon=fused).first()
            slot_no = getattr(slot_rel, "slot", None)
            self.caller.msg(
                f"Added {getattr(fused, 'name', fused)} to party in slot {slot_no or '?'}"
            )
        else:
            self.caller.msg(
                f"{getattr(fused, 'name', fused)} already in party (slot {getattr(fused, 'party_slot', '?')})."
            )

        try:
            record_fusion(fused, trainer, fused, permanent=True)
        except Exception as err:  # pragma: no cover - defensive
            self.caller.msg(f"Error: {err}")
            return

        fid = getattr(fused, "unique_id", None)
        target.db.fusion_id = fid
        if not getattr(target.db, "fusion_species", None):
            target.db.fusion_species = getattr(
                getattr(fused, "species", None), "name", None
            )
        self.caller.msg(
            f"Recorded fusion for {target.key}; stored fusion ID {fid}."
        )
