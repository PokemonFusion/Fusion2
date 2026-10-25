"""Seven separately versioned finite counters from the acquisition contract.

These explicit builder APIs author content only when invoked; importing them,
starting the game or retrying an installation never resets sold stock.
"""

from pokemon.services.item_supply import ItemSupplyRoute


class FiniteItemSupplyRoute(ItemSupplyRoute):
    """Share the guarded six-item installer without expanding its offer vector."""

    offers = ()
    room_name = ""
    entrance = ""
    player_route = "+use <item>=<party slot>"

    @classmethod
    def recipe(cls):
        """Return only the exact reviewed prices/caps from this source revision."""
        from pokemon.middleware import get_item_by_name

        if not cls.offers or len({name for name, _, _ in cls.offers}) != len(cls.offers):
            raise ValueError("A reviewed finite source is required.")
        for name, price, cap in cls.offers:
            if (
                type(price) is not int
                or price <= 0
                or type(cap) is not int
                or cap <= 0
                or get_item_by_name(name)[1] is None
            ):
                raise ValueError("Invalid finite source offer.")
        return {
            "version": 1,
            "key": cls.key,
            "room": cls.room_name,
            "entrance": cls.entrance,
            "return_exit": "back",
            "refill": "none",
            "buy_only": True,
            "offers": [
                {"item": name, "price": price, "quantity": cap} for name, price, cap in cls.offers
            ],
        }

    @classmethod
    def description(cls, data):
        """Explain exact contents and existing player routes without a plot gate."""
        names = ", ".join(offer["item"] for offer in data["offers"])
        return (
            f"A sign lists finite supplies: {names}. Use +store to buy, "
            f"+inventory and +itemdex <item> to inspect, and {cls.player_route}. "
            "The back exit returns to the hub. There is no refill or resale."
        )

    @classmethod
    def install(cls, hub):
        """Require explicit approved setup; clear marker caches after outer rollback."""
        from django.db import connection, transaction
        from pokemon.services.item_shop import ShopPurchase

        try:
            return super().install(hub)
        finally:
            hub.attributes.reset_cache()
            if connection.in_atomic_block:
                transaction.on_commit(
                    lambda: ShopPurchase.refresh_attributes(hub, cls.marker), robust=True
                )
            else:
                ShopPurchase.refresh_attributes(hub, cls.marker)


class StatusMedicineSupply(FiniteItemSupplyRoute):
    """Six medicines, with useful-condition validation in existing item routes."""

    key = "status-medicine-supply-v1"
    marker = "status_medicine_supply_v1"
    room_name, entrance = "Status Medicine Counter", "statusmeds"
    offers = (
        ("Antidote", 100, 20),
        ("Paralyze Heal", 200, 20),
        ("Awakening", 250, 10),
        ("Burn Heal", 250, 10),
        ("Ice Heal", 250, 10),
        ("Full Heal", 600, 10),
    )
    names = frozenset(name for name, _, _ in offers)


class StrongMedicineSupply(FiniteItemSupplyRoute):
    """Four stronger living/fainted recovery offers."""

    key = "strong-medicine-supply-v1"
    marker = "strong_medicine_supply_v1"
    room_name, entrance = "Recovery Medicine Counter", "recoverymeds"
    offers = (
        ("Super Potion", 700, 20),
        ("Hyper Potion", 1500, 10),
        ("Revive", 1500, 10),
        ("Max Revive", 4000, 2),
    )
    names = frozenset(name for name, _, _ in offers)


class PPMedicineSupply(FiniteItemSupplyRoute):
    """Four existing PP recovery effects, without capacity shortcuts."""

    key = "pp-medicine-supply-v1"
    marker = "pp_medicine_supply_v1"
    room_name, entrance = "PP Recovery Counter", "ppmeds"
    player_route = "+use Ether=<party slot>/<move>, or the existing Elixir route"
    offers = (
        ("Ether", 1200, 10),
        ("Max Ether", 2400, 5),
        ("Elixir", 3000, 5),
        ("Max Elixir", 6000, 2),
    )
    names = frozenset(name for name, _, _ in offers)


class EvolutionStoneSupply(FiniteItemSupplyRoute):
    """Six native evolution stones; Fire Stone stays in the original counter."""

    key = "evolution-stone-supply-v1"
    marker = "evolution_stone_supply_v1"
    room_name, entrance = "Evolution Stone Counter", "stones"
    player_route = "+evolve <full Pokemon ID> <stone> for an eligible native species"
    offers = tuple(
        (name + " Stone", 3000, 5) for name in ("Water", "Thunder", "Leaf", "Ice", "Sun", "Moon")
    )
    names = frozenset(name for name, _, _ in offers)


class VitaminSupply(FiniteItemSupplyRoute):
    """Six existing EV effects, retaining shared field/stat caps."""

    key = "vitamin-supply-v1"
    marker = "vitamin_supply_v1"
    room_name, entrance = "Vitamin Counter", "vitamins"
    offers = tuple(
        (name, 10000, 2) for name in ("HP Up", "Protein", "Iron", "Calcium", "Zinc", "Carbos")
    )
    names = frozenset(name for name, _, _ in offers)


class CapacityAbilitySupply(FiniteItemSupplyRoute):
    """Four PP-capacity/native-ability offers, without skipping target guards."""

    key = "capacity-ability-supply-v1"
    marker = "capacity_ability_supply_v1"
    room_name, entrance = "Capacity and Ability Counter", "capacity"
    player_route = "+use <item>=<party slot>, selecting the actual move when prompted"
    offers = (
        ("PP Up", 9800, 2),
        ("PP Max", 15000, 1),
        ("Ability Capsule", 20000, 1),
        ("Ability Patch", 30000, 1),
    )
    names = frozenset(name for name, _, _ in offers)


class HeldStapleSupply(FiniteItemSupplyRoute):
    """Six bounded held recovery/survival/choice offers, no extra item effects."""

    key = "held-staple-supply-v1"
    marker = "held_staple_supply_v1"
    room_name, entrance = "Held Item Counter", "helditems"
    player_route = "+hold <party slot>=<item> to equip for an eligible ordinary battle"
    offers = (
        ("Sitrus Berry", 200, 10),
        ("Lum Berry", 600, 5),
        ("Focus Sash", 5000, 2),
        ("Choice Band", 5000, 1),
        ("Choice Specs", 5000, 1),
        ("Choice Scarf", 5000, 1),
    )
    names = frozenset(name for name, _, _ in offers)


FINITE_SUPPLY_ROUTES = {
    877: StatusMedicineSupply,
    878: StrongMedicineSupply,
    879: PPMedicineSupply,
    880: EvolutionStoneSupply,
    881: VitaminSupply,
    882: CapacityAbilitySupply,
    883: HeldStapleSupply,
}
