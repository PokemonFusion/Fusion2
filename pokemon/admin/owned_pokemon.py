from django.contrib import admin

from ..models import OwnedPokemon


class OwnedPokemonAdmin(admin.ModelAdmin):
    list_display = ("nickname", "species", "trainer", "created_at")


__all__ = ["OwnedPokemonAdmin", "OwnedPokemon"]
