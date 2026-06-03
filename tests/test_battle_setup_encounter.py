import types

from pokemon.battle import setup
from pokemon.battle.battledata import Pokemon
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


def test_build_initial_state_preserves_full_opponent_team():
	origin = types.SimpleNamespace(db=types.SimpleNamespace(weather="clear"))
	player_mon = Pokemon("Bulbasaur", level=5, hp=10, max_hp=10)
	player_mon.model_id = "owned:1"
	opponent_lead = Pokemon("Pikachu", level=5, hp=10, max_hp=10)
	opponent_lead.model_id = "encounter:lead"
	opponent_reserve = Pokemon("Eevee", level=5, hp=10, max_hp=10)
	opponent_reserve.model_id = "encounter:reserve"
	captainA = types.SimpleNamespace(key="Player", id=7)
	captainB = types.SimpleNamespace(key="Static Trainer", id="npc-1")
	player_participant, opponent_participant = setup.create_participants(
		captainA,
		[player_mon],
		opponent_lead,
		"Static Trainer",
		captainB,
		opponent_team=[opponent_lead, opponent_reserve],
	)

	logic = setup.build_initial_state(
		origin,
		BattleType.TRAINER,
		player_participant,
		opponent_participant,
		[player_mon],
		opponent_lead,
		captainA,
		lambda msg: None,
		captainB,
		opponent_team=[opponent_lead, opponent_reserve],
	)

	assert opponent_participant.pokemons == [opponent_lead, opponent_reserve]
	assert opponent_participant.active == [opponent_lead]
	assert logic.data.teams["B"].returnlist()[:2] == [opponent_lead, opponent_reserve]
	assert logic.state.teams["B"] == [2, 3]
	assert logic.state.positions["B1"] == 2
	assert logic.state.pokemon_control["encounter:lead"] == "npc-1"
	assert logic.state.pokemon_control["encounter:reserve"] == "npc-1"


def test_create_participants_copies_opponent_ai_profile():
	captain = types.SimpleNamespace(key="Player")
	player_mon = types.SimpleNamespace(name="Bulbasaur")
	opponent_mon = types.SimpleNamespace(name="Rattata")
	opponent_controller = types.SimpleNamespace(
		ai_profile="trainer_skilled",
		is_npc=True,
	)

	_, opponent_participant = setup.create_participants(
		captain,
		[player_mon],
		opponent_mon,
		"Youngster Emery",
		opponent_controller,
	)

	assert opponent_participant.player is opponent_controller
	assert opponent_participant.ai_profile == "trainer_skilled"
	assert getattr(opponent_participant, "is_npc", False)


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

	def fake_init(origin, player_pokemon, opponent_poke, opponent_name, battle_type, **kwargs):
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
	assert session.captainB.ai_profile == "wild_basic"
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

	def fake_init(origin, player_pokemon, opponent_poke, opponent_name, battle_type, **kwargs):
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
	assert session.captainB.ai_profile == "trainer_basic"
	assert session.trainers == [session.captainA, session.captainB]
	assert session.captainB.db.battle_id == session.battle_id
	assert session.captainB.db.battle_lock == session.battle_id


def test_battle_session_select_opponent_uses_generated_trainer_encounter(monkeypatch):
	from pokemon.battle import battleinstance as battleinstance_mod

	room = types.SimpleNamespace(
		db=types.SimpleNamespace(battles=[]),
		ndb=types.SimpleNamespace(battle_instances={}),
	)
	player = types.SimpleNamespace(
		key="Player",
		id=3,
		db=types.SimpleNamespace(),
		ndb=types.SimpleNamespace(),
		storage=types.SimpleNamespace(get_party=lambda: []),
		location=room,
	)
	mon = types.SimpleNamespace(name="Rattata", model_id="encounter:1")
	reserve = types.SimpleNamespace(name="Pidgey", model_id="encounter:2")
	encounter = types.SimpleNamespace(
		display_name="Youngster Emery",
		intro_text="Youngster Emery challenges you with Rattata!",
		team=[mon, reserve],
		ai_profile="trainer_skilled",
	)
	captured = {}

	class TrainerOnlyRng:
		def choice(self, values):
			return "trainer"

	def fake_generate_random_trainer_encounter(passed_room, *, rng=None):
		captured["room"] = passed_room
		captured["rng"] = rng
		return encounter

	monkeypatch.setattr(
		battleinstance_mod,
		"generate_random_trainer_encounter",
		fake_generate_random_trainer_encounter,
	)

	session = BattleSession(player, rng=TrainerOnlyRng())
	opponent_poke, opponent_name, battle_type, intro_message = session._select_opponent()

	assert opponent_poke is mon
	assert opponent_name == "Youngster Emery"
	assert battle_type == BattleType.TRAINER
	assert intro_message == encounter.intro_text
	assert session.temp_pokemon_ids == ["encounter:1", "encounter:2"]
	assert session._pending_opponent_team == [mon, reserve]
	assert session._pending_opponent_ai_profile == "trainer_skilled"
	assert captured["room"] is room
	assert captured["rng"] is session.rng


def test_battle_session_start_trainer_encounter_preserves_display_name():
	room = types.SimpleNamespace(
		db=types.SimpleNamespace(battles=[]),
		ndb=types.SimpleNamespace(battle_instances={}),
	)
	player = types.SimpleNamespace(
		key="Player",
		id=4,
		db=types.SimpleNamespace(),
		ndb=types.SimpleNamespace(),
		storage=types.SimpleNamespace(get_party=lambda: []),
		location=room,
	)
	mon = types.SimpleNamespace(name="Pikachu", model_id="encounter:static-1")
	encounter = types.SimpleNamespace(
		display_name="Test Trainer",
		intro_text="Test Trainer challenges you with Pikachu!",
		team=[mon],
		ai_profile="gym_leader",
	)
	session = BattleSession(player)
	session._prepare_player_party = lambda trainer: []

	def fake_init(origin, player_pokemon, opponent_poke, opponent_name, battle_type, **kwargs):
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

	session.start_trainer_encounter(encounter)

	assert session.captainB is not None
	assert session.captainB.name == "Test Trainer"
	assert session.captainB.active_pokemon is mon
	assert session.captainB.team == [mon]
	assert getattr(session.captainB, "is_npc", False)
	assert session.captainB.ai_profile == "gym_leader"
	assert session._pending_opponent_ai_profile == "gym_leader"
	assert session.temp_pokemon_ids == ["encounter:static-1"]


def test_battle_session_start_trainer_encounter_preserves_full_team():
	room = types.SimpleNamespace(
		db=types.SimpleNamespace(battles=[]),
		ndb=types.SimpleNamespace(battle_instances={}),
	)
	player = types.SimpleNamespace(
		key="Player",
		id=5,
		db=types.SimpleNamespace(),
		ndb=types.SimpleNamespace(),
		storage=types.SimpleNamespace(get_party=lambda: []),
		location=room,
	)
	lead = types.SimpleNamespace(name="Pikachu", model_id="encounter:static-1")
	reserve = types.SimpleNamespace(name="Eevee", model_id="encounter:static-2")
	encounter = types.SimpleNamespace(
		display_name="Test Trainer",
		trainer_class="Gym Leader",
		source_type="gym_leader",
		intro_text="Test Trainer challenges you with Pikachu!",
		team=[lead, reserve],
		ai_profile="trainer_basic",
		metadata={"gym_key": "test_gym", "badge_key": "test_badge"},
	)
	session = BattleSession(player)
	session._prepare_player_party = lambda trainer: []
	captured = {}

	def fake_init(origin, player_pokemon, opponent_poke, opponent_name, battle_type, **kwargs):
		captured["opponent_poke"] = opponent_poke
		captured["opponent_name"] = opponent_name
		captured["battle_type"] = battle_type
		captured["opponent_team"] = kwargs.get("opponent_team")
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

	session.start_trainer_encounter(encounter)

	assert session.captainB is not None
	assert session.captainB.name == "Test Trainer"
	assert session.captainB.active_pokemon is lead
	assert session.captainB.team == [lead, reserve]
	assert captured["opponent_poke"] is lead
	assert captured["opponent_name"] == "Test Trainer"
	assert captured["battle_type"] == BattleType.TRAINER
	assert captured["opponent_team"] == [lead, reserve]
	assert session.temp_pokemon_ids == ["encounter:static-1", "encounter:static-2"]
	assert session.encounter_metadata["source_type"] == "gym_leader"
	assert session.encounter_metadata["display_name"] == "Test Trainer"
	assert session.encounter_metadata["trainer_class"] == "Gym Leader"
	assert session.encounter_metadata["gym_key"] == "test_gym"
	assert session.encounter_metadata["badge_key"] == "test_badge"
