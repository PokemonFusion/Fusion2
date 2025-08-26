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
