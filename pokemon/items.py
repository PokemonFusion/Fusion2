"""Metadata for supported game items omitted from the competitive item dex."""

from dataclasses import dataclass

from pokemon.names import normalize_name


@dataclass(frozen=True)
class GameplayItem:
    """Share a complete display name and description across item interfaces."""

    name: str
    desc: str

    @property
    def raw(self) -> dict[str, object]:
        """Match the metadata interface used by dex-backed item displays."""
        return {"name": self.name, "desc": self.desc}


@dataclass(frozen=True)
class FieldRecoveryItem(GameplayItem):
    """One source for field medicine effects, display metadata and reference cost."""

    price: int
    effect: str
    amount: int | None = None
    target_scope: str = "single"
    category: str = "Medicine"

    @property
    def raw(self) -> dict[str, object]:
        """Expose the same metadata interface used by itemdex and inventory."""
        return {**super().raw, "price": self.price, "category": self.category,
                "effect": self.effect, "amount": self.amount,
                "targetScope": self.target_scope, "fieldOnly": True}


@dataclass(frozen=True)
class HeldEscapeItem(GameplayItem):
    """Describe a reusable held escape effect without capture capability."""

    price: int = 4000
    category: str = "Held Items"

    @property
    def raw(self) -> dict[str, object]:
        """Expose ordinary item interfaces and an explicit non-capture flag."""
        return {**super().raw, "price": self.price, "category": self.category,
                "isPokeball": False, "heldEffect": "escape", "consumed": False}


FIELD_RECOVERY_ITEMS = {
    "freshwater": FieldRecoveryItem("Fresh Water", "Field use: restores up to 30 HP to one living Pokemon.",
                                   price=200, effect="heal", amount=30),
    "sodapop": FieldRecoveryItem("Soda Pop", "Field use: restores up to 50 HP to one living Pokemon.",
                                price=300, effect="heal", amount=50),
    "lemonade": FieldRecoveryItem("Lemonade", "Field use: restores up to 70 HP to one living Pokemon.",
                                 price=400, effect="heal", amount=70),
    "moomoomilk": FieldRecoveryItem("Moomoo Milk", "Field use: restores up to 100 HP to one living Pokemon.",
                                   price=600, effect="heal", amount=100),
    "sweetheart": FieldRecoveryItem("Sweet Heart", "Field use: restores up to 20 HP to one living Pokemon.",
                                   price=3000, effect="heal", amount=20),
    "lavacookie": FieldRecoveryItem("Lava Cookie", "Field use: cures one living Pokemon's major status condition.",
                                   price=350, effect="status"),
    "oldgateau": FieldRecoveryItem("Old Gateau", "Field use: cures one living Pokemon's major status condition.",
                                  price=350, effect="status"),
    "casteliacone": FieldRecoveryItem("Casteliacone", "Field use: cures one living Pokemon's major status condition.",
                                     price=350, effect="status"),
    "lumiosegalette": FieldRecoveryItem("Lumiose Galette", "Field use: cures one living Pokemon's major status condition.",
                                       price=350, effect="status"),
    "shaloursable": FieldRecoveryItem("Shalour Sable", "Field use: cures one living Pokemon's major status condition.",
                                     price=350, effect="status"),
    "bigmalasada": FieldRecoveryItem("Big Malasada", "Field use: cures one living Pokemon's major status condition.",
                                    price=350, effect="status"),
    "pewtercrunchies": FieldRecoveryItem("Pewter Crunchies", "Field use: cures one living Pokemon's major status condition.",
                                        price=250, effect="status"),
    "maxhoney": FieldRecoveryItem("Max Honey", "Field use: revives one fainted Pokemon to full HP. No unlock effect.",
                                 price=4000, effect="revive"),
    "sacredash": FieldRecoveryItem("Sacred Ash", "Field use with =party: revives eligible fainted party Pokemon to full HP.",
                                  price=50000, effect="revive", target_scope="party"),
}


GAMEPLAY_ITEMS = {
    "everstone": GameplayItem("Everstone", "Prevents the holder from evolving."),
    "blackaugurite": GameplayItem("Black Augurite", "Evolves Scyther into Kleavor."),
    "smokeball": HeldEscapeItem(
        "Smoke Ball", "Held: guarantees the acting holder's escape from eligible wild battles with +flee. "
        "Reusable; item suppression and trainer/scripted no-flee restrictions still apply. Not a capture ball."
    ),
    **FIELD_RECOVERY_ITEMS,
}


def get_gameplay_item(name: object) -> GameplayItem | None:
    """Resolve complete normalized names; prefixes remain invalid."""
    return GAMEPLAY_ITEMS.get(normalize_name(name))


def is_capture_ball(name: object) -> bool:
    """Require complete canonical capture metadata instead of a name suffix."""
    from pokemon.dex import ITEMDEX
    from pokemon.names import resolve_dex_entry

    item = resolve_dex_entry(ITEMDEX, getattr(name, "name", name))
    raw = item if isinstance(item, dict) else getattr(item, "raw", {})
    return bool(raw and raw.get("isPokeball") is True)
