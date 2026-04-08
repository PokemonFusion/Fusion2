"""Adapters for optional battle and dex dependencies.

This module centralizes import fallback logic used by lightweight utility
helpers so callers can depend on stable adapter functions instead of repeating
``try``/``except`` import blocks.
"""

from __future__ import annotations

import importlib.util
import logging
import sys
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger(__name__)


def normalize_key(value: str) -> str:
    """Normalize user-facing names into a consistent lookup key.

    The adapter prefers the battle engine normalizer when available. If the
    battle engine is unavailable (common in isolated unit tests), this falls
    back to a lightweight, behavior-compatible implementation.
    """

    try:
        from pokemon.battle.engine import _normalize_key as engine_normalize_key

        logger.debug("normalize_key: using pokemon.battle.engine._normalize_key")
        return engine_normalize_key(value)
    except ImportError:  # pragma: no cover - optional dependency boundary
        logger.debug("normalize_key: using local fallback normalizer")
        return value.replace(" ", "").replace("-", "").replace("'", "").lower()


def get_battle_factories() -> dict[str, Callable[..., Any] | None]:
    """Return optional battle factory callables from the best available source.

    Returns
    -------
    dict
        Dictionary containing:
        - ``calc_stats_from_model``: callable or ``None``.
        - ``create_battle_pokemon``: callable or ``None``.
    """

    bi = sys.modules.get("pokemon.battle.battleinstance")
    if bi is not None:
        logger.debug("get_battle_factories: using pokemon.battle.battleinstance from sys.modules")
        return {
            "calc_stats_from_model": getattr(bi, "_calc_stats_from_model", None),
            "create_battle_pokemon": getattr(bi, "create_battle_pokemon", None),
        }

    try:  # pragma: no cover - exercised with full package available
        from pokemon.battle import battleinstance as bi

        logger.debug("get_battle_factories: imported pokemon.battle.battleinstance")
        return {
            "calc_stats_from_model": getattr(bi, "_calc_stats_from_model", None),
            "create_battle_pokemon": getattr(bi, "create_battle_pokemon", None),
        }
    except ImportError:  # pragma: no cover - optional dependency boundary
        logger.debug("get_battle_factories: battleinstance unavailable, returning empty factories")
        return {
            "calc_stats_from_model": None,
            "create_battle_pokemon": None,
        }


def get_dex_data() -> dict[str, Any]:
    """Return dex objects using resilient import and file-loading fallbacks.

    Returns
    -------
    dict
        Dictionary containing:
        - ``dex_module``: imported dex module or ``None``.
        - ``pokedex``: Pokédex mapping (possibly empty).
        - ``movedex``: Movedex mapping (possibly empty).
    """

    try:
        from pokemon import dex as dex_mod

        logger.debug("get_dex_data: using imported pokemon.dex module")
        return {
            "dex_module": dex_mod,
            "pokedex": getattr(dex_mod, "POKEDEX", {}) or {},
            "movedex": getattr(dex_mod, "MOVEDEX", {}) or {},
        }
    except ImportError:  # pragma: no cover - optional dependency boundary
        logger.debug("get_dex_data: pokemon.dex import failed, checking module cache")

    cached_dex = sys.modules.get("pokemon.dex")
    if cached_dex is not None:
        logger.debug("get_dex_data: using cached pokemon.dex from sys.modules")
        return {
            "dex_module": cached_dex,
            "pokedex": getattr(cached_dex, "POKEDEX", {}) or {},
            "movedex": getattr(cached_dex, "MOVEDEX", {}) or {},
        }

    try:  # pragma: no cover - fallback path
        dex_path = Path(__file__).resolve().parents[1] / "dex" / "__init__.py"
        spec = importlib.util.spec_from_file_location("pokemon.dex", dex_path)
        if spec and spec.loader:
            real_dex = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = real_dex
            spec.loader.exec_module(real_dex)
            logger.debug("get_dex_data: loaded pokemon.dex via importlib from %s", dex_path)
            return {
                "dex_module": real_dex,
                "pokedex": getattr(real_dex, "POKEDEX", {}) or {},
                "movedex": getattr(real_dex, "MOVEDEX", {}) or {},
            }
    except (ImportError, AttributeError, FileNotFoundError):
        logger.debug("get_dex_data: importlib fallback failed", exc_info=True)

    logger.debug("get_dex_data: all dex fallbacks exhausted; returning empty dex data")
    return {"dex_module": None, "pokedex": {}, "movedex": {}}
