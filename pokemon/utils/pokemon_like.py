from __future__ import annotations

from typing import Optional, Protocol, Sequence, runtime_checkable


@runtime_checkable
class PokemonLike(Protocol):
	"""Protocol for objects representing a Pokémon."""

	name: str
	species: str
	ability: Optional[str]
	gender: Optional[str]
	types: Optional[Sequence[str]]
	type_: Optional[str]
	level: Optional[int]
	growth_rate: Optional[str]
	xp: Optional[int]
	experience: Optional[int]
	total_exp: Optional[int]
	hp: Optional[int]
	current_hp: Optional[int]
	moves: Sequence
	held_item: Optional[str]
	status: Optional[str]
	nature: Optional[str]
