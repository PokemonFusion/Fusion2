"""Admin registrations for the Pokémon app.

This module connects Django models to the admin interface.  The game's test
suite often runs in a lightweight environment where the ORM isn't fully
configured.  When that happens the imported model references become ``None``.
Attempting to register ``None`` with ``admin.site`` raises ``TypeError``.

To keep these environments usable we skip registration for any missing models.
"""

from django.contrib import admin

try:  # pragma: no cover - defensive import
    from ..models.core import BattleSlot, OwnedPokemon, Pokemon
    from ..models.moves import ActiveMoveslot, Move
    from ..models.storage import StorageBox, UserStorage
    from ..models.trainer import GymBadge, GymLeaderProfile, NPCPokemonTemplate, NPCTrainer, Trainer
except Exception:  # Any import failure leaves models unset for safe registration
    Pokemon = OwnedPokemon = BattleSlot = None
    Move = ActiveMoveslot = None
    Trainer = GymBadge = GymLeaderProfile = NPCTrainer = NPCPokemonTemplate = None
    StorageBox = UserStorage = None
try:  # pragma: no cover - defensive import
    from .owned_pokemon import OwnedPokemonAdmin
except Exception:  # Missing model leaves admin class unset
    OwnedPokemonAdmin = None


def _register(model, admin_class=None):
    """Safely register a model with Django's admin site.

    Args:
        model: The Django model class to register.  If ``None`` the registration
            is skipped.
        admin_class: Optional ``ModelAdmin`` subclass for customizing the admin
            interface.
    """

    if model is None:
        return
    if admin_class:
        admin.site.register(model, admin_class)
    else:
        admin.site.register(model)


class GymBadgeAdmin(admin.ModelAdmin):
    list_display = ("name", "region")
    search_fields = ("name", "region", "description")
    list_filter = ("region",)


class GymLeaderProfileAdmin(admin.ModelAdmin):
    list_display = (
        "npc_trainer",
        "league_key",
        "gym_key",
        "badge",
        "badge_key",
        "required_badge_count",
        "is_enabled",
        "sort_order",
    )
    search_fields = (
        "npc_trainer__name",
        "league_key",
        "gym_key",
        "badge__name",
        "badge_key",
    )
    list_filter = ("is_enabled", "league_key")
    autocomplete_fields = ("npc_trainer", "badge")
    ordering = ("sort_order", "league_key", "gym_key")


class NPCPokemonTemplateInline(admin.TabularInline):
    model = NPCPokemonTemplate
    extra = 0
    fields = (
        "sort_order",
        "template_key",
        "species",
        "level",
        "ability",
        "nature",
        "gender",
        "held_item",
        "move_names",
    )
    ordering = ("sort_order", "id")


class NPCTrainerAdmin(admin.ModelAdmin):
    list_display = ("name", "template_count", "has_gym_profile")
    search_fields = ("name", "description")
    inlines = [NPCPokemonTemplateInline] if NPCPokemonTemplate is not None else []
    ordering = ("name",)

    def template_count(self, obj):
        related = getattr(obj, "pokemon_templates", None)
        if related is None:
            return 0
        count = getattr(related, "count", None)
        if callable(count):
            return count()
        return len(list(related.all())) if hasattr(related, "all") else 0

    def has_gym_profile(self, obj):
        return hasattr(obj, "gym_leader_profile")

    has_gym_profile.boolean = True


class NPCPokemonTemplateAdmin(admin.ModelAdmin):
    list_display = ("npc_trainer", "sort_order", "template_key", "species", "level")
    search_fields = ("npc_trainer__name", "template_key", "species")
    list_filter = ("species", "level")
    autocomplete_fields = ("npc_trainer",)
    ordering = ("npc_trainer__name", "sort_order", "id")


_register(Pokemon)
_register(UserStorage)
_register(StorageBox)
_register(OwnedPokemon, OwnedPokemonAdmin)
_register(ActiveMoveslot)
_register(BattleSlot)
_register(Move)
_register(Trainer)
_register(GymBadge, GymBadgeAdmin)
_register(NPCTrainer, NPCTrainerAdmin)
_register(NPCPokemonTemplate, NPCPokemonTemplateAdmin)
_register(GymLeaderProfile, GymLeaderProfileAdmin)
