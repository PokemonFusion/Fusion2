"""Test restoration of teams after rebuilding ndb references."""

import types

from .test_battle_rebuild import BattleHandler, BattleSession, DummyRoom


class DummyPokemonModel:
	"""Simple stand-in for a stored Pokémon model."""

	def __init__(self, name: str):
		self.name = name
		self.level = 5
		self.moves = ["tackle"]
		self.current_hp = 20
		# provide an identifier for build_battle_pokemon_from_model
		self.unique_id = name


class DummyStorage:
	"""Storage container returning a predefined party."""

	def __init__(self, party):
		self.party = party

	def get_party(self):  # pragma: no cover - trivial
		return list(self.party)


class DummyPlayer:
	"""Player with a configurable Pokémon party."""

	def __init__(self, pid: int, room: DummyRoom, party):
		self.key = f"Player{pid}"
		self.id = pid
		self.db = types.SimpleNamespace()
		self.ndb = types.SimpleNamespace()
		self.location = room
		self.storage = DummyStorage(party)

	def msg(self, text):  # pragma: no cover - interface stub
		pass


def test_pvp_team_restored_after_rebuild_ndb():
	"""Starting battle, clearing ndb, rebuilding restores teams."""

	room = DummyRoom()
	poke_a = DummyPokemonModel("Alpha")
	poke_b = DummyPokemonModel("Bravo")
	p1 = DummyPlayer(1, room, [poke_a])
	p2 = DummyPlayer(2, room, [poke_b])

	inst = BattleSession(p1, p2)
	inst.start_pvp()

	# sanity check initial teams
	assert [p.name for p in p1.team] == ["Alpha"]
	assert [p.name for p in p2.team] == ["Bravo"]

	# simulate reload by clearing ndb and team attributes
	p1.ndb = types.SimpleNamespace()
	p2.ndb = types.SimpleNamespace()
	p1.team = []
	p2.team = []
	room.ndb = types.SimpleNamespace()

	handler = BattleHandler()
	handler.register(inst)
	handler.rebuild_ndb()

	assert [p.name for p in p1.team] == ["Alpha"]
	assert [p.name for p in p2.team] == ["Bravo"]
