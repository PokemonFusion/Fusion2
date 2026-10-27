"""One historical completion receipt for each character's initial setup."""
from uuid import uuid4
from django.db import models


class OnboardingCompletion(models.Model):
    """Retain the original grant identity after later trading, release or deletion."""

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    character = models.OneToOneField("objects.ObjectDB", null=True, blank=True, on_delete=models.SET_NULL, related_name="onboarding_completion")
    origin_character_id = models.BigIntegerField(unique=True)
    pokemon = models.ForeignKey("OwnedPokemon", null=True, blank=True, on_delete=models.SET_NULL, related_name="onboarding_grants")
    pokemon_uuid = models.UUIDField(unique=True)
    kind = models.CharField(max_length=10, choices=(("human", "Human"), ("fusion", "Fusion")))
    choices = models.JSONField(default=dict)
    receipt = models.JSONField(default=dict)
    completed_at = models.DateTimeField(auto_now_add=True)
