import pytest
from pokemon.battle.battledata import BattleData, Team, Pokemon, Move
from pokemon.battle.engine import execute_turn


def make_battle():
    team_a = Team(trainer="A", pokemon_list=[Pokemon(name="Pikachu", hp=100)])
    team_b = Team(trainer="B", pokemon_list=[Pokemon(name="Eevee", hp=100)])
    return BattleData(team_a, team_b)


def test_execute_moves():
    battle = make_battle()
    battle.turndata.positions["A1"].declareAttack("B1", Move("Tackle"))
    battle.turndata.positions["B1"].declareAttack("A1", Move("Tackle"))

    execute_turn(battle, damage=10)

    assert battle.turndata.positions["A1"].pokemon.hp == 90
    assert battle.turndata.positions["B1"].pokemon.hp == 90
    assert battle.battle.turn == 2


@pytest.mark.xfail(reason="Switching not implemented yet")
def test_switching():
    battle = make_battle()
    battle.teams["A"].slot2 = Pokemon(name="Charmander", hp=100)
    battle.turndata.positions["A1"].declareSwitch(2)
    execute_turn(battle)
    assert battle.turndata.positions["A1"].pokemon.name == "Charmander"


@pytest.mark.xfail(reason="Faint resolution not implemented yet")
def test_faint_resolution():
    battle = make_battle()
    battle.turndata.positions["A1"].declareAttack("B1", Move("Tackle"))
    battle.turndata.positions["B1"].pokemon.hp = 5
    execute_turn(battle, damage=10)
    assert battle.turndata.positions["B1"].pokemon is None
