import types

from pokemon.battle import setup
from pokemon.battle.engine import BattleType
from pokemon.battle.battleinstance import BattleSession


def test_build_initial_state_marks_wild_encounter(monkeypatch):
	state_stub = types.SimpleNamespace(
		encounter_kind="",
		pokemon_control={},
		roomweather="",
		watchers=set(),
	)

	def fake_from_battle_data(cls, data, ai_type="Wild"):
		return state_stub

	monkeypatch.setattr(
		setup.BattleState,
		"from_battle_data",
		classmethod(fake_from_battle_data),
	)

	monkeypatch.setattr(
		setup,
		"Battle",
		lambda *args, **kwargs: types.SimpleNamespace(log_action=None),
	)

	class DummyLogic:
		def __init__(self, battle, data, state):
			self.battle = battle
			self.data = data
			self.state = state

	monkeypatch.setattr(setup, "BattleLogic", DummyLogic)

	origin = types.SimpleNamespace(db=types.SimpleNamespace(weather="clear"))
	player_participant = types.SimpleNamespace(
		key="Player",
		pokemons=[object()],
		active=[object()],
	)
	opponent_participant = types.SimpleNamespace(
		key="Wild Opponent",
		pokemons=[object()],
		active=[object()],
	)
	player_pokemon = [types.SimpleNamespace(model_id=1, hp=10, max_hp=10)]
	opponent_poke = types.SimpleNamespace(model_id=None, name="Oddish", hp=10, max_hp=10)
	captainA = types.SimpleNamespace(key="Player", id=7)

	logic = setup.build_initial_state(
		origin,
		BattleType.WILD,
		player_participant,
		opponent_participant,
		player_pokemon,
		opponent_poke,
		captainA,
		lambda msg: None,
	)

	assert logic.state.encounter_kind == "wild"
	assert state_stub.encounter_kind == "wild"


def test_battle_session_start_assigns_wild_shell(monkeypatch):
	room = types.SimpleNamespace(
		db=types.SimpleNamespace(battles=[]),
		ndb=types.SimpleNamespace(battle_instances={}),
	)
	player = types.SimpleNamespace(
		key="Player",
		id=1,
		db=types.SimpleNamespace(),
		ndb=types.SimpleNamespace(),
		storage=types.SimpleNamespace(get_party=lambda: []),
		location=room,
	)

	session = BattleSession(player)

	wild_mon = types.SimpleNamespace(name="Oddish")

	session._select_opponent = lambda: (wild_mon, "Wild", BattleType.WILD, None)
	session._prepare_player_party = lambda trainer: []

	def fake_init(origin, player_pokemon, opponent_poke, opponent_name, battle_type):
	        session.logic = types.SimpleNamespace(
	                state=types.SimpleNamespace(
	                        encounter_kind="wild",
	                        pokemon_control={},
	                        watchers=set(),
	                ),
	                data=None,
	                battle=None,
	        )

	session._init_battle_state = fake_init
	session._setup_battle_room = lambda intro_message=None: None

	session.start()

	assert session.captainB is not None
	assert session.captainB.active_pokemon is wild_mon
	assert session.captainB.team == [wild_mon]
	assert session.captainB.name == "Wild Oddish"
	assert getattr(session.captainB, "is_wild", False)
	assert session.trainers == [session.captainA, session.captainB]
	assert session.captainB.db.battle_id == session.battle_id
	assert session.captainB.db.battle_lock == session.battle_id
	assert player.db.battle_lock == session.battle_id


def test_battle_session_start_assigns_trainer_shell(monkeypatch):
	room = types.SimpleNamespace(
	        db=types.SimpleNamespace(battles=[]),
	        ndb=types.SimpleNamespace(battle_instances={}),
	)
	player = types.SimpleNamespace(
	        key="Player",
	        id=2,
	        db=types.SimpleNamespace(),
	        ndb=types.SimpleNamespace(),
	        storage=types.SimpleNamespace(get_party=lambda: []),
	        location=room,
	)

	session = BattleSession(player)

	trainer_mon = types.SimpleNamespace(name="Charmander")
	session._select_opponent = lambda: (
	        trainer_mon,
	        "Trainer Casey",
	        BattleType.TRAINER,
	        "Trainer Casey challenges you!",
	)
	session._prepare_player_party = lambda trainer: []

	def fake_init(origin, player_pokemon, opponent_poke, opponent_name, battle_type):
	        session.logic = types.SimpleNamespace(
	                state=types.SimpleNamespace(
	                        encounter_kind="trainer",
	                        pokemon_control={},
	                        watchers=set(),
	                ),
	                data=None,
	                battle=None,
	        )

	session._init_battle_state = fake_init
	session._setup_battle_room = lambda intro_message=None: None

	session.start()

	assert session.captainB is not None
	assert session.captainB.name == "Trainer Casey"
	assert session.captainB.active_pokemon is trainer_mon
	assert session.captainB.team == [trainer_mon]
	assert getattr(session.captainB, "is_npc", False)
	assert session.trainers == [session.captainA, session.captainB]
	assert session.captainB.db.battle_id == session.battle_id
	assert session.captainB.db.battle_lock == session.battle_id
