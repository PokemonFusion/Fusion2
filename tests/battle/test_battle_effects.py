"""Tests for the +effects battle state renderer."""

from types import SimpleNamespace

from pokemon.battle.battledata import BattleData, Pokemon, Team
from pokemon.ui.battle_effects import render_effects_panel
from utils.battle_display import strip_ansi


def _mon(
	name: str,
	*,
	ability=None,
	item=None,
	held_item="",
	boosts=None,
	volatiles=None,
	effects=None,
):
	return SimpleNamespace(
		name=name,
		species=name,
		level=5,
		hp=10,
		max_hp=20,
		gender="N",
		status="",
		ability=ability,
		item=item,
		held_item=held_item,
		boosts=boosts or {},
		volatiles=volatiles or {},
		effects=effects or [],
	)


def _session(player_mon, foe_mon, *, state=None, battle=None):
	player = SimpleNamespace(name="Spike", active_pokemon=player_mon)
	foe = SimpleNamespace(name="Wild Pidgey", active_pokemon=foe_mon, is_wild=True)
	data = BattleData(Team("Spike", [player_mon]), Team("Wild Pidgey", [foe_mon]))
	return SimpleNamespace(
		captainA=player,
		captainB=foe,
		teamA=[player],
		teamB=[foe],
		state=state or SimpleNamespace(turn=2, encounter_kind="wild"),
		battle=battle,
		logic=SimpleNamespace(data=data, battle=battle),
	)


def test_effects_panel_reads_item_ability_stages_and_volatiles() -> None:
	player_mon = _mon(
		"Bulbasaur",
		ability="Overgrow",
		held_item="",
		boosts={"attack": 2, "special_defense": -1},
		volatiles={"taunt": {"duration": 3}, "confusion": True},
	)
	foe_mon = _mon("Pidgey", ability="Keen Eye", held_item="")
	session = _session(player_mon, foe_mon)

	clean = strip_ansi(render_effects_panel(session, session.captainA, total_width=78))

	assert "Item: None   Ability: Overgrow" in clean
	assert "Stages: Atk+2 SpD-1" in clean
	assert "Taunt 3t" in clean
	assert "Confusion" in clean


def test_effects_panel_reads_battle_field_and_side_conditions() -> None:
	player_mon = _mon("Bulbasaur")
	foe_mon = _mon("Pidgey")
	side_a = SimpleNamespace(
		conditions={"reflect": {"duration": 4}, "tailwind": {"duration": 2}, "stealthrock": {}},
		hazards={"spikes": 2},
		screens={},
	)
	side_b = SimpleNamespace(conditions={}, hazards={}, screens={})
	battle = SimpleNamespace(
		field=SimpleNamespace(
			weather="rain",
			weather_state={"duration": 5},
			terrain="",
			pseudo_weather={"trickroom": {"duration": 3}},
		),
		participants=[
			SimpleNamespace(team="A", side=side_a),
			SimpleNamespace(team="B", side=side_b),
		],
	)
	session = _session(player_mon, foe_mon, battle=battle)

	clean = strip_ansi(render_effects_panel(session, session.captainA, total_width=78))

	assert "Rain 5t" in clean
	assert "Trick Room 3t" in clean
	assert "Reflect 4t" in clean
	assert "Tailwind 2t" in clean
	assert "Hazards: SR" in clean
	assert "Spikes" in clean and "2" in clean


def test_effects_hides_unrevealed_opponent_ability() -> None:
	player_mon = _mon("Bulbasaur", ability="Overgrow")
	foe_mon = _mon("Pidgey", ability="Keen Eye")
	session = _session(player_mon, foe_mon)

	clean = strip_ansi(render_effects_panel(session, session.captainA, total_width=78))

	assert "Item: None   Ability: Overgrow" in clean
	assert "Item: None   Ability: Unknown" in clean
	assert "Keen Eye" not in clean


def test_effects_shows_revealed_ability_to_matching_side_only() -> None:
	player_mon = _mon("Bulbasaur", ability="Overgrow")
	foe_mon = _mon("Pidgey", ability="Keen Eye")
	session = _session(player_mon, foe_mon)
	session.logic.data.reveal_ability_to_viewer("A", foe_mon, "Keen Eye", pokemon_side="B")

	clean_a = strip_ansi(render_effects_panel(session, session.captainA, total_width=78))
	clean_b = strip_ansi(render_effects_panel(session, session.captainB, total_width=78))

	assert "Ability: Keen Eye" in clean_a
	assert "Ability: Overgrow" not in clean_b
	assert "Ability: Unknown" in clean_b


def test_effects_global_reveal_is_visible_to_other_side() -> None:
	player_mon = _mon("Bulbasaur", ability="Overgrow")
	foe_mon = _mon("Pidgey", ability="Keen Eye")
	session = _session(player_mon, foe_mon)
	session.logic.data.reveal_ability_to_all(player_mon, "Overgrow", pokemon_side="A")

	clean = strip_ansi(render_effects_panel(session, session.captainB, total_width=78))

	assert "Ability: Overgrow" in clean


def test_effects_admin_reveal_can_show_and_hide_hidden_abilities() -> None:
	player_mon = _mon("Bulbasaur", ability="Overgrow")
	foe_mon = _mon("Pidgey", ability="Keen Eye")
	session = _session(player_mon, foe_mon)
	admin = SimpleNamespace(name="GM", is_superuser=True)

	clean = strip_ansi(render_effects_panel(session, admin, total_width=78))
	assert "Ability: Keen Eye [admin]" in clean

	session.logic.data.admin_ability_reveal = False
	clean = strip_ansi(render_effects_panel(session, admin, total_width=78))
	assert "Keen Eye" not in clean
	assert "Ability: Unknown" in clean


def test_entry_reveal_helper_marks_switch_in_abilities_global() -> None:
	from pokemon.battle.engine import Battle, BattleParticipant, BattleType

	player_mon = Pokemon("Bulbasaur", ability="Overgrow")
	foe_mon = Pokemon("Pidgey", ability="Intimidate")
	data = BattleData(Team("Spike", [player_mon]), Team("Wild Pidgey", [foe_mon]))
	participant_a = BattleParticipant("Spike", [player_mon], team="A")
	participant_b = BattleParticipant("Wild Pidgey", [foe_mon], is_ai=True, team="B")
	battle = Battle(BattleType.WILD, [participant_a, participant_b])
	battle.bind_reveal_data(data)

	assert battle.reveal_entry_ability(foe_mon) is True
	assert data.get_revealed_ability_for_viewer("A", foe_mon, pokemon_side="B") == "Intimidate"
	assert data.get_revealed_ability_for_viewer("B", foe_mon, pokemon_side="B") == "Intimidate"


def test_revealed_abilities_survive_battle_data_serialization() -> None:
	player_mon = Pokemon("Bulbasaur", ability="Overgrow", model_id=101)
	foe_mon = Pokemon("Pidgey", ability="Keen Eye", model_id=202)
	data = BattleData(Team("Spike", [player_mon]), Team("Wild Pidgey", [foe_mon]))
	data.reveal_ability_to_viewer("A", foe_mon, "Keen Eye", pokemon_side="B")
	data.admin_ability_reveal = False

	restored = BattleData.from_dict(data.to_dict())
	restored_foe = restored.teams["B"].returnlist()[0]

	assert restored.admin_ability_reveal is False
	assert restored.get_revealed_ability_for_viewer("A", restored_foe, pokemon_side="B") == "Keen Eye"
