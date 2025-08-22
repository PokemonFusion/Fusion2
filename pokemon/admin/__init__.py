"""Admin registrations for the Pokémon app.

This module connects Django models to the admin interface.  The game's test
suite often runs in a lightweight environment where the ORM isn't fully
configured.  When that happens the imported model references become ``None``.
Attempting to register ``None`` with ``admin.site`` raises ``TypeError``.

To keep these environments usable we skip registration for any missing models.
"""

from django.contrib import admin

from ..models import (
    ActiveMoveslot,
    BattleSlot,
    GymBadge,
    Move,
    OwnedPokemon,
    Pokemon,
    StorageBox,
    Trainer,
    UserStorage,
)
from .owned_pokemon import OwnedPokemonAdmin


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


_register(Pokemon)
_register(UserStorage)
_register(StorageBox)
_register(OwnedPokemon, OwnedPokemonAdmin)
_register(ActiveMoveslot)
_register(BattleSlot)
_register(Move)
_register(Trainer)
_register(GymBadge)
