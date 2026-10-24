"""Transactional manual battle medicine, including reviewed recovery equivalents."""

from __future__ import annotations

from django.db import transaction

from pokemon.names import normalize_name
from pokemon.services.move_management import _get_move_pp_from_dex, _get_movedex
from pokemon.services.pokemon_refs import parse_pokemon_ref
from pokemon.services.recovery_effects import (
    BATTLE_BERRY_FRACTIONS, BATTLE_FOOD_HEALING, BATTLE_REVIVAL_FOODS,
    BATTLE_STATUS_FOODS, BERRY_HEALING, BERRY_PP, BERRY_STATUSES,
)


class ItemUnavailable(Exception):
    """An item debit failed; roll back any partial inventory changes."""


class BattleItemCapability:
    """One manual-use policy for input, saved choices and final battle dispatch."""

    @staticmethod
    def validate(item, *, battle=None):
        """Reject unsupported uses without inspecting target effect or spending."""
        from pokemon.items import is_capture_ball

        if normalize_name(item) == "smokeball":
            raise ValueError("Smoke Ball is a held item. Equip it with +hold before battle and use +flee.")
        if BattleMedicineUse.supports(item):
            return
        if is_capture_ball(item):
            if battle is not None and getattr(getattr(battle, "type", None), "name", "") != "WILD":
                raise ValueError("Poké Balls can only be used against wild Pokémon.")
            return
        raise ValueError("That item has no supported manual battle use. Use +use outside battle for field items "
                         "or +hold before battle for held items.")

    @classmethod
    def invalid_pending(cls, battle):
        """Find deferred item actions without changing any participant state."""
        for participant in battle.participants:
            pending = getattr(participant, "pending_action", None)
            for action in pending if isinstance(pending, list) else [pending] if pending else []:
                if getattr(action, "item", None) or getattr(getattr(action, "action_type", None), "name", "") == "ITEM":
                    try:
                        cls.validate(action.item, battle=battle)
                    except ValueError as error:
                        yield participant, action, str(error)


class BattlePPRestoration:
    """Restore the first depleted active move, using stored PP when owned."""

    def __init__(self, pokemon, trainer=None, *, amount=10, move=None, all_moves=False):
        """Bind the battle snapshot, item owner and restoration amount."""
        self.pokemon = pokemon
        self.trainer = trainer
        self.amount = amount
        self.move = move
        self.all_moves = all_moves

    @staticmethod
    def _maximum(move_name, bonus=0):
        """Resolve display and compact move names to their boosted PP cap."""
        _, base = _get_move_pp_from_dex(_get_movedex(), move_name)
        return int(base) + int(bonus) if base is not None else None

    def _update_snapshot(self, move_name, pp):
        """Keep serialised battle moves consistent with the committed slot."""
        for move in self.pokemon.moves:
            if normalize_name(move.name) == normalize_name(move_name):
                move.pp = pp

    def restore(self, consume_item) -> bool:
        """Commit one item debit and one capped PP write, or apply no effect."""
        kind, identifier = parse_pokemon_ref(getattr(self.pokemon, "model_id", None))
        try:
            if kind == "owned" and identifier:
                return self._restore_owned(identifier, consume_item)
            return self._restore_temporary(consume_item)
        except ItemUnavailable:
            return False

    def _restore_owned(self, identifier, consume_item):
        """Lock fresh owned slots so reconnects and competing uses agree."""
        from pokemon.models.core import OwnedPokemon
        from pokemon.models.moves import ActiveMoveslot, MovePPBoost

        with transaction.atomic():
            owned = OwnedPokemon.objects.select_for_update().get(pk=identifier)
            owned.refresh_from_db()
            if owned.trainer_id != getattr(self.trainer, "pk", None):
                raise ValueError("PP restoration requires the owning trainer.")
            from pokemon.services.necrozma_guards import assert_operation

            assert_operation(identifier, "pp")
            slots = list(
                ActiveMoveslot.objects.select_for_update(of=("self",))
                .filter(
                    pokemon_id=identifier,
                )
                .select_related("move")
                .order_by("slot")
            )
            bonuses = dict(
                MovePPBoost.objects.filter(pokemon_id=identifier).values_list("move_id", "bonus_pp")
            )
            changes = []
            for move in self.pokemon.moves:
                slot = next(
                    (s for s in slots if normalize_name(s.move.name) == normalize_name(move.name)),
                    None,
                )
                if slot is None:
                    continue
                if (
                    self.move is not None
                    and str(self.move) != str(slot.slot)
                    and normalize_name(self.move) != normalize_name(move.name)
                ):
                    continue
                maximum = self._maximum(slot.move.name, bonuses.get(slot.move_id, 0))
                if maximum is None:
                    continue
                current = slot.current_pp if slot.current_pp is not None else maximum
                if current >= maximum:
                    continue
                updated = (
                    maximum if self.amount is None else min(maximum, max(0, current) + self.amount)
                )
                changes.append((slot, updated))
                if not self.all_moves:
                    break
            if changes:
                if not consume_item():
                    raise ItemUnavailable
            for slot, updated in changes:
                slot.current_pp = updated
                slot.save(update_fields=["current_pp"])
        # BattleSession wraps the entire turn in another transaction. Apply
        # runtime values after our savepoint succeeds, before later actions and
        # the turn checkpoint; an outer on_commit callback would be too late.
        for slot, updated in changes:
            self._update_snapshot(slot.move.name, updated)
        return bool(changes)

    def _restore_temporary(self, consume_item):
        """Support transient battle simulations without requiring model rows."""
        changes = []
        for index, move in enumerate(self.pokemon.moves, 1):
            if (
                self.move is not None
                and str(self.move) != str(index)
                and normalize_name(self.move) != normalize_name(move.name)
            ):
                continue
            maximum = getattr(move, "max_pp", None)
            if maximum is None:
                maximum = self._maximum(move.name)
            current = getattr(move, "pp", maximum)
            if maximum is None or current is None or current >= maximum:
                continue
            updated = (
                maximum if self.amount is None else min(maximum, max(0, current) + self.amount)
            )
            changes.append((move, updated))
            if not self.all_moves:
                break
        if not changes:
            return False
        if not consume_item():
            raise ItemUnavailable
        for move, updated in changes:
            move.pp = updated
        return True


class BattleMedicineUse:
    """Validate the selected owned battle target and commit one medicine use."""

    healing = {
        "potion": 20,
        "superpotion": 60,
        "hyperpotion": 120,
        "maxpotion": None,
        "fullrestore": None,
        "energypowder": 60,
        "energyroot": 120,
    }
    statuses = {
        "antidote": {"psn", "tox"},
        "burnheal": {"brn"},
        "iceheal": {"frz"},
        "awakening": {"slp"},
        "paralyzeheal": {"par"},
        "fullheal": {"brn", "psn", "tox", "frz", "slp", "par"},
        "healpowder": {"brn", "psn", "tox", "frz", "slp", "par"},
        "fullrestore": {"brn", "psn", "tox", "frz", "slp", "par"},
    }
    revivals = {"revive", "maxrevive", "revivalherb"}
    pp_items = {
        "ether": (10, False),
        "maxether": (None, False),
        "elixir": (10, True),
        "maxelixir": (None, True),
    }
    # Preserve the original generic +use dispatch. Berry/food field services
    # still own their wider feeding rules and move-selector validation.
    standard_items = frozenset(healing) | frozenset(statuses) | revivals | frozenset(pp_items)
    healing = {**healing, **BERRY_HEALING, **BATTLE_FOOD_HEALING}
    fractions = BATTLE_BERRY_FRACTIONS
    statuses = {**statuses, **BERRY_STATUSES,
                **dict.fromkeys(BATTLE_STATUS_FOODS, statuses["fullheal"])}
    revivals = revivals | BATTLE_REVIVAL_FOODS
    pp_items = {**pp_items, **BERRY_PP}
    herbs = {
        "energypowder": (5, 10),
        "healpowder": (5, 10),
        "energyroot": (10, 15),
        "revivalherb": (15, 20),
    }

    def __init__(self, pokemon, trainer=None, *, battle=None, move=None):
        """Resolve fractional HP against this target without changing class tables."""
        self.pokemon, self.trainer = pokemon, trainer
        self.battle, self.move = battle, move
        self.healing = {
            **type(self).healing,
            **{key: max(1, pokemon.max_hp // divisor)
               for key, divisor in self.fractions.items()},
        }

    @classmethod
    def supports(cls, item):
        """Recognize standard medicine and the named recovery-equivalent subset."""
        key = normalize_name(item)
        return (
            key in cls.healing or key in cls.fractions or key in cls.statuses
            or key in cls.revivals or key in cls.pp_items
        )

    def _owned(self, identifier):
        """Lock storage before fresh owner, placement and egg validation."""
        from pokemon.models.core import OwnedPokemon
        from pokemon.models.storage import PokemonPlacement, UserStorage

        storage = UserStorage.objects.select_for_update().get(user_id=self.trainer.user_id)
        row = OwnedPokemon.objects.select_for_update().filter(pk=identifier).values().get()
        owned = OwnedPokemon.objects.get(pk=identifier)
        # Evennia's identity map may return the pre-queue model instance.
        # Apply the independently fetched locked row, including current owner,
        # egg state and friendship, before checking eligibility or saving.
        for name, value in row.items():
            setattr(owned, name, value)
        owned._state.fields_cache.clear()
        placement = (
            PokemonPlacement.objects.select_for_update()
            .filter(pokemon=owned, storage=storage)
            .values("location_type")
            .first()
        )
        if owned.trainer_id != self.trainer.pk or owned.is_egg or placement is None:
            raise ValueError("Medicine requires an eligible owned party member.")
        from pokemon.services.necrozma_guards import assert_operation

        assert_operation(identifier, "field")
        if placement["location_type"] not in {"party", "fusion"}:
            raise ValueError("Medicine cannot target a boxed or reserved Pokemon.")
        if placement["location_type"] == "fusion":
            character = self.trainer.user
            if str(getattr(character.db, "fusion_id", "")) != str(owned.pk):
                raise ValueError("That Fusion reservation is not this character's battler.")
        return owned

    def use(self, item, consume_item):
        """Keep inventory, durable effects and the battle snapshot consistent."""
        self._snapshot_update = None
        kind, identifier = parse_pokemon_ref(getattr(self.pokemon, "model_id", None))
        if kind == "owned" and identifier:
            try:
                with transaction.atomic():
                    owned = self._owned(identifier)
                    used = self._apply(normalize_name(item), consume_item, owned)
            except ItemUnavailable:
                return False
            if used and self._snapshot_update is not None:
                self._snapshot_update()
            return used
        try:
            return self._apply(normalize_name(item), consume_item)
        except ItemUnavailable:
            return False

    def _apply(self, key, consume_item, owned=None):
        pokemon = self.pokemon
        if key in self.pp_items:
            if pokemon.hp <= 0:
                return False
            amount, all_moves = self.pp_items[key]
            if all_moves and self.move is not None:
                raise ValueError("Elixirs restore all active move slots; omit the move selector.")
            return BattlePPRestoration(
                pokemon, self.trainer, amount=amount, move=self.move, all_moves=all_moves
            ).restore(consume_item)
        old_hp, old_status = pokemon.hp, pokemon.status
        hp, status = old_hp, old_status
        if key in self.healing and 0 < hp < pokemon.max_hp:
            amount = self.healing[key]
            hp = pokemon.max_hp if amount is None else min(pokemon.max_hp, hp + amount)
        if hp > 0 and status in self.statuses.get(key, set()):
            status = ""
        if key in self.revivals and hp <= 0:
            hp = max(1, pokemon.max_hp // 2) if key == "revive" else pokemon.max_hp
        if (hp, status) == (old_hp, old_status):
            return False
        if not consume_item():
            raise ItemUnavailable
        friendship = getattr(owned or pokemon, "friendship", 70)
        if key in self.herbs:
            low, high = self.herbs[key]
            friendship = max(0, friendship - (low if friendship < 200 else high))
        if owned is not None:
            owned.current_hp, owned.status = hp, status or ""
            owned.friendship = friendship
            if not status:
                owned.sleep_turns = None
            owned.save(update_fields=["current_hp", "status", "sleep_turns", "friendship"])

        def update_snapshot():
            pokemon.hp = hp
            pokemon.friendship = friendship
            if status != old_status:
                pokemon.setStatus(status or 0, battle=self.battle, effect="item:" + key)
            pokemon.is_fainted = hp <= 0

        if owned is None:
            update_snapshot()
        else:
            self._snapshot_update = update_snapshot
        return True
