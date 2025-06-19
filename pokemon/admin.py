from django.contrib import admin
from .models import (
    Pokemon,
    UserStorage,
    StorageBox,
    OwnedPokemon,
    ActiveMoveset,
)

admin.site.register(Pokemon)
admin.site.register(UserStorage)
admin.site.register(StorageBox)
admin.site.register(OwnedPokemon)
admin.site.register(ActiveMoveset)
