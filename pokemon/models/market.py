"""Fixed-price Pokemon listings with durable payment/ownership receipts."""

from uuid import uuid4

from django.db import models


class MarketListing(models.Model):
    """Publish one reserved existing asset and retain its historical sale result."""

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    seller = models.ForeignKey("objects.ObjectDB", null=True, on_delete=models.SET_NULL, related_name="pokemon_sales")
    seller_character_id = models.PositiveBigIntegerField(db_index=True)
    seller_name = models.CharField(max_length=255)
    pokemon = models.ForeignKey("OwnedPokemon", null=True, on_delete=models.SET_NULL, related_name="market_listings")
    owned_id = models.UUIDField()
    request_selector = models.CharField(max_length=100)
    snapshot = models.JSONField()
    price = models.PositiveIntegerField()
    state = models.CharField(max_length=10, default="active", db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(db_index=True)
    closed_at = models.DateTimeField(null=True)
    buyer = models.ForeignKey("objects.ObjectDB", null=True, on_delete=models.SET_NULL, related_name="pokemon_purchases")
    buyer_character_id = models.PositiveBigIntegerField(null=True)
    purchase_id = models.UUIDField(null=True, unique=True)
    receipt = models.JSONField(default=dict)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["pokemon"], condition=models.Q(state="active"), name="market_one_active_asset"),
            models.CheckConstraint(condition=models.Q(price__gte=1, price__lte=1_000_000), name="market_price_range"),
            models.CheckConstraint(condition=models.Q(state__in=("active", "sold", "cancelled", "expired")), name="market_known_state"),
            models.CheckConstraint(condition=(models.Q(state="active", seller__isnull=False, pokemon__isnull=False, closed_at__isnull=True)
                | (~models.Q(state="active") & models.Q(closed_at__isnull=False))), name="market_active_shape"),
            models.CheckConstraint(condition=(models.Q(state="sold", buyer_character_id__isnull=False, purchase_id__isnull=False)
                | (~models.Q(state="sold") & models.Q(buyer_character_id__isnull=True, purchase_id__isnull=True))), name="market_purchase_shape"),
        ]
