"""Native Necrozma pairs, persistent source PP and character-bound operations.

These records do not participate in the separate trainer/Pokémon Fusion system.
Only live pairs protect their two owned sources; historical receipts retain UUIDs.
"""

from uuid import uuid4

from django.db import models


class NecrozmaResource(models.Model):
    """A host's once-introduced form move, retained across separation cycles."""

    host = models.ForeignKey("OwnedPokemon", on_delete=models.CASCADE, related_name="necrozma_resources")
    source = models.CharField(max_length=50)
    current_pp = models.PositiveSmallIntegerField()
    policy_version = models.PositiveSmallIntegerField(default=1)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("host", "source"), name="necrozma_host_source_unique"),
            models.CheckConstraint(condition=models.Q(source__in=("Sunsteel Strike", "Moongeist Beam")),
                                   name="necrozma_resource_source"),
            models.CheckConstraint(condition=models.Q(current_pp__lte=8, policy_version=1),
                                   name="necrozma_resource_shape"),
        ]


class NecrozmaCombination(models.Model):
    """One active lifecycle with two retained owned identities and one bound slot."""

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    storage = models.ForeignKey("UserStorage", on_delete=models.PROTECT, related_name="necrozma_pairs")
    host = models.OneToOneField("OwnedPokemon", on_delete=models.PROTECT, related_name="necrozma_host_pair")
    companion = models.OneToOneField("OwnedPokemon", on_delete=models.PROTECT, related_name="necrozma_companion_pair")
    base_species = models.CharField(max_length=50, default="Necrozma")
    target_species = models.CharField(max_length=50)
    policy_version = models.PositiveSmallIntegerField(default=1)
    resource = models.OneToOneField(NecrozmaResource, on_delete=models.PROTECT, related_name="active_pair")
    moveset = models.ForeignKey("Moveset", on_delete=models.PROTECT)
    move_slot = models.PositiveSmallIntegerField()
    displaced_move = models.ForeignKey("Move", null=True, blank=True, on_delete=models.PROTECT)
    displaced_pp = models.PositiveSmallIntegerField(null=True, blank=True)
    return_type = models.CharField(max_length=10)
    return_slot = models.PositiveSmallIntegerField(null=True, blank=True)
    # A deleted box is a lost hint, never a reason to delete a retained source.
    return_box = models.ForeignKey("StorageBox", null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=~models.Q(host=models.F("companion")), name="necrozma_distinct_sources"),
            models.CheckConstraint(condition=models.Q(base_species="Necrozma", policy_version=1,
                target_species__in=("Necrozma-Dusk-Mane", "Necrozma-Dawn-Wings"),
                move_slot__gte=1, move_slot__lte=4), name="necrozma_pair_shape"),
            models.CheckConstraint(condition=(models.Q(displaced_move__isnull=True, displaced_pp__isnull=True)
                | models.Q(displaced_move__isnull=False, displaced_pp__isnull=False)), name="necrozma_displaced_shape"),
            models.CheckConstraint(condition=(models.Q(return_type="party", return_slot__gte=1,
                return_slot__lte=6, return_slot__isnull=False, return_box__isnull=True)
                | models.Q(return_type="box", return_slot__isnull=True)), name="necrozma_return_shape"),
        ]


class NecrozmaOperation(models.Model):
    """Expiring exact-terms request and durable outcome without source foreign keys."""

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    storage = models.ForeignKey("UserStorage", on_delete=models.CASCADE, related_name="necrozma_operations")
    action = models.CharField(max_length=10)
    terms = models.JSONField()
    state = models.CharField(max_length=10, default="pending")
    expires_at = models.DateTimeField()
    result = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(action__in=("combine", "separate")), name="necrozma_operation_action"),
            models.CheckConstraint(condition=models.Q(state__in=("pending", "completed", "cancelled", "expired")),
                                   name="necrozma_operation_state"),
            models.CheckConstraint(condition=(models.Q(state="completed", completed_at__isnull=False)
                | (~models.Q(state="completed") & models.Q(completed_at__isnull=True))), name="necrozma_completion_shape"),
        ]
