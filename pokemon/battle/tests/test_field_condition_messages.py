from pokemon.data.text import DEFAULT_TEXT
from pokemon.dex.functions import conditions_funcs as cond_mod

from .helpers import build_battle


def test_sandstorm_logs_start_upkeep_and_end() -> None:
        battle, attacker, _ = build_battle()
        logs: list[str] = []
        battle.log_action = logs.append

        assert battle.setWeather("sandstorm", source=attacker) is True

        start_msg = DEFAULT_TEXT["sandstorm"]["start"]
        upkeep_msg = DEFAULT_TEXT["sandstorm"].get("upkeep")
        end_msg = DEFAULT_TEXT["sandstorm"]["end"]

        assert start_msg in logs

        for _ in range(5):
                battle.handle_weather()

        if upkeep_msg:
                assert upkeep_msg in logs
        assert end_msg in logs
        assert battle.field.weather is None


def test_electric_terrain_logs_start_block_and_end(monkeypatch) -> None:
        class DummyElectricTerrain:
                def __init__(self) -> None:
                        self.duration = 2

                def durationCallback(self, source=None, *_args, **_kwargs):
                        return self.duration

                def onFieldStart(self, field, source=None, *_args, **_kwargs):
                        field.pseudo_weather["electricterrain"] = {"duration": self.duration}

                def onFieldResidual(self, field, *_args, **_kwargs):
                        effect = field.pseudo_weather.get("electricterrain")
                        if not effect:
                                return
                        effect["duration"] -= 1
                        if effect["duration"] <= 0:
                                field.pseudo_weather.pop("electricterrain", None)

                def onFieldEnd(self, field, *_args, **_kwargs):
                        field.pseudo_weather.pop("electricterrain", None)

        monkeypatch.setattr(cond_mod, "Electricterrain", DummyElectricTerrain, raising=False)

        battle, attacker, defender = build_battle()
        logs: list[str] = []
        battle.log_action = logs.append

        assert battle.setTerrain("electricterrain", source=attacker) is True

        start_msg = DEFAULT_TEXT["electricterrain"]["start"]
        block_msg = DEFAULT_TEXT["electricterrain"]["block"].replace("[POKEMON]", defender.name)
        end_msg = DEFAULT_TEXT["electricterrain"]["end"]

        assert start_msg in logs

        battle.apply_status_condition(defender, "slp", source=attacker, effect="move:spore")
        assert block_msg in logs

        for _ in range(2):
                battle.handle_terrain()

        assert end_msg in logs
        assert battle.field.terrain is None
