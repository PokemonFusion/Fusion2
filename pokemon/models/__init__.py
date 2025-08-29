"""Lightweight package init for `pokemon.models`.

Do **not** eagerly import Evennia/Django-dependent modules here; CI unit tests may
import :mod:`pokemon.models.stats` without the Evennia runtime. Keep this module
cheap and free of side effects.
"""

from typing import TYPE_CHECKING

# Safe, pure-Python utilities can be imported here in the future. Keep
# Django/Evennia-dependent imports inside their respective modules.

if TYPE_CHECKING:  # pragma: no cover - only for type checkers
    from . import stats  # noqa: F401

# Import models for Django auto-discovery.  The try/except keeps this module
# importable in contexts where Django isn't configured (like during unit tests).
try:  # pragma: no cover - best effort for Django
    from .fusion import PokemonFusion  # noqa: F401
except Exception:  # pragma: no cover - Django not initialized
    PokemonFusion = None  # type: ignore
