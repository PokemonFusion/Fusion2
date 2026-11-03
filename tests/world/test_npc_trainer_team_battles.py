from pokemon.battle.battledata import Pokemon
from pokemon.battle.engine import Battle, BattleType
from pokemon.battle.participants import BattleParticipant
from pokemon.data.text import DEFAULT_TEXT


def _pokemon(name: str, hp: int) -> Pokemon:
    return Pokemon(name, level=5, hp=hp, max_hp=10)


def _battle_with_npc_team(*npc_team: Pokemon) -> tuple[Battle, BattleParticipant, BattleParticipant]:
    player_mon = _pokemon("Bulbasaur", 10)
    player = BattleParticipant("Player", [player_mon], is_ai=False, team="A")
    npc = BattleParticipant("Static Trainer", list(npc_team), is_ai=True, team="B")
    player.active = [player_mon]
    npc.active = [npc_team[0]]
    player.side.active = player.active
    npc.side.active = npc.active
    battle = Battle(BattleType.TRAINER, [player, npc])
    return battle, player, npc


def test_npc_trainer_reserve_enters_when_active_pokemon_faints():
    lead = _pokemon("Pikachu", 0)
    reserve = _pokemon("Eevee", 10)
    battle, _player, npc = _battle_with_npc_team(lead, reserve)
    logs: list[str] = []
    battle.log_action = logs.append

    battle.run_faint()
    winner = battle.check_win_conditions()

    assert lead.is_fainted is True
    assert npc.has_lost is False
    assert npc.active == [reserve]
    assert npc.side.active is npc.active
    assert winner is None
    assert battle.battle_over is False
    switch_msg = (
        DEFAULT_TEXT["default"]["switchIn"]
        .replace("[TRAINER]", "Static Trainer")
        .replace("[FULLNAME]", "Eevee")
    )
    assert switch_msg in logs


def test_npc_trainer_battle_ends_only_after_all_team_members_faint():
    lead = _pokemon("Pikachu", 0)
    reserve = _pokemon("Eevee", 0)
    battle, player, npc = _battle_with_npc_team(lead, reserve)

    battle.run_faint()
    winner = battle.check_win_conditions()

    assert npc.has_lost is True
    assert npc.active == []
    assert winner is player
    assert battle.battle_over is True
