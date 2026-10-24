"""Durable consent, receipts and exclusive reservations for ownership writers."""

from uuid import uuid4

from django.db import models


class OwnershipTransfer(models.Model):
    """Bind immutable asset terms and both characters' approvals to one receipt."""

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    proposer = models.ForeignKey("objects.ObjectDB", on_delete=models.CASCADE,
                                 related_name="proposed_pokemon_transfers")
    recipient = models.ForeignKey("objects.ObjectDB", on_delete=models.CASCADE,
                                  related_name="received_pokemon_transfers")
    purpose = models.CharField(max_length=12, default="trade", choices=(("trade", "Trade"), ("market", "Marketplace")))
    terms = models.JSONField()
    approvals = models.JSONField(default=list)
    state = models.CharField(max_length=12, default="pending", db_index=True)
    expires_at = models.DateTimeField(db_index=True)
    result = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(purpose__in=("trade", "market")), name="transfer_known_purpose"),
            models.CheckConstraint(condition=~models.Q(proposer=models.F("recipient")),
                                   name="transfer_distinct_characters"),
            models.CheckConstraint(condition=models.Q(state__in=("pending", "completed", "cancelled", "expired")),
                                   name="transfer_known_state"),
            models.CheckConstraint(
                condition=(models.Q(state="completed", completed_at__isnull=False)
                           | (~models.Q(state="completed") & models.Q(completed_at__isnull=True))),
                name="transfer_completion_shape"),
        ]


class PokemonReservation(models.Model):
    """One exclusive system claim; ownership and canonical placement remain intact."""

    pokemon = models.OneToOneField("OwnedPokemon", on_delete=models.CASCADE,
                                  related_name="system_reservation")
    storage = models.ForeignKey("UserStorage", on_delete=models.CASCADE,
                                related_name="pokemon_reservations")
    kind = models.CharField(max_length=12)
    token = models.UUIDField(db_index=True)
    transfer = models.ForeignKey(OwnershipTransfer, null=True, blank=True,
                                  on_delete=models.PROTECT, related_name="reservations")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(kind__in=("trade", "market", "daycare", "breeding")),
                                   name="reservation_known_kind"),
            models.CheckConstraint(condition=(models.Q(kind="trade", transfer__isnull=False)
                                               | (~models.Q(kind="trade") & models.Q(transfer__isnull=True))),
                                   name="reservation_transfer_shape"),
        ]
