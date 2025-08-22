import math
import random
from typing import Optional

STATUS_MODIFIERS = {
	"slp": 2.5,
	"frz": 2.5,
	"par": 1.5,
	"brn": 1.5,
	"psn": 1.5,
	"tox": 1.5,
}


def attempt_capture(
	max_hp: int,
	current_hp: int,
	catch_rate: int,
	*,
	ball_modifier: float = 1.0,
	status: Optional[str] = None,
	rng: Optional[random.Random] = None,
) -> bool:
	"""Return True if a Pokémon is caught using modern mechanics."""

	rng = rng or random
	status_key = (status or "").lower()
	status_mod = STATUS_MODIFIERS.get(status_key, 1.0)

	a = math.floor(((3 * max_hp - 2 * current_hp) * catch_rate * ball_modifier * status_mod) / (3 * max_hp))
	a = max(1, a)

	if a >= 255:
		return True

	b = int(65536 / ((255 / a) ** 0.1875))
	for _ in range(4):
		if rng.randint(0, 65535) >= b:
			return False
	return True
