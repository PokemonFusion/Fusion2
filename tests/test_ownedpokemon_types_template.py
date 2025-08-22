import os
import sys
import types

from django.conf import settings
from django.template import Context, Engine

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
if not settings.configured:
	settings.configure(
		SECRET_KEY="test",
		DEFAULT_CHARSET="utf-8",
		INSTALLED_APPS=[],
		USE_I18N=False,
		ROOT_URLCONF="tests.urls",
		CHANNEL_LOG_NUM_TAIL_LINES=100,
	)


class DummyOwnedPokemon:
	"""Minimal OwnedPokemon stand-in for type lookup and template tests."""

	def __init__(self, species, level=1, nickname="", data=None):
		self.species = species
		self.level = level
		self.nickname = nickname
		self.data = data or {}
		self._types_override = None

	@property
	def name(self) -> str:
		return self.nickname or self.species

	def _lookup_species_types(self) -> list[str]:
		species_name = self.species
		entry = POKEDEX.get(species_name) or POKEDEX.get(species_name.lower()) or POKEDEX.get(species_name.capitalize())
		if entry:
			types = getattr(entry, "types", None)
			if types is None and isinstance(entry, dict):
				types = entry.get("types")
			if types:
				return [str(t).title() for t in types if t]
		return []

	@property
	def types(self) -> list[str]:
		override = getattr(self, "_types_override", None)
		if override is not None:
			return override
		ts = self._lookup_species_types()
		if ts:
			return ts
		data = getattr(self, "data", {}) or {}
		t_from_json = data.get("type") or data.get("types")
		if isinstance(t_from_json, str):
			return [p.strip().title() for p in t_from_json.replace(",", "/").split("/") if p.strip()]
		if isinstance(t_from_json, (list, tuple)):
			return [str(p).title() for p in t_from_json if p]
		return []


def render_character_sheet(pokemon_list: list[DummyOwnedPokemon]) -> str:
	tpl_path = os.path.join(ROOT, "web", "templates", "website", "character_sheet.html")
	tpl_str = open(tpl_path).read().replace('{% extends "website/base.html" %}', "")
	engine = Engine()
	return engine.from_string(tpl_str).render(
		Context(
			{
				"characters": [
					{
						"character": types.SimpleNamespace(key="Test"),
						"trainer": None,
						"pokemon": pokemon_list,
					}
				]
			}
		)
	)


def test_types_and_template_rendering():
	import importlib

	globals()["POKEDEX"] = importlib.import_module("pokemon.dex").POKEDEX
	assert "Pikachu" in POKEDEX
	mon = DummyOwnedPokemon("Pikachu", level=5)
	assert mon.types == ["Electric"]

	missing = DummyOwnedPokemon("Unknownmon")
	assert missing.types == []

	rendered = render_character_sheet([mon, missing])
	assert '<span class="type-chip type-electric">Electric</span>' in rendered
	assert '<span class="type-chip type-unknown">Unknown</span>' in rendered
