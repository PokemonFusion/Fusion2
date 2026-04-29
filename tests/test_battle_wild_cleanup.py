import os
import types

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from pokemon.battle.battleinstance import BattleSession
from pokemon.models.core import OwnedPokemon


class DummyRoom:
	def __init__(self):
		self.id = 1
		self.db = types.SimpleNamespace()
		self.ndb = types.SimpleNamespace()


class DummyPlayer:
	def __init__(self, room):
		self.key = "Player"
		self.id = 99
		self.db = types.SimpleNamespace()
		self.ndb = types.SimpleNamespace()
		self.location = room

	def msg(self, *args, **kwargs):
		return None

	def move_to(self, destination, quiet=False):
		self.location = destination


def test_wild_encounter_cleanup_deletes_ephemeral_refs(monkeypatch):
	handler = types.SimpleNamespace(register=lambda *a, **k: None, unregister=lambda *a, **k: None)
	monkeypatch.setattr("pokemon.battle.battleinstance.battle_handler", handler, raising=False)

	deleted = []
	monkeypatch.setattr(
		"pokemon.battle.battleinstance.delete_encounter_by_ref",
		lambda model_id: deleted.append(model_id) or True,
	)

	room = DummyRoom()
	player = DummyPlayer(room)

	session = BattleSession(player)
	session.logic = types.SimpleNamespace(
		state=None,
		battle=types.SimpleNamespace(participants=[]),
		data=None,
	)
	session.temp_pokemon_ids = ["encounter:test-mon"]

	session.end()

	assert deleted == ["encounter:test-mon"]
	assert session.temp_pokemon_ids == []


def test_ownedpokemon_party_slot_handles_missing_related_manager():
	dummy = types.SimpleNamespace(active_slots=object())
	assert OwnedPokemon.party_slot.fget(dummy) is None
