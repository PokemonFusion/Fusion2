"""Atomic field progression items using the shared owned-target boundary."""

from copy import copy
from django.db import connection, transaction

from pokemon.names import normalize_name
from pokemon.services.field_items import FieldMedicineError, FieldMedicineUse


class FieldRareCandyUse(FieldMedicineUse):
    """Consume one Rare Candy and persist one level gain under shared locks."""

    selected_move_items = set()

    @classmethod
    def supports(cls, item):
        """Keep PP-capacity and other progression items outside this repair."""
        return normalize_name(item) == "rarecandy"

    def _apply(self, item, pokemon, trainer, *, move=None):
        """Commit inventory, EXP, level and level-up moves together or neither."""
        from pokemon.dex import POKEDEX
        from pokemon.models.stats import exp_for_level, level_for_exp
        from pokemon.names import resolve_dex_entry
        from pokemon.utils.move_learning import get_learnable_levelup_moves, learn_move

        # Do not mutate a shared Evennia identity-map instance while another
        # command is waiting for our storage/row locks.
        pokemon = copy(pokemon)
        pokemon._state = copy(pokemon._state)
        species = resolve_dex_entry(POKEDEX, pokemon.species)
        if species is None:
            raise FieldMedicineError("Invalid saved species; contact staff before using Rare Candy.")
        growth = species.raw.get("growthRate", "medium_fast")
        level = level_for_exp(pokemon.total_exp, growth)
        if pokemon.total_exp < 0 or pokemon.level != level:
            raise FieldMedicineError("Invalid saved level/EXP; contact staff before using Rare Candy.")
        if level >= 100:
            raise FieldMedicineError(f"{pokemon.name} is already level 100. No item was consumed.")
        if not trainer.remove_item(item):
            # Raising also rolls back a debit that failed after a partial write.
            raise FieldMedicineError("Rare Candy could not be consumed. Nothing was changed.")
        pokemon.total_exp = exp_for_level(level + 1, growth)
        pokemon.level = level + 1
        pokemon.__dict__.pop("_cached_stats", None)
        pokemon.save(update_fields=["total_exp", "level"])
        moves, _ = get_learnable_levelup_moves(pokemon)
        for name in moves:
            # Use the normal learner without its best-effort EXP wrapper: an
            # unexpected failure must propagate and roll back this whole use.
            learn_move(pokemon, name)
        self.result_name, self.result_level = pokemon.name, pokemon.level
        if moves:
            # UI is not transactional. Only publish learning/prompts after the
            # outermost transaction commits, never after a rolled-back level.
            identifier, learned = pokemon.pk, tuple(moves)

            def show_moves():
                """Publish only committed learning, with a named robust callback."""
                self._show_moves(identifier, learned)

            transaction.on_commit(show_moves, robust=True)
        return True

    def success_message(self, item, target):
        """Describe the committed level without resolving the target again."""
        return f"{self.result_name} grew to level {self.result_level}."

    def notify_success(self, item, target):
        """Do not announce a level if a containing operation rolls back."""
        message = self.success_message(item, target)

        def notify():
            """A disconnected transport cannot undo the committed effect."""
            self.caller.msg(message)

        transaction.on_commit(notify, robust=True)

    def _resync(self, pokemon):
        """Do not publish uncommitted fields to shared caches in a parent use."""
        if connection.in_atomic_block:
            from pokemon.models.core import OwnedPokemon

            OwnedPokemon.flush_cached_instance(pokemon)

            def resync():
                """Refresh held references only after the parent commits."""
                super(FieldRareCandyUse, self)._resync(pokemon)

            transaction.on_commit(resync, robust=True)
        else:
            super()._resync(pokemon)

    def _show_moves(self, identifier, names):
        """Retain ordinary learned-move notices and full-moveset prompts."""
        from pokemon.models.core import OwnedPokemon
        from pokemon.models.storage import PokemonPlacement

        row = OwnedPokemon.objects.filter(pk=identifier, trainer__user_id=self.caller.pk).values().first()
        placement = PokemonPlacement.objects.filter(pokemon_id=identifier).values().first()
        if row is None or placement is None:
            return
        if placement["location_type"] != "party" and not (
            placement["location_type"] == "fusion"
            and str(identifier) == str(getattr(self.caller.db, "fusion_id", ""))
        ):
            return
        pokemon = OwnedPokemon.objects.get(pk=identifier)
        self._refresh(pokemon, row)
        active = {normalize_name(name) for name in pokemon.activemoveslot_set.values_list("move__name", flat=True)}
        for name in names:
            if normalize_name(name) in active:
                self.caller.msg(f"{pokemon.name} learned {name.capitalize()}!")
            else:
                from menus import learn_move as learn_menu
                from utils.enhanced_evmenu import EnhancedEvMenu

                EnhancedEvMenu(self.caller, learn_menu, startnode="node_start",
                               start_kwargs={"pokemon": pokemon, "move_name": name})
