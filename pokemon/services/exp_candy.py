"""Bounded EXP Candy progression, separate from Rare Candy's existing semantics."""

from copy import copy

from django.db import transaction

from pokemon.names import normalize_name
from pokemon.services.field_items import FieldMedicineError
from pokemon.services.field_progression import FieldProgressionUse


class CandyProgression:
    """Validate project growth semantics before any item or progression write."""

    amounts = {
        "expcandyxs": 100,
        "expcandys": 800,
        "expcandym": 3000,
        "expcandyl": 10000,
        "expcandyxl": 30000,
    }
    rates = {
        "fast": "fast",
        "mediumfast": "medium_fast",
        "mediumslow": "medium_slow",
        "parabolic": "medium_slow",
        "slow": "slow",
        "fluctuating": "fluctuating",
    }

    @classmethod
    def growth(cls, raw):
        """Use the existing missing-field default, but reject explicit unknown curves."""
        value = raw.get("growthRate", "medium_fast")
        if not isinstance(value, str) or normalize_name(value) not in cls.rates:
            raise FieldMedicineError("Unsupported saved growth curve; no EXP Candy was consumed.")
        return cls.rates[normalize_name(value)]

    @classmethod
    def plan(cls, pokemon, raw, item):
        """Return one useful bounded gain and final level, never silently fix old data."""
        from pokemon.models.stats import exp_for_level, level_for_exp

        rate = cls.growth(raw)
        level, total = pokemon.level, pokemon.total_exp
        if (
            type(level) is not int
            or type(total) is not int
            or not 1 <= level <= 100
            or total < 0
            or level_for_exp(total, rate) != level
        ):
            raise FieldMedicineError("Invalid saved level/EXP; no EXP Candy was consumed.")
        if level == 100:
            raise FieldMedicineError("That Pokemon is already level 100. No item was consumed.")
        gained = min(cls.amounts[normalize_name(item)], exp_for_level(100, rate) - total)
        if gained <= 0:
            raise FieldMedicineError("That EXP Candy would have no useful effect.")
        return gained, total + gained, level_for_exp(total + gained, rate)

    @staticmethod
    def crossed_moves(pokemon, species, old_level, new_level):
        """Order exact crossed-level knowledge by level and canonical move identity."""
        from pokemon.middleware import get_moveset_by_name

        if old_level == new_level:
            return []
        _, moveset = get_moveset_by_name(species)
        if not moveset:
            raise FieldMedicineError(
                "The species learning source is unavailable; nothing was consumed."
            )
        known = {
            normalize_name(name) for name in pokemon.learned_moves.values_list("name", flat=True)
        }
        candidates = []
        for level, name in moveset.get("level-up", []):
            if (
                type(level) is int
                and old_level < level <= new_level
                and normalize_name(name) not in known
            ):
                candidates.append((level, normalize_name(name), name))
        result = []
        for level, key, name in sorted(candidates):
            if key not in known:
                result.append((level, name))
                known.add(key)
        return result


class FieldExpCandyUse(FieldProgressionUse):
    """Atomically debit/advance/remember and persist later active-slot choices."""

    selected_move_items = set()

    @classmethod
    def supports(cls, item):
        """Enable only the five reviewed names, never a generic candy fallback."""
        return normalize_name(item) in CandyProgression.amounts

    def use(self, item, target, *, move=None):
        """Take character first so durable choice Attributes share ownership lock order."""
        from evennia.objects.models import ObjectDB
        from pokemon.services.battle_rewards import BattleRewards
        from pokemon.services.ownership import assert_character_free

        character = BattleRewards.character(self.caller)
        try:
            with transaction.atomic():
                ObjectDB.objects.select_for_update().filter(pk=character.pk).values("pk").get()
                assert_character_free(character)
                return super().use(item, target, move=move)
        except ObjectDB.DoesNotExist as error:
            raise FieldMedicineError("Your current character is unavailable.") from error

    def _apply(self, item, pokemon, trainer, *, move=None):
        """Keep paid EXP, crossed knowledge, HP and durable choice records together."""
        from pokemon.dex import POKEDEX
        from pokemon.names import resolve_dex_entry
        from pokemon.helpers.pokemon_helpers import get_max_hp, refresh_stats
        from pokemon.services.item_learning import ItemLearning
        from pokemon.services.move_management import get_or_create_move
        from pokemon.services.necrozma_moves import progression_species, remember_move

        pokemon = copy(pokemon)
        pokemon._state = copy(pokemon._state)
        source = progression_species(pokemon)
        species = resolve_dex_entry(POKEDEX, source)
        if species is None:
            raise FieldMedicineError("Invalid saved species; no EXP Candy was consumed.")
        gained, total, level = CandyProgression.plan(pokemon, species.raw, item)
        crossed = CandyProgression.crossed_moves(pokemon, source, pokemon.level, level)
        old_hp, maximum = pokemon.current_hp, get_max_hp(pokemon)
        if type(old_hp) is not int or not 0 <= old_hp <= maximum:
            raise FieldMedicineError("Invalid saved HP; no EXP Candy was consumed.")
        queue = ItemLearning(self.caller)
        queue.read()  # Invalid pending state must fail before a debit.
        if not trainer.remove_item(item):
            raise FieldMedicineError("EXP Candy could not be consumed. Nothing was changed.")
        pokemon.total_exp, pokemon.level = total, level
        pokemon.__dict__.pop("_cached_stats", None)
        new_max = refresh_stats(pokemon)["hp"]
        pokemon.current_hp = 0 if old_hp == 0 else max(1, min(new_max, old_hp + new_max - maximum))
        pokemon.save(update_fields=["total_exp", "level", "current_hp"])
        entries = []
        for earned_level, name in crossed:
            if not remember_move(pokemon, name, knowledge_only=True):
                pokemon.learned_moves.add(get_or_create_move(name, pokemon=pokemon))
            learned = next(
                move
                for move in pokemon.learned_moves.all()
                if normalize_name(move.name) == normalize_name(name)
            )
            entries.append((learned, earned_level))
        queue.add_locked(pokemon, entries)
        self.result_name, self.result_level, self.result_exp = pokemon.name, level, gained
        return True

    def success_message(self, item, target):
        """Report only the committed useful gain without re-resolving a changed target."""
        return f"{self.result_name} gained {self.result_exp} EXP and is level {self.result_level}."

    def notify_success(self, item, target):
        """Publish progression and resumable learning only after the containing commit."""
        from pokemon.services.item_learning import ItemLearning

        message = self.success_message(item, target)

        def publish():
            """A failed/disconnected UI cannot undo paid knowledge or EXP."""
            self.caller.msg(message)
            ItemLearning(self.caller).offer_if_available()

        transaction.on_commit(publish, robust=True)
