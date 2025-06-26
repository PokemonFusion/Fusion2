from django.contrib import admin
from .models import (
    Pokemon,
    UserStorage,
    StorageBox,
    OwnedPokemon,
    ActiveMoveset,
    Trainer,
    GymBadge,
)

admin.site.register(Pokemon)
admin.site.register(UserStorage)
admin.site.register(StorageBox)
admin.site.register(OwnedPokemon)
admin.site.register(ActiveMoveset)
admin.site.register(Trainer)
admin.site.register(GymBadge)
