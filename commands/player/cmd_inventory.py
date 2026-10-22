"""Inventory-related command set for Pokémon game.

This module houses commands dealing with a player's inventory, such as
viewing items, adding new ones, giving them to others and using them.
"""

from dataclasses import dataclass

from evennia import Command

from utils.dex_suggestions import item_not_found_message
from utils.locks import require_no_battle_lock


def _inventory_item_key(item_name: str) -> tuple[str | None, object | None, str]:
    """Return canonical dex key, data object, and stored inventory key."""

    from pokemon.middleware import get_item_by_name

    canonical, data = get_item_by_name(item_name)
    if canonical:
        return canonical, data, canonical.lower()
    fallback = (item_name or "").replace(" ", "").replace("-", "").replace("'", "").lower()
    return None, None, fallback


def _display_item_name(data, fallback: str) -> str:
    raw = getattr(data, "raw", None)
    display = raw.get("name") if isinstance(raw, dict) else None
    display = display or (data.get("name") if isinstance(data, dict) else None)
    display = display or getattr(data, "name", None)
    return display or str(fallback).title()


@dataclass
class _ParsedItemUse:
    item_query: str
    canonical: str | None
    item_data: object | None
    item_key: str
    target_query: str | None = None
    ambiguous_item_sides: bool = False


@dataclass
class _ResolvedUseTarget:
    query: str
    slot: int | None = None
    pokemon: object | None = None
    is_self: bool = False


def _parse_item_use_args(args: str) -> _ParsedItemUse:
    """Parse +use args into canonical item-first structure."""

    if "=" not in args:
        canonical, item_data, item_key = _inventory_item_key(args)
        return _ParsedItemUse(args, canonical, item_data, item_key)

    left, right = [part.strip() for part in args.split("=", 1)]
    left_canonical, left_data, left_key = _inventory_item_key(left)
    right_canonical, right_data, right_key = _inventory_item_key(right)

    if left_canonical and right_canonical:
        return _ParsedItemUse(
            left,
            left_canonical,
            left_data,
            left_key,
            target_query=right,
            ambiguous_item_sides=True,
        )

    if left_canonical or not right_canonical:
        return _ParsedItemUse(left, left_canonical, left_data, left_key, target_query=right)

    return _ParsedItemUse(
        right,
        right_canonical,
        right_data,
        right_key,
        target_query=left,
    )


def _pokemon_text(value) -> str:
    if value is None:
        return ""
    nested = getattr(value, "name", None)
    return str(nested if nested is not None else value).strip()


def _normalize_target_text(value) -> str:
    from pokemon.names import normalize_name

    return normalize_name(_pokemon_text(value))


def _iter_active_party(caller):
    getter = getattr(caller, "get_active_party", None)
    if callable(getter):
        try:
            return list(getter())
        except Exception:
            pass

    storage = getattr(caller, "storage", None)
    party_getter = getattr(storage, "get_party", None)
    if callable(party_getter):
        try:
            return list(party_getter())
        except Exception:
            pass

    slot_getter = getattr(caller, "get_active_pokemon_by_slot", None)
    if callable(slot_getter):
        party = []
        for slot in range(1, 7):
            pokemon = slot_getter(slot)
            if pokemon:
                party.append(pokemon)
        return party

    return []


def _resolve_use_target(caller, query: str) -> tuple[_ResolvedUseTarget | None, str]:
    raw = (query or "").strip()
    if not raw:
        return None, "Usage: +use <item>=<target>"

    lowered = raw.lower()
    if lowered in {"self", "me"}:
        return _ResolvedUseTarget(raw, is_self=True), ""

    if raw.isdigit():
        slot = int(raw)
        getter = getattr(caller, "get_active_pokemon_by_slot", None)
        pokemon = getter(slot) if callable(getter) else None
        if not pokemon:
            return None, f"No Pokemon in party slot {slot}."
        return _ResolvedUseTarget(raw, slot=slot, pokemon=pokemon), ""

    needle = _normalize_target_text(raw)
    for slot, pokemon in enumerate(_iter_active_party(caller), 1):
        candidates = (
            getattr(pokemon, "name", None),
            getattr(pokemon, "nickname", None),
            getattr(pokemon, "species", None),
            getattr(pokemon, "unique_id", None),
            getattr(pokemon, "id", None),
        )
        normalized = [_normalize_target_text(candidate) for candidate in candidates]
        if needle in normalized:
            return _ResolvedUseTarget(raw, slot=slot, pokemon=pokemon), ""

    return None, f"No Pokemon target found for '{raw}'."


def _trainer_has_item(trainer, item_key: str, amount: int = 1) -> bool:
    checker = getattr(trainer, "has_item", None)
    if callable(checker):
        return bool(checker(item_key, amount))
    quantity = getattr(trainer, "get_item_quantity", None)
    if callable(quantity):
        return int(quantity(item_key) or 0) >= amount
    return True


class CmdInventory(Command):
    """Show items in your inventory.

    Usage:
      +inventory

    Examples:
      +inventory

    Notes:
      Use +use for field-use items and +battle/item for battle items.
    """

    key = "+inventory"
    aliases = ["inventory"]
    locks = "cmd:all()"
    help_category = "Inventory"

    def func(self):
        trainer = getattr(self.caller, "trainer", None)
        if not trainer:
            self.caller.msg("You have no trainer record.")
            return

        entries = trainer.list_inventory()
        if not entries:
            self.caller.msg("Your inventory is empty.")
            return

        lines = ["Your Inventory:"]
        from pokemon.middleware import get_item_by_name, get_item_description

        for entry in entries:
            item_name, data = get_item_by_name(entry.item_name)
            item_name = item_name or entry.item_name
            desc = get_item_description(item_name, data)
            display = _display_item_name(data, item_name)
            lines.append(f"{display} x{entry.quantity} - {desc}")
        self.caller.msg("\n".join(lines))


class CmdAddItem(Command):
    """Add an item to your inventory.

    Usage:
      @additem <item> <amount>
    """

    key = "@additem"
    aliases = ["additem"]
    locks = "cmd:perm(Builder)"
    help_category = "Admin"

    def func(self):
        if not require_no_battle_lock(self.caller):
            return
        parts = self.args.split()
        if len(parts) != 2:
            self.caller.msg("Usage: @additem <item> <amount>")
            return
        item = parts[0]
        try:
            qty = int(parts[1])
        except ValueError:
            self.caller.msg("Usage: @additem <item> <amount>")
            return
        trainer = getattr(self.caller, "trainer", None)
        if not trainer:
            self.caller.msg("You have no trainer record.")
            return
        trainer.add_item(item, qty)
        self.caller.msg(f"Added {qty} x {item}.")


class CmdGiveItem(Command):
    """Give an item to another player (admin-only).

    Usage:
      @giveitem <player> = <item>:<amount>
    """

    key = "@giveitem"
    aliases = ["+giveitem"]
    locks = "cmd:perm(Builder)"
    help_category = "Admin"

    def parse(self):
        self.amount_error = False
        parts = self.args.split("=")
        if len(parts) != 2:
            self.target_name = self.item_name = self.amount = None
            return
        self.target_name = parts[0].strip()
        item_part = parts[1].strip().split(":")
        self.item_name = item_part[0].strip().lower()
        try:
            self.amount = int(item_part[1].strip()) if len(item_part) > 1 else 1
        except ValueError:
            self.amount = None
            self.amount_error = True

    def func(self):
        if not require_no_battle_lock(self.caller):
            return
        if not all([self.target_name, self.item_name]):
            self.caller.msg("Usage: @giveitem <player> = <item>:<amount>")
            return
        if self.amount_error:
            self.caller.msg("Amount must be a number.")
            return

        target = self.caller.search(self.target_name)
        if not target or not hasattr(target, "trainer"):
            self.caller.msg("Player not found or has no trainer record.")
            return
        if not require_no_battle_lock(target):
            return

        canonical, _data, item_key = _inventory_item_key(self.item_name)
        if not canonical:
            self.caller.msg(
                item_not_found_message(
                    self.item_name,
                    f"Item '{self.item_name}' not found in ITEMDEX.",
                )
            )
            return

        target.trainer.add_item(item_key, self.amount)
        self.caller.msg(f"Gave {self.amount} x {canonical} to {target.key}.")


class CmdUseItem(Command):
    """Use an item outside of battle.

    Usage:
      +use <item>
      +use <item>=<target>

    Examples:
      +use Rare Candy=1
      +use Rare Candy=Charizard
      +use PP Up=2
      +use PP Max=2
      +use Potion=3
      +use Revive=6
      +use Ether=3/Water Gun
      +use Max Elixir=fusion
      +use Oran Berry=3
      +use Leppa Berry=3/Water Gun
      +use Mystery Berry=3/4
      +use Gold Berry=fusion
      +use Pomeg Berry=3
      +use Protein=3
      +use Health Feather=fusion
      +use Ability Capsule=3
      +use Ability Patch=fusion
      +use Bottle Cap=3/Atk
      +use Gold Bottle Cap=fusion
      +use Fresh Water=3
      +use Max Honey=6
      +use Sacred Ash=party

    Notes:
      Field medicine heals HP, cures status, revives fainted Pokemon and
      restores PP. Targets accept canonical party slots, unambiguous names,
      full Pokemon IDs or your current Fusion. Ether and Max Ether accept
      /<move name or slot>; omitting it selects the first depleted active move.
      Elixirs restore all active moves. Herbs also lower friendship on success.
      PP Up and PP Max prompt for an exact active move name or displayed slot.
      PP Up adds one fifth of base PP, up to three times; PP Max fills the cap.
      Each raises current PP by the capacity gain. Use +use cancel to cancel.
      Targets use the same fresh owned-party/current-Fusion checks as medicine.
      An expired or changed target/moveset needs a new prompt. Eggs cannot use it.
      Rare Candy uses the same fresh target checks and atomically raises one
      level with one bag item, up to level 100. Eggs, boxes, foreign Pokemon
      and inactive Fusion reservations cannot use it. Failed uses spend none.
      Recovery berries and Berry Juice share medicine limits. Leppa restores
      10 PP and Mystery Berry restores 5 PP to one active move, selected by
      /<move name or real slot>, or the first depleted move if omitted.
      Berry/Gold Berry heal 10/30 HP. Burnt thaws freeze; Ice cures burn;
      Mint cures sleep; PRZ Cure handles paralysis; PSN Cure handles poison
      or toxic poison. Miracle cures major saved status, as Lum does.
      Bitter/Persim are confusion-only held berries with no field effect.
      Pomeg/Kelpsy/Qualot/Hondew/Grepa/Tamato lower the matching
      HP/Atk/Def/SpA/SpD/Spe EVs by up to 10 and raise friendship by 10 below
      100, 5 below 200, or 2 at 200+ (cap 255). Either useful effect allows use.
      An ineffective use consumes nothing. EV berries do not revive Pokemon.
      HP Up/Protein/Iron/Calcium/Zinc/Carbos add up to 10 EVs to
      HP/Atk/Def/SpA/SpD/Spe. Health/Muscle/Resist/Genius/Clever/Swift Feather
      add 1 EV to those same stats. Caps are 252 per stat and 510 total;
      partial increases use one item, capped or invalid EVs use none.
      Training preserves HP deficit and fainting; it accepts no move selector.
      Ability Capsule switches ordinary ability slots 0/1. Ability Patch
      switches an ordinary slot to hidden H, or hidden H back to ordinary 0.
      Both use the saved native species/form slots; special abilities, absent
      destinations and single-ability Capsule uses have no effect. Invalid
      saved abilities and transformed/locked forms cannot use these items.
      Hyper Training requires level 50+. Bottle Cap needs /<stat name>:
      HP/Atk/Def/SpA/SpD/Spe. Gold Bottle Cap trains all remaining eligible
      stats with one copy and no selector. Trained stats use effective IV 31;
      genetic IVs remain unchanged. Perfect/already-trained stats spend none.
      Training preserves HP deficit/fainting and appears on +party <slot>.
      Other combat-trigger and contest berries have no manual field route.
      Healing foods/drinks and status foods use the same field medicine rules.
      Max Honey revives one fainted target to full HP; Sacred Ash=party revives
      eligible fainted party members with one item, excluding eggs/boxes/Fusion.
      These equivalents are field-only and accept no move selector.
      Battle items use +battle/item while a battle is waiting for your action.
      +heal restores your party at a Pokemon Center.
    """

    key = "+use"
    aliases = ["+useitem"]
    locks = "cmd:all()"
    help_category = "Inventory"

    def func(self):
        if not require_no_battle_lock(self.caller):
            return
        args = self.args.strip()
        trainer = getattr(self.caller, "trainer", None)

        if not trainer:
            self.caller.msg("You have no trainer record.")
            return

        pending = getattr(self.caller.ndb, "pending_pp_item", None)

        if pending and "=" not in args:
            if args.casefold() == "cancel":
                self.caller.ndb.pending_pp_item = None
                self.caller.msg("PP item selection cancelled. No item was consumed.")
                return
            from pokemon.services.field_pp import FieldPPCapacityUse

            service = FieldPPCapacityUse(self.caller)
            try:
                used = service.confirm(pending, args)
            except ValueError as error:
                self.caller.msg(str(error))
                return
            if used:
                service.notify_success(pending["item"], pending["pokemon_id"])
            return

        if not args:
            self.caller.msg("Usage: +use <item> or +use <item>=<target>")
            return

        parsed = _parse_item_use_args(args)
        canonical = parsed.canonical
        item_data = parsed.item_data
        item_name = parsed.item_key

        if parsed.ambiguous_item_sides:
            self.caller.msg(
                f"Ambiguous item use: both '{parsed.item_query}' and '{parsed.target_query}' look like item names. "
                "Use +use <item>=<target>; if your Pokemon shares an item name, use its party slot."
            )
            return

        if not canonical:
            self.caller.msg(
                item_not_found_message(
                    parsed.item_query,
                    f"No such item '{parsed.item_query}' exists.",
                )
            )
            return

        from pokemon.services.field_berries import FieldBerryUse
        from pokemon.services.field_food import FieldFoodUse
        from pokemon.services.field_items import FieldMedicineUse
        from pokemon.services.field_progression import FieldRareCandyUse
        from pokemon.services.field_training import FieldTrainingUse
        from pokemon.services.field_abilities import FieldAbilityUse
        from pokemon.services.field_hyper_training import FieldHyperTrainingUse

        field_service = next((service for service in (FieldMedicineUse, FieldBerryUse, FieldFoodUse,
                                                     FieldRareCandyUse, FieldTrainingUse, FieldAbilityUse,
                                                     FieldHyperTrainingUse)
                              if service.supports(item_name)), None)
        if field_service is not None:
            display_name = _display_item_name(item_data, canonical)
            if not parsed.target_query:
                selector = "party" if getattr(item_data, "target_scope", "") == "party" else "<party slot, Pokemon name or fusion>[/<move>]"
                if hasattr(field_service, "usage_target"):
                    selector = field_service.usage_target(item_name)
                self.caller.msg(f"Usage: +use {display_name}={selector}")
                return
            target_query, separator, move = parsed.target_query.partition("/")
            if not target_query.strip() or (separator and not move.strip()):
                label = getattr(field_service, "selection_label", "move name or slot")
                self.caller.msg(f"Specify a Pokemon target and, after '/', a {label}.")
                return
            try:
                service = field_service(self.caller)
                used = service.use(
                    item_name, target_query.strip(), move=move.strip() if separator else None
                )
            except ValueError as error:
                self.caller.msg(str(error))
                return
            if used:
                service.notify_success(display_name, target_query.strip())
            elif used is not None:
                self.caller.msg(f"{display_name} had no effect. No item was consumed.")
            return

        if item_name in {"ppup", "ppmax"}:
            if not parsed.target_query:
                self.caller.msg(f"Usage: +use {_display_item_name(item_data, canonical)}=<party slot or Pokemon name>")
                return
            from pokemon.services.field_pp import FieldPPCapacityUse

            try:
                FieldPPCapacityUse(self.caller).use(item_name, parsed.target_query)
            except ValueError as error:
                self.caller.msg(str(error))
            return

        if parsed.target_query is not None:
            _target, error = _resolve_use_target(self.caller, parsed.target_query)
            if error:
                self.caller.msg(error)
                return

        if not _trainer_has_item(trainer, item_name):
            self.caller.msg(f"You don't have any {_display_item_name(item_data, canonical)} to use.")
            return

        self.caller.msg(
            f"{_display_item_name(item_data, canonical)} is not usable outside battle yet. "
            "Supported field items include medicine, recovery/EV berries, Berry Juice, vitamins/feathers, Ability Capsule/Patch, Bottle Caps, Rare Candy, PP Up and PP Max. "
            "Use +heal at a Pokemon Center to restore your party; "
            "battle items use +item <item> during battle."
        )
