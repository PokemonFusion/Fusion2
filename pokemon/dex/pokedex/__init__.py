"""Regional Pokédex segments aggregated into a single mapping."""

from __future__ import annotations

from importlib import import_module
from typing import Dict

pokedex: Dict[str, dict] = {}

for name in (
	"kanto",
	"johto",
	"hoenn",
	"sinnoh",
	"unova",
	"kalos",
	"alola",
	"galar",
	"paldea",
	"extras",
):
	module = import_module(f"{__package__}.{name}")
	pokedex.update(getattr(module, "pokedex", {}))

__all__ = ["pokedex"]
