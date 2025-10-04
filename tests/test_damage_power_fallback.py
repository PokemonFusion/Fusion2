"""Regression tests for damage calculation fallbacks."""

from types import SimpleNamespace

from pokemon.battle.engine import BattleMove, _apply_move_damage


class StubPokemon:
        """Lightweight Pokémon stub exposing the stats the damage engine expects."""

        def __init__(self, name: str, *, level: int = 50, types: list[str] | None = None):
                self.name = name
                self.level = level
                self.hp = 100
                self.max_hp = 100
                self.types = [t.title() for t in (types or ["Normal"])]
                self.status = 0
                self.toxic_counter = 0
                self.tempvals: dict[str, int] = {}
                self.ability = None
                self.item = None
                self.boosts = {
                        "atk": 0,
                        "def": 0,
                        "spa": 0,
                        "spd": 0,
                        "spe": 0,
                        "accuracy": 0,
                        "evasion": 0,
                }
                self.base_stats = SimpleNamespace(
                        attack=55,
                        defense=45,
                        special_attack=65,
                        special_defense=55,
                        speed=70,
                        hp=100,
                )


class StubBattle:
        """Minimal battle stub providing the hooks used by damage calculation."""

        def __init__(self, user, target):
                self._user = user
                self._target = target
                self._user_part = SimpleNamespace(active=[user], team=None, has_lost=False)
                self._target_part = SimpleNamespace(active=[target], team=None, has_lost=False)
                self.participants = [self._user_part, self._target_part]
                self.field = SimpleNamespace(terrain_handler=None, weather_handler=None)
                self.log_action = lambda *args, **kwargs: None

        def participant_for(self, pokemon):
                if pokemon is self._user:
                        return self._user_part
                if pokemon is self._target:
                        return self._target_part
                return None


def test_apply_move_damage_loads_power_from_dex_when_missing():
        """Battle damage falls back to dex base power when move.power is unset."""

        attacker = StubPokemon("Pikachu", types=["Electric"])
        target = StubPokemon("Squirtle", types=["Water"])
        move = BattleMove(
                name="Thunderbolt",
                power=0,
                accuracy=100,
                type="Electric",
                raw={"category": "Special"},
        )

        battle = StubBattle(attacker, target)
        result = _apply_move_damage(attacker, target, move, battle=battle)

        recorded_power = result.debug.get("power", [])
        assert recorded_power and recorded_power[0] == 90
        assert move.power == 90
