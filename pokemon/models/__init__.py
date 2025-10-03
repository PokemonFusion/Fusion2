"""Model package initialisation helpers.

This package previously avoided importing any Django models to keep pure-Python
unit tests light-weight.  That approach prevented Django from discovering the
app's models during migrations which, in turn, caused relational fields
referencing :class:`~pokemon.models.trainer.Trainer` and
:class:`~pokemon.models.trainer.NPCTrainer` to fail validation.  We now lazily
import the concrete model modules when Django is configured so that migrations
and runtime usage work as expected while still allowing pure-Python imports to
succeed in isolation.
"""

from __future__ import annotations

import importlib
import logging
from typing import TYPE_CHECKING

logger = logging.getLogger(__name__)


def ensure_model_modules_loaded(*, require_ready: bool = False) -> bool:
    """Import Django model modules when the ORM is available.

    Django populates an application's models by importing ``pokemon.models``.
    When this package refused to import its model submodules, the ORM could not
    register classes such as :class:`Trainer`.  The guard below makes the import
    conditional on Django being installed *and* configured so that simple
    utility imports used in non-Django contexts continue to work.
    
    Parameters
    ----------
    require_ready:
        When ``True`` the function attempts the import even if Django's app
        registry is still populating.  The default ``False`` skips the work
        until Django signals that all apps are ready, which avoids spurious
        ``AppRegistryNotReady`` errors during ``django.setup``.
    """

    try:  # Defensive: allow imports when Django is unavailable in lightweight tests.
        from django.apps import apps
        from django.conf import settings
    except Exception:  # pragma: no cover - Django not installed or misconfigured.
        return False

    if not settings.configured:  # pragma: no cover - happens in some test harnesses.
        return False

    if not (require_ready or apps.apps_ready):  # pragma: no cover - wait until Django is ready.
        return False

    for module_name in ("core", "trainer", "moves", "storage"):
        full_name = f"{__name__}.{module_name}"
        try:
            importlib.import_module(full_name)
        except ImportError:  # pragma: no cover - module legitimately missing.
            logger.debug("Model module %s could not be imported", full_name)
        except Exception:  # pragma: no cover - log unexpected issues for debugging.
            logger.exception("Unexpected error importing model module %s", full_name)
            raise

    return True

# Import models immediately only when Django is already initialised.  The
# Evennia launcher imports this module during ``django.setup`` before the app
# registry is fully populated; delaying the import avoids ``AppRegistryNotReady``
# while still letting third-party scripts call ``ensure_model_modules_loaded``
# manually when needed.
ensure_model_modules_loaded()


# Safe, pure-Python utilities can be imported here in the future. Keep
# Django/Evennia-dependent imports inside their respective modules.

if TYPE_CHECKING:  # pragma: no cover - only for type checkers
    from . import stats  # noqa: F401
