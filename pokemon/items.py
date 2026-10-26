"""Metadata for supported game items omitted from the competitive item dex."""

from dataclasses import dataclass

from pokemon.names import normalize_name


BATTLE_RECOVERY_FOODS = frozenset({
    "freshwater", "sodapop", "lemonade", "moomoomilk", "sweetheart",
    "lavacookie", "oldgateau", "casteliacone", "lumiosegalette", "shaloursable",
    "bigmalasada", "pewtercrunchies", "maxhoney",
})


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
                "targetScope": self.target_scope,
                "fieldOnly": normalize_name(self.name) not in BATTLE_RECOVERY_FOODS}


@dataclass(frozen=True)
class EvolutionItem(GameplayItem):
    """Describe a bag evolution item; eligibility stays in reviewed rules."""

    price: int
    category: str = "Evolution Items"

    @property
    def raw(self) -> dict[str, object]:
        """Share reference price and inventory category with normal interfaces."""
        return {**super().raw, "price": self.price, "category": self.category}


@dataclass(frozen=True)
class HeldQualificationItem(GameplayItem):
    """Identify encounter qualification without a consumable evolution effect."""

    price: int = 1500
    category: str = "Held Items"

    @property
    def raw(self) -> dict[str, object]:
        """Expose ordinary display/equip metadata, with no capture capability."""
        return {**super().raw, "price": self.price, "category": self.category,
                "isPokeball": False, "qualificationOnly": True}


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


@dataclass(frozen=True)
class EVTrainingItem(GameplayItem):
    """Describe a field-only EV supplement or one atomic all-stat reset."""

    price: int
    stat: str | None
    amount: int | None = 10

    @property
    def raw(self) -> dict[str, object]:
        """Expose truthful itemdex/inventory metadata without a battle activation."""
        return {**super().raw, "price": self.price, "category": "Training Items",
                "effect": "ev" if self.stat else "ev-reset", "stat": self.stat,
                "amount": self.amount, "fieldOnly": True}


@dataclass(frozen=True)
class ExpCandyItem(GameplayItem):
    """Describe one bounded field EXP gain; activation uses the atomic service."""

    amount: int

    @property
    def raw(self) -> dict[str, object]:
        """Share the authored amount/price without inventing a held/battle effect."""
        return {**super().raw, "price": self.amount, "category": "Training Items",
                "effect": "exp", "amount": self.amount, "fieldOnly": True}


@dataclass(frozen=True)
class BattleBoosterItem(GameplayItem):
    """Publish exact manual bag effects without adding field or held callbacks."""

    effect: str
    price: int = 1000

    @property
    def raw(self) -> dict[str, object]:
        """Keep named battle-only policy separate from arbitrary dex callbacks."""
        return {**super().raw, "price": self.price, "category": "Battle Items",
                "effect": self.effect, "battleOnly": True, "isPokeball": False}


BATTLE_BOOSTER_ITEMS = {
    normalize_name(name): BattleBoosterItem(name,
        f"Manual battle use: {description} Use +item [acting slot] {name}=<actor's party slot>. "
        "Current conscious owned actor only; two-participant singles/doubles. "
        "Embargo prevents use. No field or held effect.", effect, price)
    for name, description, effect, price in (
        ("X Attack", "Attack +2 stages through normal ability rules.", "boost:atk:2", 1000),
        ("X Defense", "Defense +2 stages through normal ability rules.", "boost:def:2", 1000),
        ("X Sp. Atk", "Special Attack +2 stages through normal ability rules.", "boost:spa:2", 1000),
        ("X Sp. Def", "Special Defense +2 stages through normal ability rules.", "boost:spd:2", 1000),
        ("X Speed", "Speed +2 stages through normal ability rules.", "boost:spe:2", 1000),
        ("X Accuracy", "Accuracy +2 stages through normal ability rules.", "boost:accuracy:2", 1000),
        ("Dire Hit", "Focus Energy (+2 critical stages); repeat active use has no effect.", "focusenergy", 1000),
        ("Guard Spec.", "Side Mist for five turns including activation; active use cannot refresh it.", "mist:5", 1500))
}


EXP_CANDY_ITEMS = {
    normalize_name("Exp. Candy " + size): ExpCandyItem(
        "Exp. Candy " + size,
        f"Field use: grants up to {amount} EXP within the species' level100 threshold. "
        "Use +use Exp. Candy " + size + "=<current target>. Earned moves stay stored; "
        "use +learn pending for active choices. No evolution, revival, held or manual battle effect.",
        amount)
    for size, amount in (("XS", 100), ("S", 800), ("M", 3000), ("L", 10000), ("XL", 30000))
}


FIELD_TRAINING_ITEMS = {
    normalize_name(name): EVTrainingItem(
        name, f"Field use: adds up to 10 {stat} EVs within stat/total caps. "
        f"Use +use {name}=<current target>. No held or manual battle effect.", 10000, stat)
    for name, stat in (("Health Mochi", "HP"), ("Muscle Mochi", "Attack"),
                       ("Resist Mochi", "Defense"), ("Genius Mochi", "Special Attack"),
                       ("Clever Mochi", "Special Defense"), ("Swift Mochi", "Speed"))
}
FIELD_TRAINING_ITEMS["freshstartmochi"] = EVTrainingItem(
    "Fresh-Start Mochi", "Field use: resets all six valid EVs to zero together. "
    "An all-zero target has no effect and consumes nothing. Use +use Fresh-Start Mochi=<current target>. "
    "Preserves genetic Nature, IVs, Hyper Training and progression; no held or manual battle effect.",
    20000, None, None)


FIELD_RECOVERY_ITEMS = {
    "freshwater": FieldRecoveryItem("Fresh Water", "Field or battle use: restores up to 30 HP to one living Pokemon.",
                                   price=200, effect="heal", amount=30),
    "sodapop": FieldRecoveryItem("Soda Pop", "Field or battle use: restores up to 50 HP to one living Pokemon.",
                                price=300, effect="heal", amount=50),
    "lemonade": FieldRecoveryItem("Lemonade", "Field or battle use: restores up to 70 HP to one living Pokemon.",
                                 price=400, effect="heal", amount=70),
    "moomoomilk": FieldRecoveryItem("Moomoo Milk", "Field or battle use: restores up to 100 HP to one living Pokemon.",
                                   price=600, effect="heal", amount=100),
    "sweetheart": FieldRecoveryItem("Sweet Heart", "Field or battle use: restores up to 20 HP to one living Pokemon.",
                                   price=3000, effect="heal", amount=20),
    "lavacookie": FieldRecoveryItem("Lava Cookie", "Field or battle use: cures one living Pokemon's major status condition.",
                                   price=350, effect="status"),
    "oldgateau": FieldRecoveryItem("Old Gateau", "Field or battle use: cures one living Pokemon's major status condition.",
                                  price=350, effect="status"),
    "casteliacone": FieldRecoveryItem("Casteliacone", "Field or battle use: cures one living Pokemon's major status condition.",
                                     price=350, effect="status"),
    "lumiosegalette": FieldRecoveryItem("Lumiose Galette", "Field or battle use: cures one living Pokemon's major status condition.",
                                       price=350, effect="status"),
    "shaloursable": FieldRecoveryItem("Shalour Sable", "Field or battle use: cures one living Pokemon's major status condition.",
                                     price=350, effect="status"),
    "bigmalasada": FieldRecoveryItem("Big Malasada", "Field or battle use: cures one living Pokemon's major status condition.",
                                    price=350, effect="status"),
    "pewtercrunchies": FieldRecoveryItem("Pewter Crunchies", "Field or battle use: cures one living Pokemon's major status condition.",
                                        price=250, effect="status"),
    "maxhoney": FieldRecoveryItem("Max Honey", "Field or battle use: revives one fainted Pokemon to full HP. No unlock effect.",
                                 price=4000, effect="revive"),
    "sacredash": FieldRecoveryItem("Sacred Ash", "Field use with =party: revives eligible fainted party Pokemon to full HP.",
                                  price=50000, effect="revive", target_scope="party"),
}


HYPER_TRAINING_ITEMS = {
    "bottlecap": GameplayItem(
        "Bottle Cap", "Hyper Training at level 50+: +use Bottle Cap=<target>/<HP|Atk|Def|SpA|SpD|Spe>. "
        "One eligible stat uses effective IV 31; genetic IVs stay unchanged. Consumes one bag copy on useful training."
    ),
    "goldbottlecap": GameplayItem(
        "Gold Bottle Cap", "Hyper Training at level 50+: +use Gold Bottle Cap=<target>. "
        "One copy trains all remaining eligible stats to effective IV 31 without changing genetic IVs. "
        "No effect when every stat is already trained or genetically perfect."
    ),
}


FIELD_RECOVERY_EQUIVALENTS = {
    "ragecandybar": FieldRecoveryItem(
        "Rage Candy Bar", "Field use: cures one living owned Pokemon's major status. "
        "PF2 medicinal equivalent; no story unlock or HP restoration.",
        price=350, effect="status",
    ),
    "hopoberry": FieldRecoveryItem(
        "Hopo Berry", "Field use: restores up to 10 PP to one selected active move. "
        "Use +use Hopo Berry=<target>/<move name or actual slot>. No held or lure effect.",
        price=300, effect="pp", amount=10, category="Berries",
    ),
}


GAMEPLAY_ITEMS = {
    **BATTLE_BOOSTER_ITEMS,
    **EXP_CANDY_ITEMS,
    **FIELD_TRAINING_ITEMS,
    **FIELD_RECOVERY_EQUIVALENTS,
    "gimmighoulcoin": EvolutionItem(
        "Gimmighoul Coin",
        "PF2 manual evolution: use +evolve <full-id> Gimmighoul Coin on native Chest Gimmighoul at level 2–100. Consumes 999 bag coins; Roaming and held-only coins do not qualify.",
        price=10,
    ),
    **HYPER_TRAINING_ITEMS,
    "leaderscrest": HeldQualificationItem(
        "Leader's Crest", "Marks authored leader Bisharp opponents. Your Bisharp must personally KO three "
        "qualifying leaders in won NPC/wild battles, then gain a level and use +evolve. "
        "No player-held or bag Crest is required or consumed; +party <slot> shows progress.",
    ),
    "everstone": GameplayItem("Everstone", "Prevents the holder from evolving."),
    "blackaugurite": GameplayItem("Black Augurite", "Evolves Scyther into Kleavor."),
    "scrollofdarkness": EvolutionItem(
        "Scroll of Darkness", "Use +evolve <id> Scroll of Darkness on Kubfu for Urshifu (Single Strike). "
        "PF2's non-plot item route replaces tower completion. Consumes one bag copy; "
        "held-only copies do not activate it. The Waters Scroll selects the other style.",
        price=10000,
    ),
    "scrollofwaters": EvolutionItem(
        "Scroll of Waters", "Use +evolve <id> Scroll of Waters on Kubfu for Urshifu-Rapid-Strike. "
        "PF2's non-plot item route replaces tower completion. Consumes one bag copy; "
        "held-only copies do not activate it. The Darkness Scroll selects the other style.",
        price=10000,
    ),
    "peatblock": EvolutionItem(
        "Peat Block", "Use +evolve <id> Peat Block on Ursaring for ordinary Ursaluna. "
        "PF2 replaces the full-moon condition with explicit item use. "
        "Consumes one bag copy; held-only copies do not activate it. No Bloodmoon form.",
        price=10000,
    ),
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
