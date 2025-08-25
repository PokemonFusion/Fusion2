"""Validation helpers for Pokémon stats."""

from django.core.exceptions import ValidationError

__all__ = ["validate_ivs", "validate_evs"]

# Avoid importing models.stats at module import time (can cause circular/early
# import during app loading). These limits are canonical and already duplicated
# in ``models.stats``; keep them here to prevent registry issues.
EV_LIMIT = 510
STAT_EV_LIMIT = 252


def validate_ivs(value):
    """Validate that IV list has six integers between 0 and 31.

    Args:
        value: Sequence of individual values.

    Raises:
        ValidationError: If ``value`` is not a list of six integers in range.
    """
    if not isinstance(value, (list, tuple)) or len(value) != 6:
        raise ValidationError("IVs must contain six integers.")
    for v in value:
        if not isinstance(v, int) or not 0 <= v <= 31:
            raise ValidationError("IV values must be between 0 and 31.")


def validate_evs(value):
    """Validate that EV list has six integers within allowed limits.

    Args:
        value: Sequence of effort values.

    Raises:
        ValidationError: If ``value`` is not a list of six integers within
        individual and total EV constraints.
    """
    if not isinstance(value, (list, tuple)) or len(value) != 6:
        raise ValidationError("EVs must contain six integers.")

    for v in value:
        if not isinstance(v, int) or not 0 <= v <= STAT_EV_LIMIT:
            raise ValidationError(
                f"EV values must be between 0 and {STAT_EV_LIMIT}."
            )
    if sum(value) > EV_LIMIT:
        raise ValidationError(f"Total EVs cannot exceed {EV_LIMIT}.")
