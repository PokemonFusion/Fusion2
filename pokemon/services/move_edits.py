"""Fresh owner/reservation guards for existing synchronous and menu move writes."""

from contextlib import contextmanager, nullcontext
from functools import wraps

from pokemon.services.battle_rewards import BattleRewards


class MoveEdits:
    """Retain storage-first order so level-up/item transactions can safely nest."""

    def __init__(self, caller):
        """Keep the current character authoritative over retained menu references."""
        self.caller = caller
        from pokemon.services.ownership import acting_character

        self.character = acting_character(caller)

    @contextmanager
    def locked(self, pokemon, *, require_center=False, expected_slot=None):
        """Lock fresh storage and source; never trust a menu's retained trainer cache."""
        from pokemon.models.storage import UserStorage
        from pokemon.models.core import OwnedPokemon
        from evennia.objects.models import ObjectDB
        from django.db import transaction
        from pokemon.services.ownership import assert_character_free
        from pokemon.services.placement import PlacementError, PlacementService

        storage = UserStorage.objects.filter(user_id=self.character.pk).first()
        if storage is None:
            raise PlacementError("Your character has no Pokemon storage.")
        # Item/level-up learning already runs storage-first. Center-only menu
        # requests start at the character row so movement cannot race the check.
        identifier = pokemon.pk
        try:
            with transaction.atomic() if require_center else nullcontext():
                if require_center:
                    owner = ObjectDB.objects.select_for_update(no_key=True).filter(pk=self.character.pk).values("db_location_id").get()
                    room = ObjectDB.objects.filter(pk=owner["db_location_id"]).first()
                    if room is None or BattleRewards.stored_attribute(room, "is_pokemon_center") is not True:
                        raise PlacementError("Use saved movesets at a Pokemon Center.")
                with PlacementService(storage).locked() as storage:
                    assert_character_free(self.character)
                    try:
                        source, placement = PlacementService(storage)._pokemon(pokemon, storage)
                    except OwnedPokemon.DoesNotExist as error:
                        raise PlacementError("That Pokemon no longer exists.") from error
                    if expected_slot is not None and (placement is None or placement.location_type != "party" or placement.slot != expected_slot):
                        raise PlacementError("That Pokemon is no longer in the selected party slot.")
                    if source.is_egg:
                        raise PlacementError("Eggs cannot learn or change moves.")
                    yield source
        finally:
            from django.db import connection

            cached = OwnedPokemon.get_cached_instance(identifier)
            if cached is not None:
                OwnedPokemon.flush_cached_instance(cached)
            if connection.in_atomic_block:
                transaction.on_commit(lambda: self._refresh(identifier))
            else:
                self._refresh(identifier)

    @staticmethod
    def _refresh(identifier):
        """Publish current fields after success/failure without reviving a released row."""
        from pokemon.models.core import OwnedPokemon
        from pokemon.services.ownership import fresh_owned

        try:
            fresh_owned(identifier)
        except OwnedPokemon.DoesNotExist:
            pass

    def activate_set(self, pokemon, index, *, expected_slot=None):
        """Select a saved set at a Center, where existing PP restoration is allowed."""
        from pokemon.services.move_management import apply_active_moveset
        from pokemon.services.placement import PlacementError

        with self.locked(pokemon, require_center=True, expected_slot=expected_slot) as source:
            if type(index) is not int or index not in range(4):
                raise PlacementError("Choose a saved moveset from 1 to 4.")
            moveset = source.movesets.filter(index=index).first()
            if moveset is None:
                raise PlacementError("That saved moveset does not exist.")
            source.active_moveset = moveset
            source.save(update_fields=["active_moveset"])
            apply_active_moveset(source)
            return source.name


def after_move_commit(caller, callback):
    """Publish notices/prompts only after a real player's move writes commit."""
    if caller is not None and BattleRewards.supports(caller):
        from django.db import transaction

        transaction.on_commit(callback, robust=True)
    else:
        callback()


def guarded_learning(function):
    """Revalidate every caller-bound learn request, including a stale menu reply."""
    @wraps(function)
    def guarded(pokemon, *args, caller=None, **kwargs):
        if caller is None or not BattleRewards.supports(caller):
            return function(pokemon, *args, caller=caller, **kwargs)
        from pokemon.services.placement import PlacementError

        try:
            with MoveEdits(caller).locked(pokemon) as source:
                return function(source, *args, caller=caller, **kwargs)
        except PlacementError as error:
            caller.msg(str(error) + " No moves were changed.")
            return None
    return guarded


def guarded_move_menu(function=None, *, require_center=False):
    """Guard read/write menu callbacks before inspecting any retained Pokemon."""
    if function is None:
        return lambda target: guarded_move_menu(target, require_center=require_center)
    @wraps(function)
    def guarded(caller, raw_input=None, **kwargs):
        # EvMenu inspects getfullargspec rather than the wrapped signature.
        # Keep input explicit so it forwards the player's actual reply.
        if not BattleRewards.supports(caller):
            return function(caller, raw_input, **kwargs)
        from pokemon.services.placement import PlacementError

        pokemon = kwargs.get("pokemon") or getattr(caller.ndb, "ms_pokemon", None)
        if pokemon is None:
            return function(caller, raw_input, **kwargs)
        try:
            with MoveEdits(caller).locked(pokemon, require_center=require_center) as source:
                if "pokemon" in kwargs:
                    kwargs["pokemon"] = source
                else:
                    caller.ndb.ms_pokemon = source
                return function(caller, raw_input, **kwargs)
        except PlacementError as error:
            return str(error) + " No moves were changed. Reopen the menu for an eligible owned Pokemon.", None
    return guarded
