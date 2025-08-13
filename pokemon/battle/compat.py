"""Compatibility helpers for optional Evennia dependencies."""

from __future__ import annotations

# Logger fallbacks ---------------------------------------------------------
try:  # pragma: no cover - Evennia logger not available in tests
    from evennia.utils.logger import log_info, log_warn, log_err
except Exception:  # pragma: no cover - fallback to standard logging
    import logging

    _log = logging.getLogger(__name__)

    def log_info(*args, **kwargs):  # type: ignore[misc]
        _log.info(*args, **kwargs)

    def log_warn(*args, **kwargs):  # type: ignore[misc]
        _log.warning(*args, **kwargs)

    def log_err(*args, **kwargs):  # type: ignore[misc]
        _log.error(*args, **kwargs)

# Evennia search -----------------------------------------------------------
try:  # pragma: no cover - search requires Evennia in runtime
    from evennia import search_object, DefaultScript as ScriptBase  # type: ignore
    if ScriptBase is None:  # Some stubs define DefaultScript as None
        raise Exception
except Exception:  # pragma: no cover - used in tests without Evennia
    def search_object(dbref):  # type: ignore[no-redef]
        return []

    class ScriptBase:  # type: ignore[no-redef]
        """Minimal stand-in for Evennia's ``DefaultScript``."""

        def stop(self):  # pragma: no cover - trivial stub
            pass

# Battle engine helpers ----------------------------------------------------
try:  # pragma: no cover - engine may be stubbed
    from .engine import _normalize_key as _battle_norm_key
except Exception:  # pragma: no cover - fallback normalizer
    def _battle_norm_key(name: str) -> str:  # type: ignore[no-redef]
        return name.replace(" ", "").replace("-", "").replace("'", "").lower()

# Optional modules ---------------------------------------------------------
try:  # pragma: no cover - logic may be absent during some tests
    from pokemon.battle.logic import BattleLogic
except Exception:  # pragma: no cover - dynamic import fallback
    import importlib.util as _util, pathlib as _pathlib, sys as _sys

    _logic_path = _pathlib.Path(__file__).with_name("logic.py")
    _spec = _util.spec_from_file_location("pokemon.battle.logic", _logic_path)
    _mod = _util.module_from_spec(_spec)
    _sys.modules[_spec.name] = _mod
    _spec.loader.exec_module(_mod)  # type: ignore[call-arg]
    BattleLogic = _mod.BattleLogic  # type: ignore[attr-defined]

try:  # pragma: no cover - factory may be absent
    from pokemon.battle.pokemon_factory import (
        create_battle_pokemon,
        generate_trainer_pokemon,
        generate_wild_pokemon,
        _calc_stats_from_model,
    )
except Exception:  # pragma: no cover - dynamic import fallback
    import importlib.util as _util, pathlib as _pathlib, sys as _sys

    _factory_path = _pathlib.Path(__file__).with_name("pokemon_factory.py")
    _spec_f = _util.spec_from_file_location("pokemon.battle.pokemon_factory", _factory_path)
    _mod_f = _util.module_from_spec(_spec_f)
    _sys.modules[_spec_f.name] = _mod_f
    _spec_f.loader.exec_module(_mod_f)  # type: ignore[call-arg]
    create_battle_pokemon = _mod_f.create_battle_pokemon  # type: ignore[attr-defined]
    generate_trainer_pokemon = _mod_f.generate_trainer_pokemon  # type: ignore[attr-defined]
    generate_wild_pokemon = _mod_f.generate_wild_pokemon  # type: ignore[attr-defined]
    _calc_stats_from_model = _mod_f._calc_stats_from_model  # type: ignore[attr-defined]

try:  # pragma: no cover - optional room class
    from typeclasses.rooms import FusionRoom
except Exception:  # pragma: no cover - room type not required for tests
    FusionRoom = None  # type: ignore[assignment]

__all__ = [
    "log_info",
    "log_warn",
    "log_err",
    "search_object",
    "ScriptBase",
    "_battle_norm_key",
    "BattleLogic",
    "create_battle_pokemon",
    "generate_trainer_pokemon",
    "generate_wild_pokemon",
    "_calc_stats_from_model",
    "FusionRoom",
]
