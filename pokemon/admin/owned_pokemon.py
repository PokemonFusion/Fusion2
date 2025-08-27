"""Admin configuration for the OwnedPokemon model.

This module registers :class:`~pokemon.models.core.OwnedPokemon` with
``django.contrib.admin``.  Importing the model can fail in lightweight test
environments where Django isn't fully initialized, so the import is wrapped in
``try``/``except`` and falls back to ``None`` when unavailable.
"""

from django.contrib import admin

try:  # pragma: no cover - runtime dependency
        from ..models.core import OwnedPokemon
except Exception:  # pragma: no cover - model not ready
        OwnedPokemon = None


class OwnedPokemonAdmin(admin.ModelAdmin):
        """Basic admin customization for :class:`OwnedPokemon`."""

        list_display = ("nickname", "species", "trainer", "created_at")


__all__ = ["OwnedPokemonAdmin", "OwnedPokemon"]

