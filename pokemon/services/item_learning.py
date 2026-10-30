"""Durable earned-move choices after an atomic progression-item commit."""

from contextlib import contextmanager
import hashlib
import json
import re
from uuid import UUID, uuid4

from django.db import connection, transaction


class ItemLearningError(ValueError):
    """A stale or ineligible learning request changes no move, PP or queue."""


class ItemLearning:
    """Keep knowledge paid once; activate only a fresh explicit ordinary choice.

    Writers take character -> storage -> trainer -> owned row. Attributes use
    SQL-only writes, and notices/cache publication wait for the outer commit.
    A short delivery token binds the exact current moveset/slot/PP view. Listing
    again rotates tokens, so old replies cannot act on a newer presentation.
    """

    attribute = "pending_item_learning"

    def __init__(self, caller):
        """Derive the owning character from server context, never request input."""
        from pokemon.services.battle_rewards import BattleRewards

        self.caller = caller
        self.owner = BattleRewards.character(caller)

    def read(self):
        """Reject malformed/duplicate versioned state instead of discarding paid choices."""
        from evennia.utils.dbserialize import from_pickle

        rows = list(
            self.owner.db_attributes.filter(
                db_key=self.attribute, db_category=None, db_attrtype=None
            ).values_list("db_value", flat=True)
        )
        if not rows:
            return {"schema": 1, "entries": []}
        if len(rows) != 1:
            raise ItemLearningError("Duplicate saved learning records need staff review.")
        state = from_pickle(rows[0])
        if (
            type(state) is not dict
            or set(state) != {"schema", "entries"}
            or type(state["schema"]) is not int
            or state["schema"] != 1
            or type(state["entries"]) is not list
        ):
            raise ItemLearningError("Invalid saved learning records need staff review.")
        identities, tokens, bindings = set(), set(), set()
        for entry in state["entries"]:
            try:
                if (
                    type(entry) is not dict
                    or set(entry)
                    != {"id", "pokemon", "trainer", "move", "name", "level", "token", "fingerprint"}
                    or str(UUID(entry["id"])) != entry["id"]
                    or str(UUID(entry["pokemon"])) != entry["pokemon"]
                    or any(
                        type(entry[key]) is not int or entry[key] <= 0
                        for key in ("trainer", "move", "level")
                    )
                    or entry["level"] > 100
                    or not isinstance(entry["name"], str)
                    or not entry["name"]
                    or entry["id"] in identities
                    or (entry["pokemon"], entry["move"]) in bindings
                    or entry["token"] is not None
                    and (
                        not isinstance(entry["token"], str)
                        or not re.fullmatch(r"[0-9a-f]{12}", entry["token"])
                        or entry["token"] in tokens
                    )
                    or entry["fingerprint"] is not None
                    and (
                        not isinstance(entry["fingerprint"], str)
                        or not re.fullmatch(r"[0-9a-f]{64}", entry["fingerprint"])
                    )
                    or (entry["token"] is None) != (entry["fingerprint"] is None)
                ):
                    raise ValueError
            except (TypeError, ValueError, KeyError, AttributeError) as error:
                raise ItemLearningError(
                    "Invalid saved learning choice needs staff review."
                ) from error
            identities.add(entry["id"])
            bindings.add((entry["pokemon"], entry["move"]))
            if entry["token"]:
                tokens.add(entry["token"])
        return state

    def write(self, state):
        """Persist under the character lock without uncommitted Attribute publication."""
        from evennia.typeclasses.models import Attribute
        from evennia.utils.dbserialize import to_pickle

        rows = self.owner.db_attributes.filter(
            db_key=self.attribute, db_category=None, db_attrtype=None
        )
        count = rows.count()
        if count > 1:
            raise ItemLearningError("Duplicate saved learning records need staff review.")
        if count:
            rows.update(db_value=to_pickle(state))
        else:
            attribute = Attribute.objects.create(
                db_key=self.attribute, db_model="objectdb", db_value=to_pickle(state)
            )
            self.owner.db_attributes.add(attribute)

    def refresh(self):
        """Restore committed Attribute cache values even after a containing rollback."""
        from pokemon.services.item_shop import ShopPurchase

        if connection.in_atomic_block:
            self.owner.attributes.reset_cache()
            transaction.on_commit(
                lambda: ShopPurchase.refresh_attributes(self.owner, self.attribute), robust=True
            )
        else:
            ShopPurchase.refresh_attributes(self.owner, self.attribute)

    @contextmanager
    def locked(self):
        """Revalidate current owner/battle state before queue or move mutation."""
        from evennia.objects.models import ObjectDB
        from pokemon.models.storage import UserStorage
        from pokemon.models.trainer import Trainer
        from pokemon.services.ownership import assert_character_free

        try:
            with transaction.atomic():
                ObjectDB.objects.select_for_update().filter(pk=self.owner.pk).values("pk").get()
                assert_character_free(self.owner)
                storage = UserStorage.objects.select_for_update().get(user_id=self.owner.pk)
                trainer = Trainer.objects.select_for_update().get(user_id=self.owner.pk)
                yield storage, trainer
        except (ObjectDB.DoesNotExist, UserStorage.DoesNotExist, Trainer.DoesNotExist) as error:
            raise ItemLearningError("Your current character/storage is unavailable.") from error
        finally:
            self.refresh()

    def add_locked(self, pokemon, moves):
        """Append earned knowledge inside the paid field transaction, never activate it."""
        if not moves:
            return
        state = self.read()
        existing = {(entry["pokemon"], entry["move"]) for entry in state["entries"]}
        for move, level in moves:
            identity = str(pokemon.pk), move.pk
            if identity not in existing:
                state["entries"].append(
                    {
                        "id": str(uuid4()),
                        "pokemon": str(pokemon.pk),
                        "trainer": pokemon.trainer_id,
                        "move": move.pk,
                        "name": move.name,
                        "level": level,
                        "token": None,
                        "fingerprint": None,
                    }
                )
                existing.add(identity)
        self.write(state)
        self.refresh()

    def current(self, entry, storage, trainer):
        """Resolve a real current owned target, keeping linked native hosts deferred."""
        from pokemon.models.core import OwnedPokemon
        from pokemon.services.battle_rewards import BattleRewards
        from pokemon.services.ownership import fresh_owned
        from pokemon.services.placement import PlacementError, PlacementService
        from pokemon.services.necrozma_moves import pair_for_model

        if trainer.pk != entry["trainer"]:
            raise ItemLearningError("That learning choice no longer belongs to this trainer.")
        try:
            pokemon = fresh_owned(entry["pokemon"], lock=True)
            pokemon, placement = PlacementService(storage)._pokemon(
                pokemon, storage, operation="field"
            )
        except (OwnedPokemon.DoesNotExist, PlacementError) as error:
            raise ItemLearningError(
                "The learning target is no longer currently owned and available."
            ) from error
        if (
            pokemon.trainer_id != trainer.pk
            or pokemon.is_egg
            or placement is None
            or placement.location_type not in {"party", "fusion"}
            or placement.location_type == "fusion"
            and str(pokemon.pk)
            != str(BattleRewards.stored_attribute(self.owner, "fusion_id", default=None) or "")
        ):
            raise ItemLearningError(
                "Withdraw the owned learning target into your party/current Fusion first."
            )
        if (
            not pokemon.learned_moves.filter(pk=entry["move"]).exists()
            or pokemon.level < entry["level"]
        ):
            raise ItemLearningError("The earned move/level changed; reopen learning after review.")
        if pair_for_model(pokemon, "progression"):
            raise ItemLearningError("This host's active choices stay deferred until separation.")
        return pokemon, placement

    @staticmethod
    def view(pokemon, placement):
        """Bind actual active slots, saved-set rows and PP rather than a menu index."""
        from pokemon.models.moves import ActiveMoveslot, MovePPBoost, Moveset, MovesetSlot

        active = list(
            ActiveMoveslot.objects.select_for_update()
            .filter(pokemon=pokemon)
            .order_by("slot")
            .values("pk", "slot", "move_id", "move__name", "current_pp")
        )
        sets = list(
            Moveset.objects.select_for_update()
            .filter(pokemon=pokemon)
            .order_by("index")
            .values("pk", "index")
        )
        stored = (
            list(
                MovesetSlot.objects.select_for_update()
                .filter(moveset_id=pokemon.active_moveset_id)
                .order_by("slot")
                .values("pk", "slot", "move_id")
            )
            if pokemon.active_moveset_id
            else []
        )
        if (
            any(
                type(row["slot"]) is not int or row["slot"] not in range(1, 5)
                for row in active + stored
            )
            or len({row["slot"] for row in active}) != len(active)
            or len({row["move_id"] for row in active}) != len(active)
            or [(row["slot"], row["move_id"]) for row in active]
            != [(row["slot"], row["move_id"]) for row in stored]
            or pokemon.active_moveset_id
            and pokemon.active_moveset_id not in {row["pk"] for row in sets}
        ):
            raise ItemLearningError(
                "Saved/active move slots need review before this learning choice."
            )
        state = {
            "pokemon": str(pokemon.pk),
            "trainer": pokemon.trainer_id,
            "species": pokemon.species,
            "placement": {
                "pk": placement.pk,
                "type": placement.location_type,
                "slot": placement.slot,
            },
            "active_set": pokemon.active_moveset_id,
            "sets": sets,
            "stored": stored,
            "active": active,
            "boosts": list(
                MovePPBoost.objects.filter(pokemon=pokemon)
                .order_by("move_id")
                .values("move_id", "bonus_pp")
            ),
        }
        return (
            state,
            hashlib.sha256(json.dumps(state, sort_keys=True, default=str).encode()).hexdigest(),
        )

    def present(self):
        """Show resumable text choices after commit; listing rotates old delivery tokens."""
        with self.locked() as (storage, trainer):
            state, lines = self.read(), []
            tokens = {entry["token"] for entry in state["entries"] if entry["token"]}
            for entry in state["entries"]:
                try:
                    pokemon, placement = self.current(entry, storage, trainer)
                    view, fingerprint = self.view(pokemon, placement)
                except ItemLearningError as error:
                    entry["token"], entry["fingerprint"] = None, None
                    lines.append(f"{entry['name']} remains stored: {error}")
                    continue
                token = uuid4().hex[:12]
                while token in tokens:
                    token = uuid4().hex[:12]
                tokens.add(token)
                entry["token"], entry["fingerprint"] = token, fingerprint
                slots = {row["slot"]: row["move__name"] for row in view["active"]}
                choices = "; ".join(f"{slot}: {slots.get(slot, '(empty)')}" for slot in range(1, 5))
                lines.append(
                    f"{pokemon.name} ({pokemon.pk}) learned {entry['name']} (stored). {choices}. "
                    f"Use +learn pending {token}=<1-4 or store>."
                )
            if state["entries"]:
                self.write(state)
            text = "\n".join(lines) if lines else "There are no pending item-learning choices."
            transaction.on_commit(lambda: self.caller.msg(text), robust=True)
            return bool(state["entries"])

    def offer_if_available(self):
        """Busy/disconnected players keep durable choices without UI replacement."""
        if not self.read()["entries"]:
            return
        sessions = getattr(self.caller, "sessions", None)
        if getattr(self.caller.ndb, "_evmenu", None) or sessions is None or not sessions.all():
            self.caller.msg(
                "New moves are stored. Use +learn pending to choose active slots later."
            )
            return
        self.present()

    def choose(self, token, selection):
        """Claim a fresh choice once; change only its selected slot and preserve other PP."""
        from pokemon.models.core import OwnedPokemon
        from pokemon.models.moves import ActiveMoveslot, Move, MovePPBoost, Moveset, MovesetSlot
        from pokemon.services.ownership import fresh_owned
        from pokemon.services.pp_capacity import PPCapacity

        if not isinstance(token, str) or not re.fullmatch(r"[0-9a-f]{12}", token):
            raise ItemLearningError("Use a current token from +learn pending.")
        if selection != "store" and (type(selection) is not int or selection not in range(1, 5)):
            raise ItemLearningError("Choose a current active slot1-4, or store the learned move.")
        identifier = None
        try:
            with self.locked() as (storage, trainer):
                state = self.read()
                matches = [entry for entry in state["entries"] if entry["token"] == token]
                if len(matches) != 1:
                    raise ItemLearningError(
                        "That choice expired or was handled. Use +learn pending."
                    )
                entry = matches[0]
                pokemon, placement = self.current(entry, storage, trainer)
                identifier = pokemon.pk
                view, fingerprint = self.view(pokemon, placement)
                if fingerprint != entry["fingerprint"]:
                    raise ItemLearningError(
                        "The current move/PP state changed. Use +learn pending again."
                    )
                active = {row["slot"]: row for row in view["active"]}
                already_active = any(row["move_id"] == entry["move"] for row in active.values())
                if selection != "store" and not already_active:
                    move = Move.objects.get(pk=entry["move"])
                    policy = PPCapacity.for_move(move.name)
                    boost = (
                        MovePPBoost.objects.filter(pokemon=pokemon, move=move)
                        .values_list("bonus_pp", flat=True)
                        .first()
                        or 0
                    )
                    if (
                        policy.base <= 0
                        or type(boost) is not int
                        or not 0 <= boost <= policy.stages[-1]
                    ):
                        raise ItemLearningError("The learned move's PP capacity needs review.")
                    moveset = pokemon.active_moveset_id
                    if moveset is None:
                        if view["sets"]:
                            raise ItemLearningError(
                                "Choose an active saved set before activating this learned move."
                            )
                        moveset = Moveset.objects.create(pokemon=pokemon, index=0).pk
                        OwnedPokemon.objects.filter(pk=pokemon.pk).update(active_moveset_id=moveset)
                    if selection in active:
                        stored = next(row for row in view["stored"] if row["slot"] == selection)
                        MovesetSlot.objects.filter(pk=stored["pk"]).update(move=move)
                        ActiveMoveslot.objects.filter(pk=active[selection]["pk"]).update(
                            move=move, current_pp=policy.base + boost
                        )
                    else:
                        MovesetSlot.objects.create(moveset_id=moveset, slot=selection, move=move)
                        ActiveMoveslot.objects.create(
                            pokemon=pokemon,
                            slot=selection,
                            move=move,
                            current_pp=policy.base + boost,
                        )
                state["entries"] = [row for row in state["entries"] if row["id"] != entry["id"]]
                self.write(state)
                message = (
                    f"{pokemon.name}'s {entry['name']} remains stored. No active move changed."
                    if selection == "store" or already_active
                    else f"{pokemon.name} activated {entry['name']} in slot{selection}."
                )
                transaction.on_commit(lambda: self.caller.msg(message), robust=True)
        finally:
            if identifier is not None:
                cached = OwnedPokemon.get_cached_instance(identifier)
                if cached is not None:
                    OwnedPokemon.flush_cached_instance(cached)
                if connection.in_atomic_block:
                    transaction.on_commit(lambda: fresh_owned(identifier), robust=True)
                else:
                    fresh_owned(identifier)
