from __future__ import annotations

"""Battle status package exports."""

from .status_core import (
	STATUS_BURN,
	STATUS_FREEZE,
	STATUS_PARALYSIS,
	STATUS_POISON,
	STATUS_SLEEP,
	STATUS_TOXIC,
	StatusCondition,
	can_apply_status,
	has_ability,
	has_type,
	iter_allies,
)
from .burn import Burn
from .poison import BadPoison, Poison
from .paralysis import Paralysis
from .sleep import Sleep
from .freeze import Freeze

BurnStatus = Burn
PoisonStatus = Poison
BadPoisonStatus = BadPoison
ParalysisStatus = Paralysis
SleepStatus = Sleep
FreezeStatus = Freeze

__all__ = [
	'StatusCondition',
	'can_apply_status',
	'has_ability',
	'has_type',
	'iter_allies',
	'STATUS_BURN',
	'STATUS_POISON',
	'STATUS_TOXIC',
	'STATUS_PARALYSIS',
	'STATUS_SLEEP',
	'STATUS_FREEZE',
	'Burn',
	'BurnStatus',
	'Poison',
	'PoisonStatus',
	'BadPoison',
	'BadPoisonStatus',
	'Paralysis',
	'ParalysisStatus',
	'Sleep',
	'SleepStatus',
	'Freeze',
	'FreezeStatus',
]
