"""Behavioral coverage for compact HUD ownership, slots and readable choices."""

from types import SimpleNamespace as NS

import pytest

from pokemon.battle.interface import display_battle_interface, get_battle_ui_width
from pokemon.battle.messaging import MessagingMixin
from pokemon.ui.compact_battle import BattleText
from pokemon.ui.move_gui import render_move_gui
from utils.battle_display import strip_ansi


def mon(name="Pikachu", *, hp=42, maximum=60, **kwargs):
    """Make display-only values; these fixtures do not calculate species stats."""
    return NS(
        name=name,
        species=name,
        level=20,
        hp=hp,
        max_hp=maximum,
        status="",
        ability_state={},
        boosts={},
        volatiles={},
        moves=[],
        **kwargs,
    )


def trainer(name, identifier, **db):
    """Keep exact controller identity independent of side and display name."""
    return NS(name=name, key=name, pk=identifier, db=NS(**db), ndb=NS())


def battle(*, multi=False):
    """Create authoritative physical cells with distinct private HP values."""
    players = [
        trainer(name, index + 1) for index, name in enumerate(("Alex", "Blair", "Casey", "Dee"))
    ]
    mons = [
        mon(name, hp=hp, maximum=maximum)
        for name, hp, maximum in (
            ("Pikachu", 42, 60),
            ("Eevee", 37, 81),
            ("Pidgeotto", 26, 59),
            ("Oddish", 19, 47),
        )
    ]
    parts = []
    for index, label in enumerate(("A1", "A2", "B1", "B2")):
        controller = players[index] if multi else players[0 if index < 2 else 2]
        parts.append(
            NS(
                field_position=label if multi else None,
                player=controller,
                active=[mons[index]],
                pokemons=[mons[index]],
                team=label[0],
            )
        )
    positions = {
        label: NS(pokemon=pokemon) for label, pokemon in zip(("A1", "A2", "B1", "B2"), mons)
    }
    state = NS(turn=3, encounter_kind="trainer", declare={}, multi={}, flee_allowed=False)
    session = NS(
        captainA=players[0],
        captainB=players[2],
        teamA=players[:2] if multi else [players[0]],
        teamB=players[2:] if multi else [players[2]],
        state=state,
        battle=NS(participants=parts),
        data=NS(turndata=NS(positions=positions)),
    )
    for part in parts:
        part.player.active_pokemon = part.active[0]
        part.player.team = part.pokemons
    return session, players, mons


def render(session, viewer, width=78, **kwargs):
    """Exercise the public interface with the actual recipient supplied."""
    return display_battle_interface(
        session.captainA,
        session.captainB,
        session.state,
        viewer=viewer,
        session=session,
        total_width=width,
        **kwargs,
    )


@pytest.mark.parametrize("width", [24, 40, 60, 78, 100])
def test_all_cells_fit_and_opponent_hp_stays_private(width):
    """Doubles shows every cell at each supported width, without opponent HP."""
    session, players, _ = battle()
    output = strip_ansi(render(session, players[0], width))
    assert all(label in output for label in ("A1", "A2", "B1", "B2"))
    assert "42/60" in output and "37/81" in output
    assert "26/59" not in output and "19/47" not in output
    assert max(map(len, output.splitlines())) <= width


def test_multi_ally_is_not_the_viewer_and_observer_cannot_borrow_a_side():
    """Four controllers retain ownership even when two trainers share a side."""
    session, players, _ = battle(multi=True)
    output = strip_ansi(render(session, players[1]))
    assert "YOU A2" in output and "ALLY A1" in output
    assert "37/81" in output and "42/60" not in output
    watcher = trainer("Viewer", 99)
    output = strip_ansi(render(session, watcher, viewer_team="A"))
    assert "WATCHING" in output and "YOUR MOVE" not in output
    assert all(value not in output for value in ("42/60", "37/81", "26/59", "19/47"))
    assert "Fight:" not in output


def test_fusion_survives_checkpoint_identity_and_seventh_member_is_counted():
    """Use native references and the whole roster, not six truncated markers."""
    session, players, mons = battle()
    players[0].db.fusion_id = "fusion-id"
    mons[0].model_id = "owned:fusion-id"
    roster = [mon("Eevee") for _ in range(6)] + [mons[0]]
    session.battle.participants[0].pokemons = roster
    output = strip_ansi(render(session, players[0]))
    assert "[YOU / FUSION]" in output and "Alex (Pikachu)" in output
    assert "Team: 6/6 ready + Fusion" in output
    mons[0].model_id = "encounter:fusion-id"
    assert "[YOU / FUSION]" not in strip_ansi(render(session, players[0]))


def test_screenreader_removes_decorations_even_with_a_classic_preference():
    """Accessibility is a presentation mode, not only an ASCII symbol toggle."""
    session, players, mons = battle()
    players[0].db.ui_mode = "sr"
    mons[0].status = "par"
    output = render(session, players[0], style="legacy")
    assert "PARALYZED" in output and "HP: 42/60" in output
    assert not any(character in output for character in ("|", "█", "░", "#"))
    assert "----" not in output and "┌" not in output


def test_queued_state_does_not_claim_the_player_needs_another_action():
    """Read declarations rather than always announcing YOUR MOVE."""
    session, players, _ = battle()
    session.state.declare = {"A1": {"move": "tackle"}, "A2": {"move": "growl"}}
    output = strip_ansi(render(session, players[0]))
    assert "ACTION QUEUED" in output and "YOUR MOVE" not in output


def test_doubles_partial_choice_marks_queued_cell_and_guides_remaining_actor():
    """Do not direct the player back to an actor that already declared a move."""
    session, players, mons = battle()
    session.state.declare = {"A1": {"move": "tackle"}}
    mons[1].moves = [NS(name="Thunderbolt", pp=8)]
    output = strip_ansi(render(session, players[0]))
    assert "[QUEUED]" in output and "Your slots: A2" in output
    assert "Moves for A2:" in output and "+attack A2 A B1" in output


def test_runtime_nicknames_and_illusion_appearance_remain_visible():
    """Runtime battlers carry nicknames in name, with species kept separately."""
    session, players, mons = battle()
    mons[0].name = "Sparky"
    assert "Sparky (Pikachu)" in strip_ansi(render(session, players[0]))
    mons[0].ability_state = {"illusion": {"name": "Buddy", "species": "Eevee"}}
    output = strip_ansi(render(session, players[2]))
    assert "Buddy (Eevee)" in output and "Sparky" not in output and "Pikachu" not in output


def test_struggle_has_no_invented_pp_capacity():
    """The emergency move does not consume PP like a learned move."""
    output = strip_ansi(render_move_gui([NS(name="Struggle", pp=None)]))
    assert "Struggle" in output and "--" in output and "NO PP" not in output


def test_multi_deadline_and_missing_controllers_remain_visible():
    """The new default retains the Multi format's time and input information."""
    from datetime import datetime, timedelta, timezone

    session, players, _ = battle(multi=True)
    session.state.multi = {
        "deadline": (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()
    }
    session.state.declare = {"A1": {"move": "tackle"}}
    output = strip_ansi(render(session, players[0]))
    assert "Waiting on: A2, B1, B2" in output and "Action deadline:" in output


def test_move_detail_request_keeps_the_captured_prompt_without_queuing(monkeypatch):
    """? A reads a move; it must not silently submit it or lose actor checks."""
    import sys
    from types import ModuleType
    from commands.player.battle_choice_prompts import attack_prompt

    session, players, mons = battle()
    moves = [NS(name="Thunderbolt", pp=8)]
    mons[0].moves = moves
    deliveries, captured, actions = [], {}, []
    players[0].msg = deliveries.append
    choices = NS(
        actor=lambda _actor: ("A1", mons[0]),
        _check=lambda *_: None,
        legal_moves=lambda _: [NS(move=NS(key="thunderbolt", pp=8))],
        move=lambda *args, **kwargs: actions.append((args, kwargs)),
    )
    session.choices_for = lambda _: choices
    evmenu = ModuleType("evennia.utils.evmenu")

    def capture(_caller, prompt, callback):
        """Capture the real prompt's callback without starting Evennia."""
        captured.update(prompt=prompt, callback=callback)

    evmenu.get_input = capture
    monkeypatch.setitem(sys.modules, "evennia.utils.evmenu", evmenu)
    attack_prompt(session, players[0], "")
    assert captured["callback"](players[0], "", "? A") is True
    assert actions == [] and "Power: 90" in deliveries[-1]
    assert "10% chance to paralyze" in deliveries[-1]
    assert captured["callback"](players[0], "", "A B1") is False
    assert actions[0][0] == ("Thunderbolt", "B1")


@pytest.mark.parametrize("width", [24, 40, 78])
def test_compact_moves_preserve_letters_and_truthful_pp_reasons(width):
    """A blocked move with remaining PP must not be described as out of PP."""
    moves = [
        NS(name="Thunderbolt", pp=8),
        None,
        NS(name="Quick Attack", pp=0),
        NS(name="Double Team", pp=7),
    ]
    output = strip_ansi(render_move_gui(moves, total_width=width, unavailable={3: "UNAVAILABLE"}))
    assert "[A]" in output and "[B]" not in output and "[C]" in output and "[D]" in output
    assert "Quick Attack" in output and "Double Team" in output
    assert output.count("NO PP") == 1 and "UNAVAILABLE" in output
    assert "8/8" not in output
    assert max(map(len, output.splitlines())) <= width


def test_client_width_negotiation_is_used_when_character_has_no_override():
    """Narrow client protocol widths no longer get expanded to sixty columns."""
    player = trainer("Alex", 1)
    player.sessions = NS(all=lambda: [NS(protocol_flags={"SCREENWIDTH": {0: 42}})])
    assert get_battle_ui_width(player) == 40


def test_explicit_session_keeps_reserved_and_spent_mechanics_visible():
    """A redraw must use its supplied session even without captain ndb state."""
    session, players, _ = battle()
    session.battle.mega_pending = {"A": {"target": "A1"}}
    session.battle.z_pending = {"B": {"source": "secret", "target": "A1"}}
    session.battle.mega_used = {"B"}
    session.battle.z_used = {"A"}
    output = strip_ansi(render(session, players[0]))
    assert "Mega reserved for A1" in output
    assert "B: Mega Evolution use spent" in output
    assert "A: Z-Move use spent" in output
    assert "secret" not in output


def test_live_field_conditions_replace_stale_room_weather():
    """Moves change engine weather/terrain independently of initial room text."""
    session, players, _ = battle()
    session.state.roomweather = "sunnyday"
    session.battle.field = NS(
        weather="raindance",
        terrain="electricterrain",
        pseudo_weather={"trickroom": {"duration": 3}},
    )
    output = strip_ansi(render(session, players[0]))
    assert "raindance" in output and "electricterrain" in output
    assert "Trick Room (3)" in output and "sunnyday" not in output


@pytest.mark.parametrize("ended", [False, True])
def test_failed_or_finished_battle_does_not_offer_another_attack(ended):
    """Retained errors guide retry; a completed battle offers no new actions."""
    session, players, _ = battle()
    session.battle.battle_over = ended
    session.turn_state = {} if ended else {"error": "test save refusal"}
    output = strip_ansi(render(session, players[0]))
    assert "YOUR MOVE" not in output and "Fight:" not in output
    assert ("BATTLE OVER" if ended else "+battle/retry") in output


def test_fainted_controller_gets_replacement_guidance_instead_of_fight():
    """Do not describe an empty or fainted owned field as ready to attack."""
    session, players, mons = battle(multi=True)
    mons[0].hp = 0
    output = strip_ansi(render(session, players[0]))
    assert "YOUR MOVE" not in output
    assert "Fight:" not in output
    assert "Switch:" in output


@pytest.mark.parametrize(
    "move",
    [
        {"name": "Thunderbolt", "pp": 8},
        NS(name="Thunderbolt"),
    ],
)
def test_runtime_move_pp_does_not_invent_capacity_or_remaining(move):
    """Partial move snapshots are not authoritative boosted PP capacities."""
    output = strip_ansi(render_move_gui([move]))
    assert "8/8" not in output
    if not isinstance(move, dict):
        assert "15" not in output
        assert "--" in output


def test_move_details_are_ascii_safe_for_always_hit_status_moves():
    """Move detail placeholders must be readable in ASCII and SR clients."""
    from pokemon.ui.move_gui import render_move_details

    output = strip_ansi(render_move_details(NS(name="Double Team", pp=7), accessible=True))
    assert output.isascii()
    assert "Power: --" in output and "Accuracy: --" in output


def test_details_reject_an_empty_slot_without_closing_the_prompt(monkeypatch):
    """Physical move letters stay stable when an input contains a blank slot."""
    import sys
    from types import ModuleType
    from commands.player.battle_choice_prompts import attack_prompt

    session, players, mons = battle()
    mons[0].moves = [NS(name="Thunderbolt", pp=8), None, NS(name="Quick Attack", pp=0)]
    captured, messages = {}, []
    players[0].msg = messages.append
    choices = NS(
        actor=lambda _: ("A1", mons[0]),
        _check=lambda *_: None,
        legal_moves=lambda _: [NS(move=NS(key="thunderbolt", pp=8))],
        move=lambda *_args, **_kwargs: None,
    )
    session.choices_for = lambda _: choices
    evmenu = ModuleType("evennia.utils.evmenu")
    evmenu.get_input = lambda _caller, prompt, callback: captured.update(
        prompt=prompt, callback=callback
    )
    monkeypatch.setitem(sys.modules, "evennia.utils.evmenu", evmenu)
    attack_prompt(session, players[0], "")
    assert "[A]" in strip_ansi(captured["prompt"]) and "[C]" in strip_ansi(captured["prompt"])
    assert captured["callback"](players[0], "", "? B") is True
    assert "Move details:" in messages[-1]


def test_committed_messages_group_once_and_classic_viewers_keep_their_stream():
    """Buffer publication, not combat resolution, feeds the compact summary."""
    from pokemon.services.battle_rewards import BufferedMessages

    class Session(MessagingMixin):
        """Use the real session message path without database access."""

    compact, classic = trainer("Alex", 1), trainer("Casey", 2, battle_ui_style="pf1")
    messages = [[], []]
    compact.msg, classic.msg = messages[0].append, messages[1].append
    session = Session()
    session.trainers = [compact, classic]
    session._battle_ui_collecting = True
    session._battle_ui_pending_events = []
    buffer = BufferedMessages(session)
    buffer.msg("Pikachu used Thunderbolt!")
    buffer.msg("It's super effective!")
    assert session._battle_ui_pending_events == [] and messages == [[], []]
    buffer.publish()
    assert messages[0] == []
    assert messages[1] == session._battle_ui_pending_events
    text = BattleText(40)
    from pokemon.ui.compact_battle import BattleEventPresentation

    for event in session._battle_ui_pending_events:
        text.add(BattleEventPresentation.format(event))
    output = strip_ansi(text.render())
    assert output.count("Thunderbolt") == 1 and "super effective" in output


@pytest.mark.parametrize("finished", [False, True])
def test_turn_flow_delivers_compact_results_once_including_the_final_turn(finished):
    """Exercise turn collection, normal redraw and the terminal cleanup path."""
    from pokemon.battle.turn import TurnManager
    from pokemon.services.battle_rewards import BufferedMessages

    class Session(TurnManager, MessagingMixin):
        """Render the real turn flow with a committed transport-only engine."""

    source, players, _ = battle()
    session = Session()
    session.__dict__.update(source.__dict__)
    session.battle_id, session.turn_state = 1, {}
    session.trainers, session.observers = [players[0], players[2]], []
    messages = [[], []]
    players[0].msg, players[2].msg = messages[0].append, messages[1].append
    players[2].db.battle_ui_style = "classic_modern"
    session.notify = lambda text: None
    session._set_player_control = lambda enabled: None
    session._sync_active_battle_state = lambda: None
    session._persist_turn_state = lambda: None
    session.end = lambda: setattr(session, "ended", True)
    session.battle.turn_count = 3
    session.battle.battle_over = False
    session.battle.check_win_conditions = lambda: None
    for cell in session.data.turndata.positions.values():
        cell.removeDeclare = lambda: None

    def execute():
        """Publish through the same buffer used after persistent turn commit."""
        buffer = BufferedMessages(session)
        buffer.msg("Pikachu used Thunderbolt!")
        buffer.msg("It's super effective!")
        session.battle.turn_count += 1
        session.battle.battle_over = finished
        buffer.publish()

    session.battle.run_turn = execute
    session.run_turn()
    compact = strip_ansi("\n".join(messages[0]))
    classic = strip_ansi("\n".join(messages[1]))
    assert compact.count("Thunderbolt") == classic.count("Thunderbolt") == 1
    assert "LAST TURN" in compact and "LAST TURN" not in classic
    assert not session._battle_ui_collecting
    assert getattr(session, "ended", False) == finished
