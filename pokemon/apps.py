"""Django application configuration for the ``pokemon`` app."""

from __future__ import annotations

import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class PokemonConfig(AppConfig):
    """Ensure Evennia-dependent model modules register with Django."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "pokemon"
    verbose_name = "Pokémon"

    def ready(self) -> None:  # pragma: no cover - exercised by Django at runtime
        """Import model modules once Django's app registry is ready."""

        try:
            from .models import ensure_model_modules_loaded

            ensure_model_modules_loaded()
        except Exception:  # pragma: no cover - log but don't break startup
            logger.exception("Failed to load pokemon model modules during app ready")
