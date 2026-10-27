"""Atomic, owner-validated Bottle Cap and Gold Bottle Cap field training."""

from copy import copy

from django.core.exceptions import ValidationError

from pokemon.hyper_training import HyperTraining
from pokemon.names import normalize_name
from pokemon.services.field_items import FieldMedicineError
from pokemon.services.field_progression import FieldProgressionUse


class FieldHyperTrainingUse(FieldProgressionUse):
    """Train effective IVs under shared field eligibility, row and bag locks."""

    selected_move_items = {"bottlecap"}
    selection_label = "stat name"

    @classmethod
    def supports(cls, item):
        """Allow the two existing caps without introducing new training items."""
        return normalize_name(item) in {"bottlecap", "goldbottlecap"}

    @classmethod
    def usage_target(cls, item):
        """Explain the required single-stat selector without a move prompt."""
        return ("<party slot, Pokemon name or fusion>/[HP|Atk|Def|SpA|SpD|Spe]"
                if normalize_name(item) == "bottlecap" else "<party slot, Pokemon name or fusion>")

    def _apply(self, item, pokemon, trainer, *, move=None):
        """Commit useful training flags, adjusted HP and one debit together."""
        from pokemon.data.evolution import lookup_species
        from pokemon.helpers.pokemon_helpers import get_max_hp, refresh_stats
        from pokemon.models.stats import level_for_exp
        from pokemon.models.validators import validate_evs, validate_ivs

        pokemon = copy(pokemon)
        pokemon._state = copy(pokemon._state)
        species = lookup_species(pokemon.species)
        if (species is None or getattr(pokemon, "transformed", False)
                or any(species.raw.get(key) for key in (
                    "battleOnly", "requiredAbility", "requiredItem", "requiredItems"
                ))):
            raise FieldMedicineError("Choose an eligible native field species/form for Hyper Training.")
        growth = species.raw.get("growthRate", "medium_fast")
        level = level_for_exp(pokemon.total_exp, growth)
        if pokemon.total_exp < 0 or pokemon.level != level:
            raise FieldMedicineError("Invalid saved level/EXP; contact staff before Hyper Training.")
        if level < HyperTraining.minimum_level:
            raise FieldMedicineError("Hyper Training requires level 50 or higher. No item was consumed.")
        try:
            validate_ivs(pokemon.ivs)
            validate_evs(pokemon.evs)
        except ValidationError as error:
            raise FieldMedicineError("Invalid saved IVs/EVs; contact staff before Hyper Training.") from error
        flags = list(pokemon.flags)
        if any(flag.startswith(HyperTraining.prefix) and
               flag.removeprefix(HyperTraining.prefix) not in HyperTraining.stats for flag in flags):
            raise FieldMedicineError("Invalid saved Hyper Training flags; contact staff before training.")
        if normalize_name(item) == "bottlecap":
            stat = HyperTraining.stat(move)
            if stat is None:
                raise FieldMedicineError("Choose a stat: +use Bottle Cap=3/HP (or Atk, Def, SpA, SpD, Spe).")
            selected = [stat]
        else:
            selected = list(HyperTraining.stats)
        trained = HyperTraining.trained(pokemon)
        eligible = [stat for stat in selected if stat not in trained
                    and pokemon.ivs[HyperTraining.stats.index(stat)] < 31]
        if not eligible:
            return False
        old_max, old_hp = get_max_hp(pokemon), pokemon.current_hp
        if not trainer.remove_item(item):
            raise FieldMedicineError("The Bottle Cap could not be consumed. Nothing was changed.")
        pokemon.flags = flags + [HyperTraining.prefix + stat for stat in eligible]
        pokemon.__dict__.pop("_cached_stats", None)
        new_max = refresh_stats(pokemon)["hp"]
        pokemon.current_hp = (0 if old_hp <= 0 else
                              max(1, min(new_max, old_hp + new_max - old_max)))
        pokemon.save(update_fields=["flags", "current_hp"])
        self.trained_labels = [HyperTraining.labels[HyperTraining.stats.index(stat)] for stat in eligible]
        return True

    def success_message(self, item, target):
        """Describe the committed overlay while distinguishing genetic values."""
        return (f"Used {item} on {target}. Hyper Trained: {', '.join(self.trained_labels)}. "
                "These stats use effective IV 31; genetic IVs are unchanged.")
