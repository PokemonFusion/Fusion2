"""Explicit, versioned operator replenishment; never a startup or player hook."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
import re
from uuid import UUID, uuid4


class ReplenishmentError(ValueError):
    """An operator request was refused without changing stock or its ledger."""


@dataclass(frozen=True)
class ReplenishmentPolicy:
    """A reviewed source revision and its immutable initial offer vector.

    This is authoring input, never inferred from remaining stock. Constructing
    a policy does not install a source or authorize any existing-world write.
    """

    source: str
    version: int
    offers: tuple[tuple[str, int, int], ...]

    # Only consumable offers selected by the acquisition policy. Other families
    # need their own reviewed policy change, rather than a catalog-wide refill.
    allowed = frozenset(
        {
            "Potion",
            "Oran Berry",
            "Fresh Water",
            "Antidote",
            "Paralyze Heal",
            "Awakening",
            "Burn Heal",
            "Ice Heal",
            "Full Heal",
            "Super Potion",
            "Hyper Potion",
            "Revive",
            "Max Revive",
            "Ether",
            "Max Ether",
            "Elixir",
            "Max Elixir",
            "HP Up",
            "Protein",
            "Iron",
            "Calcium",
            "Zinc",
            "Carbos",
            "PP Up",
            "PP Max",
            "Ability Capsule",
            "Ability Patch",
        }
    )

    def __post_init__(self):
        """Reject ambiguous names, booleans, unlimited stock and legacy source IDs."""
        if (
            not isinstance(self.source, str)
            or not re.fullmatch(r"[a-z][a-z0-9-]{2,79}", self.source)
            or self.source == "nonplot-item-supply-v1"
            or type(self.version) is not int
            or self.version < 1
            or type(self.offers) is not tuple
            or not self.offers
        ):
            raise ReplenishmentError("A reviewed, separately versioned source policy is required.")
        names = []
        for offer in self.offers:
            if (
                type(offer) is not tuple
                or len(offer) != 3
                or not isinstance(offer[0], str)
                or offer[0] not in self.allowed
                or any(type(value) is not int or value <= 0 for value in offer[1:])
            ):
                raise ReplenishmentError("Only exact finite reviewed consumable offers may opt in.")
            names.append(offer[0])
        if len(set(names)) != len(names):
            raise ReplenishmentError("Duplicate offers require review.")

    def vector(self):
        """Return a fresh canonical mapping, preserving strict prices and caps."""
        return {name: {"price": price, "quantity": cap} for name, price, cap in sorted(self.offers)}

    def identity(self):
        """Bind receipts to exact source, version, prices and initial quantities."""
        return {"source": self.source, "version": self.version, "offers": self.vector()}


class ItemReplenishment:
    """Serialize explicit refills with purchases on the shop's ObjectDB row.

    Persist the opt-in marker and append-only per-request receipts as ordinary
    Attributes. SQL writes bypass shared Attribute caches until outer commit.
    The actor must be a current active Builder-or-higher AccountDB, checked in
    SQL for every action. Returning from a caller-owned transaction is tentative.
    """

    marker = "item_replenishment"
    category = "item_replenishment_receipts"
    interval = timedelta(hours=24)

    @staticmethod
    def clock():
        """Read server UTC; clients and operator arguments cannot supply time."""
        return datetime.now(timezone.utc)

    @staticmethod
    def digest(value):
        """Hash portable JSON rather than a mutable/cached Python identity."""
        return hashlib.sha256(
            json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()

    @staticmethod
    def timestamp(value):
        """Accept only canonical aware UTC timestamps, never local/naive time."""
        try:
            parsed = datetime.fromisoformat(value)
            if parsed.utcoffset() != timedelta(0) or parsed.isoformat() != value:
                raise ValueError
            return parsed
        except (TypeError, ValueError) as error:
            raise ReplenishmentError("The replenishment clock or ledger needs review.") from error

    @classmethod
    def now(cls):
        """Validate the server clock before comparing elapsed time."""
        value = cls.clock()
        if not isinstance(value, datetime):
            raise ReplenishmentError("The server UTC clock is unavailable.")
        return cls.timestamp(value.isoformat())

    @staticmethod
    def authorize(actor):
        """Refresh real account permissions; object flags and stale caches grant nothing."""
        from django.conf import settings
        from evennia.accounts.models import AccountDB

        if not isinstance(actor, AccountDB) or not actor.pk:
            raise ReplenishmentError("An active Builder account is required.")
        row = (
            AccountDB.objects.select_for_update()
            .filter(pk=actor.pk)
            .values("is_active", "is_superuser", "db_is_bot")
            .first()
        )
        if not row or not row["is_active"] or row["db_is_bot"]:
            raise ReplenishmentError("An active Builder account is required.")
        hierarchy = [permission.casefold() for permission in settings.PERMISSION_HIERARCHY]
        allowed = (
            set(hierarchy[hierarchy.index("builder") :]) if "builder" in hierarchy else {"builder"}
        )
        permissions = AccountDB.objects.filter(
            pk=actor.pk, db_tags__db_tagtype="permission"
        ).values_list("db_tags__db_key", flat=True)
        if not row["is_superuser"] and not allowed.intersection(
            key.casefold() for key in permissions
        ):
            raise ReplenishmentError("An active Builder account is required.")

    @classmethod
    @contextmanager
    def locked(cls, room, actor):
        """Share the purchase lock and restore committed Attribute cache state."""
        from django.db import connection, transaction
        from evennia.objects.models import ObjectDB
        from pokemon.services.item_shop import ShopPurchase

        try:
            with transaction.atomic():
                cls.authorize(actor)
                room = ObjectDB.objects.select_for_update().get(pk=room.pk)
                yield room
        except ObjectDB.DoesNotExist as error:
            raise ReplenishmentError("The source no longer exists.") from error
        finally:
            if connection.in_atomic_block:
                room.attributes.reset_cache()
                transaction.on_commit(
                    lambda: ShopPurchase.refresh_attributes(room, cls.marker, "store_inventory"),
                    robust=True,
                )
            else:
                ShopPurchase.refresh_attributes(room, cls.marker, "store_inventory")

    @staticmethod
    def read(room, key, *, category=None):
        """Read authoritative SQL and reject ambiguous duplicate ledger Attributes."""
        from evennia.utils.dbserialize import from_pickle

        rows = list(
            room.db_attributes.filter(
                db_key=key, db_category=category, db_attrtype=None
            ).values_list("db_value", flat=True)
        )
        if len(rows) > 1:
            raise ReplenishmentError("Duplicate source records need review.")
        return from_pickle(rows[0]) if rows else None

    @staticmethod
    def write(room, key, value, *, category=None, create=False):
        """Write SQL only; no uncommitted Attribute handler publication."""
        from evennia.typeclasses.models import Attribute
        from evennia.utils.dbserialize import to_pickle

        rows = room.db_attributes.filter(db_key=key, db_category=category, db_attrtype=None)
        if create:
            if rows.exists():
                raise ReplenishmentError("The source receipt already exists.")
            attribute = Attribute.objects.create(
                db_key=key,
                db_category=category,
                db_model=room.__dbclass__.__name__.lower(),
                db_value=to_pickle(value),
            )
            room.db_attributes.add(attribute)
        elif rows.update(db_value=to_pickle(value)) != 1:
            raise ReplenishmentError("The source ledger is unavailable.")

    @classmethod
    def stock(cls, room, policy):
        """Reject source/price/quantity drift and any legacy six-item route."""
        from pokemon.services.item_supply import ItemSupplyRoute

        if (
            room.db_tags.filter(db_key=ItemSupplyRoute.key, db_category="item_supply").exists()
            or cls.read(room, "is_item_shop") is not True
            or cls.read(room, "store_buy_only") is not True
        ):
            raise ReplenishmentError("Only a separately reviewed buy-only source may opt in.")
        raw, caps = cls.read(room, "store_inventory"), policy.vector()
        if type(raw) is not dict or set(raw) != set(caps):
            raise ReplenishmentError("The source offer set drifted; nothing was refilled.")
        for name, offer in raw.items():
            if (
                type(offer) is not dict
                or set(offer) != {"price", "quantity"}
                or type(offer["price"]) is not int
                or offer["price"] != caps[name]["price"]
                or type(offer["quantity"]) is not int
                or not 0 <= offer["quantity"] <= caps[name]["quantity"]
            ):
                raise ReplenishmentError(
                    "The source price or quantity drifted; nothing was refilled."
                )
        return raw

    @classmethod
    def state(cls, room, policy):
        """Validate source binding, monotone sequence and latest durable receipt."""
        state = cls.read(room, cls.marker)
        if (
            type(state) is not dict
            or set(state)
            != {
                "schema",
                "room",
                "instance",
                "policy",
                "initialized",
                "last",
                "sequence",
                "request",
            }
            or type(state["schema"]) is not int
            or state["schema"] != 1
            or state["room"] != room.pk
            or state["policy"] != policy.identity()
            or type(state["sequence"]) is not int
            or state["sequence"] < 0
        ):
            raise ReplenishmentError("The source opt-in or policy revision needs review.")
        try:
            if str(UUID(state["instance"])) != state["instance"]:
                raise ValueError
        except (ValueError, TypeError, AttributeError) as error:
            raise ReplenishmentError("The source instance needs review.") from error
        initial, last = cls.timestamp(state["initialized"]), cls.timestamp(state["last"])
        if last < initial:
            raise ReplenishmentError("The source clock moved backwards.")
        if state["sequence"] == 0:
            if state["request"] is not None or initial != last:
                raise ReplenishmentError("The initial ledger needs review.")
        else:
            receipt = cls.read(room, str(state["request"]), category=cls.category)
            cls.validate_receipt(receipt, state, policy)
            if receipt["sequence"] != state["sequence"] or receipt["committed_at"] != state["last"]:
                raise ReplenishmentError("The latest replenishment receipt needs review.")
        return state

    @classmethod
    def validate_receipt(cls, receipt, state, policy):
        """Require an intact exact stock delta and source/window identity."""
        try:
            body = {key: value for key, value in receipt.items() if key != "digest"}
            if (
                receipt["digest"] != cls.digest(body)
                or receipt["instance"] != state["instance"]
                or receipt["room"] != state["room"]
                or receipt["policy"] != policy.identity()
                or type(receipt["sequence"]) is not int
                or not 1 <= receipt["sequence"] <= state["sequence"]
                or receipt["after"] != policy.vector()
                or receipt["eligible_at"]
                != (cls.timestamp(receipt["previous_at"]) + cls.interval).isoformat()
                or cls.timestamp(receipt["committed_at"]) < cls.timestamp(receipt["eligible_at"])
                or set(receipt["before"]) != set(policy.vector())
                or receipt["delta"]
                != {
                    name: cap["quantity"] - receipt["before"][name]["quantity"]
                    for name, cap in policy.vector().items()
                }
                or any(type(delta) is not int or delta < 0 for delta in receipt["delta"].values())
                or not any(receipt["delta"].values())
            ):
                raise ValueError
        except (AttributeError, KeyError, TypeError, ValueError) as error:
            raise ReplenishmentError("The replenishment receipt needs review.") from error

    @classmethod
    def configure(cls, room, policy, actor):
        """Explicitly bind an untouched full counter; retries never refill it.

        Requires separate world-change authority. No rebinding or policy
        upgrades are implicit. First eligibility starts 24 hours after opt-in.
        """
        if not isinstance(policy, ReplenishmentPolicy):
            raise ReplenishmentError("A reviewed policy is required.")
        with cls.locked(room, actor) as room:
            stock, now = cls.stock(room, policy), cls.now()
            if cls.read(room, cls.marker) is not None:
                state = cls.state(room, policy)
                if now < cls.timestamp(state["last"]):
                    raise ReplenishmentError("The source clock moved backwards.")
                return state
            if stock != policy.vector():
                raise ReplenishmentError(
                    "Only exact initial stock may opt in; sold stock cannot define caps."
                )
            state = {
                "schema": 1,
                "room": room.pk,
                "instance": str(uuid4()),
                "policy": policy.identity(),
                "initialized": now.isoformat(),
                "last": now.isoformat(),
                "sequence": 0,
                "request": None,
            }
            cls.write(room, cls.marker, state, create=True)
            return state

    @classmethod
    def refill(cls, room, policy, actor, request_id):
        """Top up once per rolling 24 hours, or replay the same durable receipt.

        Reuse the request UUID after uncertainty. Replays return the original
        receipt even after later purchases/refills, never perform another top-up.
        Full stock returns None without consuming a window or request identity.
        """
        from pokemon.services.item_shop import ShopPurchase

        if not isinstance(policy, ReplenishmentPolicy):
            raise ReplenishmentError("A reviewed policy is required.")
        try:
            request = str(UUID(str(request_id)))
        except (ValueError, TypeError, AttributeError) as error:
            raise ReplenishmentError("A unique request UUID is required.") from error
        with cls.locked(room, actor) as room:
            stock, state, now = cls.stock(room, policy), cls.state(room, policy), cls.now()
            last = cls.timestamp(state["last"])
            if now < last:
                raise ReplenishmentError("The source clock moved backwards.")
            prior = cls.read(room, request, category=cls.category)
            if prior is not None:
                cls.validate_receipt(prior, state, policy)
                if prior["actor"] != actor.pk or prior["request"] != request:
                    raise ReplenishmentError("That request belongs to a different operator.")
                return prior
            if now < last + cls.interval:
                raise ReplenishmentError(
                    "The source is not eligible until " + (last + cls.interval).isoformat()
                )
            after = policy.vector()
            delta = {
                name: after[name]["quantity"] - offer["quantity"] for name, offer in stock.items()
            }
            if not any(delta.values()):
                return None
            receipt = {
                "schema": 1,
                "room": room.pk,
                "instance": state["instance"],
                "policy": policy.identity(),
                "sequence": state["sequence"] + 1,
                "request": request,
                "actor": actor.pk,
                "previous_at": state["last"],
                "eligible_at": (last + cls.interval).isoformat(),
                "committed_at": now.isoformat(),
                "before": stock,
                "after": after,
                "delta": delta,
            }
            receipt["digest"] = cls.digest(receipt)
            ShopPurchase.write_stock(room, after)
            cls.write(room, request, receipt, category=cls.category, create=True)
            cls.write(
                room,
                cls.marker,
                {
                    **state,
                    "last": now.isoformat(),
                    "sequence": receipt["sequence"],
                    "request": request,
                },
            )
            return receipt
