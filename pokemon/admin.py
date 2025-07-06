from django.contrib import admin
from .models import (
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

admin.site.register(Pokemon)
admin.site.register(UserStorage)
admin.site.register(StorageBox)
admin.site.register(OwnedPokemon)
admin.site.register(ActiveMoveslot)
admin.site.register(BattleSlot)
admin.site.register(Move)
admin.site.register(Trainer)
admin.site.register(GymBadge)
