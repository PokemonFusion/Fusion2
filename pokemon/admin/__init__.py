from django.contrib import admin
from ..models import (
    Pokemon,
    UserStorage,
    StorageBox,
    OwnedPokemon,
    ActiveMoveslot,
    BattleSlot,
    Move,
    Trainer,
    GymBadge,
)

from .owned_pokemon import OwnedPokemonAdmin

admin.site.register(Pokemon)
admin.site.register(UserStorage)
admin.site.register(StorageBox)
admin.site.register(OwnedPokemon, OwnedPokemonAdmin)
admin.site.register(ActiveMoveslot)
admin.site.register(BattleSlot)
admin.site.register(Move)
admin.site.register(Trainer)
admin.site.register(GymBadge)
