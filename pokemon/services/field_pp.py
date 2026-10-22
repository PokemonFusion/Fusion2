"""Fresh, atomic PP Up/PP Max prompts through the field item boundary."""

from uuid import uuid4

from django.db import transaction

from pokemon.names import normalize_name
from pokemon.services.field_items import FieldMedicineError
from pokemon.services.field_progression import FieldProgressionUse
from pokemon.services.pp_capacity import PPCapacity


class InvalidPPSelection(FieldMedicineError):
    """An invalid choice can retry the unchanged prompt without any writes."""


class FieldPPCapacityUse(FieldProgressionUse):
    """Bind a prompt to stable owned/placement/move identities, never a model."""

    selected_move_items = {"ppup", "ppmax"}

    @classmethod
    def supports(cls, item):
        """Limit this route to the two existing PP-capacity items."""
        return normalize_name(item) in cls.selected_move_items

    def confirm(self, pending, selection):
        """Carry an opaque prompt identity into the locked field transaction."""
        if not isinstance(pending, dict) or not {"token", "pokemon_id", "item", "state"} <= pending.keys():
            self.caller.ndb.pending_pp_item = None
            raise FieldMedicineError("That PP prompt has expired. Use the item again.")
        self.pending = pending
        try:
            return self.use(pending["item"], pending["pokemon_id"], move=selection)
        except InvalidPPSelection:
            raise
        except Exception:
            # A target/inventory/persistence failure expires the prompt. There
            # is no paid effect to replay; the player can start a new prompt.
            if getattr(self.caller.ndb, "pending_pp_item", None) == pending:
                self.caller.ndb.pending_pp_item = None
            raise

    def _targets(self, storage, query, item):
        """Check replay under the same storage lock as item and placement writes."""
        pending = getattr(self, "pending", None)
        if pending is not None and getattr(self.caller.ndb, "pending_pp_item", None) != pending:
            raise FieldMedicineError("That PP prompt has expired. Use the item again.")
        return super()._targets(storage, query, item)

    @staticmethod
    def _state(pokemon):
        """Read fresh placement and active move/boost identities for the prompt."""
        from pokemon.models.moves import ActiveMoveslot, MovePPBoost
        from pokemon.models.storage import PokemonPlacement

        return {
            "placement": PokemonPlacement.objects.select_for_update().filter(pokemon_id=pokemon.pk).values(
                "pk", "storage_id", "location_type", "slot").get(),
            "moves": list(ActiveMoveslot.objects.select_for_update().filter(pokemon_id=pokemon.pk).order_by("slot").values(
                "pk", "slot", "move_id", "move__name")),
            "boosts": list(MovePPBoost.objects.select_for_update().filter(pokemon_id=pokemon.pk).order_by("move_id").values(
                "move_id", "bonus_pp")),
        }

    def _apply(self, item, pokemon, trainer, *, move=None):
        """Prompt without a debit, or commit exactly one confirmed paid boost."""
        state = self._state(pokemon)
        pending = getattr(self, "pending", None)
        if pending is None:
            if move is not None:
                raise FieldMedicineError("Choose a Pokemon first, then select a move from the PP prompt.")
            if not state["moves"]:
                raise FieldMedicineError("That Pokemon knows no active moves.")
            pending = {"token": uuid4().hex, "pokemon_id": str(pokemon.pk),
                       "item": normalize_name(item), "state": state}
            lines = ["Choose a move to increase PP:"]
            current = dict(pokemon.activemoveslot_set.values_list("slot", "current_pp"))
            for slot in state["moves"]:
                lines.append(f"{slot['slot']}. {slot['move__name'].title()} "
                             f"({current[slot['slot']]}/{pokemon.get_max_pp(slot['move__name'])})")
            lines.append("Use +use <move name or number> to select, or +use cancel.")

            def show_prompt():
                """A rolled-back outer operation cannot leave a usable prompt."""
                self.caller.ndb.pending_pp_item = pending
                self.caller.msg("\n".join(lines))

            transaction.on_commit(show_prompt, robust=True)
            return None
        if state != pending["state"]:
            self.caller.ndb.pending_pp_item = None
            raise FieldMedicineError("That PP prompt is stale. Use the item again.")
        selection = str(move or "").strip()
        matches = [slot for slot in state["moves"] if (
            slot["slot"] == int(selection) if selection.isdigit()
            else normalize_name(slot["move__name"]) == normalize_name(selection))]
        if len(matches) != 1:
            raise InvalidPPSelection("Invalid or ambiguous move selection; use an exact displayed slot or move name.")
        slot = matches[0]
        # Invalidate before releasing the storage lock. Even two confirmations
        # with two copies cannot replay this prompt. Errors require a new prompt.
        self.caller.ndb.pending_pp_item = None
        bonus = next((row["bonus_pp"] for row in state["boosts"] if row["move_id"] == slot["move_id"]), 0)
        policy = PPCapacity.for_move(slot["move__name"])
        maximize = normalize_name(item) == "ppmax"
        if policy.increased_bonus(bonus, maximize=maximize) is None:
            if policy.blocked or policy.base < 5:
                message = "That move's PP cannot be raised."
            elif bonus == policy.stages[-1]:
                message = "That move already has maximum PP."
            elif 0 <= bonus < policy.stages[-1]:
                message = "That move has a nonstandard saved PP bonus. Use PP Max to reach maximum PP or contact staff."
            else:
                message = "Invalid saved PP bonus; contact staff."
            raise FieldMedicineError(message + " No item was consumed.")
        if not trainer.remove_item(item):
            raise FieldMedicineError("The PP item could not be consumed. Nothing was changed.")
        apply = pokemon.apply_pp_max if maximize else pokemon.apply_pp_up
        applied = apply(slot["move__name"])
        if not applied:
            raise FieldMedicineError("The move is no longer eligible. Nothing was changed.")
        self.result_name, self.result_move = pokemon.name, slot["move__name"]
        return True

    def success_message(self, item, target):
        """Report only the committed target/move, without resolving it again."""
        return f"{self.result_name}'s {self.result_move} PP was increased."
