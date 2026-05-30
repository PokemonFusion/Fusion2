import random
import types


from unittest.mock import patch

from pokemon.battle.actions import Action, ActionType
from pokemon.battle.engine import Battle, BattleParticipant, BattleType
from pokemon.battle.battleinstance import BattleSession


class SimplePokemon:
        """Minimal Pokémon stub for flee tests."""

        def __init__(self, name: str, speed: int, ability=None):
                self.name = name
                self.hp = 100
                self.max_hp = 100
                self.speed = speed
                self.ability = ability
                self.moves = []
                self.tempvals = {}
                self.volatiles = {}
                self.boosts = {}


def _build_battle(player_poke, opponent_poke, *, rng=None):
        player = BattleParticipant("Player", [player_poke])
        opponent = BattleParticipant("Wild", [opponent_poke])
        player.active = [player_poke]
        opponent.active = [opponent_poke]
        return Battle(BattleType.WILD, [player, opponent], rng=rng)


def test_run_success_marks_battle_over_and_logs():
        fast = SimplePokemon("Swift", speed=120)
        slow = SimplePokemon("Slug", speed=30)
        battle = _build_battle(fast, slow)
        messages = []
        battle.log_action = messages.append

        action = Action(battle.participants[0], ActionType.RUN, pokemon=fast)
        battle.execute_actions([action])

        assert battle.battle_over is True
        assert battle.participants[0].flee_attempts == 1
        assert messages and "fled" in messages[-1].lower()


def test_run_failure_consumes_attempt_and_logs():
        slow_runner = SimplePokemon("Runner", speed=30)
        fast_foe = SimplePokemon("Hunter", speed=90)
        rng = random.Random(0)
        battle = _build_battle(slow_runner, fast_foe, rng=rng)
        messages = []
        battle.log_action = messages.append

        action = Action(battle.participants[0], ActionType.RUN, pokemon=slow_runner)
        battle.execute_actions([action])

        assert battle.battle_over is False
        assert battle.participants[0].flee_attempts == 1
        assert messages and "couldn't get away" in messages[-1].lower()


def test_run_blocked_by_arena_trap():
        runner = SimplePokemon("Runner", speed=150)
        trapper = SimplePokemon("Trapper", speed=10, ability="Arena Trap")
        battle = _build_battle(runner, trapper)
        messages = []
        battle.log_action = messages.append

        action = Action(battle.participants[0], ActionType.RUN, pokemon=runner)
        battle.execute_actions([action])

        assert battle.battle_over is False
        assert battle.participants[0].flee_attempts == 1
        assert battle._flee_result["reason"] == "trapped"
        assert any("trapped" in msg.lower() for msg in messages)


def test_switch_action_uses_selected_pokemon():
        lead = SimplePokemon("Lead", speed=80)
        bench = SimplePokemon("Bench", speed=70)
        opponent_poke = SimplePokemon("Opponent", speed=50)
        player = BattleParticipant("Player", [lead, bench])
        opponent = BattleParticipant("Wild", [opponent_poke])
        player.active = [lead]
        opponent.active = [opponent_poke]
        battle = Battle(BattleType.WILD, [player, opponent])

        action = Action(player, ActionType.SWITCH, pokemon=bench, target=bench, priority=6)

        with patch.object(battle, "perform_switch_action") as switch:
                battle.execute_actions([action])

        switch.assert_called_once_with(player, bench)


def test_run_away_overrides_trap():
        runner = SimplePokemon("Runner", speed=20, ability="Run Away")
        trapper = SimplePokemon("Trapper", speed=100, ability="Arena Trap")
        battle = _build_battle(runner, trapper, rng=random.Random(0))
        messages = []
        battle.log_action = messages.append

        action = Action(battle.participants[0], ActionType.RUN, pokemon=runner)
        battle.execute_actions([action])

        assert battle.battle_over is True
        assert battle._flee_result["reason"] == "runaway"
        assert any("fled" in msg.lower() for msg in messages)


class _DummyBattle:
        def __init__(self, *, end_after=True):
                self.turn_count = 0
                self.participants = [types.SimpleNamespace(pokemons=[object()])]
                self.battle_over = False
                self._end_after = end_after

        def run_turn(self):
                self.turn_count += 1
                self.battle_over = self._end_after

        def check_win_conditions(self):
                return None


def _make_session(battle, *, end_expected):
        session = BattleSession.__new__(BattleSession)
        state = types.SimpleNamespace(turn=1, declare={})
        data = types.SimpleNamespace(
                battle=types.SimpleNamespace(turn=1),
                turndata=types.SimpleNamespace(positions={}),
        )
        session.logic = types.SimpleNamespace(battle=battle, state=state, data=data)
        session.trainers = []
        session.teamA = []
        session.teamB = []
        session.battle_id = 1
        session.turn_state = {}
        session._set_player_control = lambda value: None
        session._notify_turn_banner = lambda *a, **kw: None
        session._persisted = False

        def persist():
                session._persisted = True

        session._persist_turn_state = persist
        session.prompt_called = False

        def prompt():
                session.prompt_called = True

        session.prompt_next_turn = prompt
        session.ended = False

        def end():
                session.ended = True

        session.end = end
        session.msg = lambda *a, **kw: None
        session.notify = lambda *a, **kw: None
        session.debug_events = []

        def persist_debug_record(**kwargs):
                session.debug_events.append(kwargs)

        session.persist_debug_record = persist_debug_record
        return session


def test_battle_session_ends_on_successful_flee():
        battle = _DummyBattle(end_after=True)
        session = _make_session(battle, end_expected=True)
        session.run_turn()

        assert session.ended is True
        assert session.prompt_called is False
        assert session._persisted is False


def test_battle_session_prompts_after_failed_flee():
        battle = _DummyBattle(end_after=False)
        session = _make_session(battle, end_expected=False)
        session.run_turn()

        assert session.ended is False
        assert session.prompt_called is True
        assert session._persisted is True


class _ExplodingBattle(_DummyBattle):
        def run_turn(self):
                raise RuntimeError("boom")


def test_battle_session_records_turn_error_debug():
        battle = _ExplodingBattle(end_after=False)
        session = _make_session(battle, end_expected=False)

        session.run_turn()

        assert "error" in session.turn_state
        assert any(event.get("event") == "turn_error" for event in session.debug_events)
        assert "boom" in session.turn_state["error"]


class _DummyPosition:
        def __init__(self, pokemon):
                self.pokemon = pokemon
                self.cleared = False

        def removeDeclare(self):
                self.cleared = True


class _DummyTeam:
        def __init__(self, pokemons):
                self.pokemons = pokemons

        def returnlist(self):
                return self.pokemons


def test_battle_session_syncs_switched_active_pokemon_before_prompt():
        lead = SimplePokemon("Charmander", speed=65)
        bench = SimplePokemon("Pikachu", speed=90)
        foe = SimplePokemon("Rattata", speed=72)
        player = types.SimpleNamespace(
                name="Player",
                team="A",
                player=None,
                pokemons=[lead, bench],
                active=[lead],
        )
        opponent = types.SimpleNamespace(
                name="Wild",
                team="B",
                player=None,
                pokemons=[foe],
                active=[foe],
        )

        class _SwitchingBattle:
                def __init__(self):
                        self.turn_count = 1
                        self.participants = [player, opponent]
                        self.battle_over = False

                def run_turn(self):
                        self.turn_count += 1
                        player.active[0] = bench

                def check_win_conditions(self):
                        return None

        session = BattleSession.__new__(BattleSession)
        state = types.SimpleNamespace(
                turn=1,
                declare={"A1": {"switch": 2}, "B1": {"move": "quickattack"}},
                positions={"A1": 1, "B1": 3},
                teams={"A": [1, 2], "B": [3]},
        )
        pos_a = _DummyPosition(lead)
        pos_b = _DummyPosition(foe)
        data = types.SimpleNamespace(
                battle=types.SimpleNamespace(turn=1),
                teams={"A": _DummyTeam([lead, bench]), "B": _DummyTeam([foe])},
                turndata=types.SimpleNamespace(positions={"A1": pos_a, "B1": pos_b}),
        )
        session.logic = types.SimpleNamespace(battle=_SwitchingBattle(), state=state, data=data)
        captain_a = types.SimpleNamespace(active_pokemon=lead)
        captain_b = types.SimpleNamespace(active_pokemon=foe)
        session.teamA = [captain_a]
        session.teamB = [captain_b]
        session.trainers = []
        session.battle_id = 1
        session.turn_state = {}
        session._set_player_control = lambda value: None
        session._notify_turn_banner = lambda *a, **kw: None
        session._persist_turn_state = lambda: None
        session.msg = lambda *a, **kw: None
        session.notify = lambda *a, **kw: None
        session.debug_events = []
        session.persist_debug_record = lambda **kwargs: session.debug_events.append(kwargs)
        session.prompt_called = False
        session.prompt_next_turn = lambda: setattr(session, "prompt_called", True)

        session.run_turn()

        assert captain_a.active_pokemon is bench
        assert pos_a.pokemon is bench
        assert state.positions["A1"] == 2
        assert state.declare == {}
        assert pos_a.cleared is True
        assert session.prompt_called is True


def test_run_move_invokes_flee_action():
        """`Battle.run_move` should execute queued flee actions via `attempt_flee`."""

        runner = SimplePokemon("Runner", speed=80)
        opponent = SimplePokemon("Opponent", speed=50)
        battle = _build_battle(runner, opponent)
        run_action = Action(
                battle.participants[0],
                ActionType.RUN,
                battle.participants[1],
                pokemon=runner,
        )
        battle.participants[0].pending_action = run_action

        def _fake_attempt(action):
                assert action is run_action
                battle.battle_over = True
                return True

        with patch.object(battle, "attempt_flee", side_effect=_fake_attempt) as attempt:
                battle.run_move()

        assert attempt.called
        assert battle.battle_over is True
