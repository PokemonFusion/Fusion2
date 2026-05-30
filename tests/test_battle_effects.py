"""Tests for the +effects battle state renderer."""

from types import SimpleNamespace

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
	return SimpleNamespace(
		captainA=player,
		captainB=foe,
		teamA=[player],
		teamB=[foe],
		state=state or SimpleNamespace(turn=2, encounter_kind="wild"),
		battle=battle,
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
