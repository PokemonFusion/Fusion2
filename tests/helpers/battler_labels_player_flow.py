"""Check same-named targets through production battle commands and the engine."""

from __future__ import annotations

from collections import Counter
from unittest.mock import patch

from compact_battle_player_flow import (
    BaseDatabaseWrapper, NS, fixture, refuse_database,
)


def main():
    """Exercise real selectors, declarations, resolution and rendered results."""
    with patch.object(BaseDatabaseWrapper, "ensure_connection", refuse_database):
        import django

        django.setup()
        import evennia
        from evennia.commands.command import Command
        from evennia.commands.cmdset import CmdSet

        evennia.Command, evennia.CmdSet = Command, CmdSet
        from commands.player.cmd_battle_attack import CmdBattleAttack
        from pokemon.battle.interface import display_battle_interface
        from pokemon.battle.labels import BattlerLabels
        from utils.battle_display import strip_ansi

        prompts = []

        def capture(player, prompt, callback):
            """Replace only interactive transport, retaining the real callback."""
            prompts.append((player, strip_ansi(prompt), callback))

        def attack(player, args):
            """Send the same arguments used by the ordinary +attack command."""
            cmd = CmdBattleAttack()
            cmd.caller, cmd.args, cmd.switches = player, args, []
            cmd.parse()
            cmd.func()

        with (
            patch("evennia.utils.evmenu.get_input", capture),
            patch("commands.player.cmd_battle_attack.get_system",
                  return_value=NS(battle_manager=None)),
        ):
            for mode in ("doubles", "multi", "singles"):
                session, players = fixture(doubles=mode == "doubles", multi=mode == "multi")
                battle = session.battle
                logs = []
                battle.log_action = logs.append
                cells = session.data.turndata.positions
                for cell in cells.values():
                    cell.pokemon.name = "Echo"
                if mode == "multi":
                    cells["A1"].pokemon._pf2_active_fusion = True
                names = BattlerLabels(battle)
                originals = [(cell.pokemon, cell.pokemon.name, cell.pokemon.model_id)
                             for cell in cells.values()]
                targets = {"A1": "B2", "A2": "B1", "B1": "A2", "B2": "A1"}
                if mode == "singles":
                    targets = {"A1": "B1", "B1": "A1"}
                for position, cell in cells.items():
                    part = next(part for part in battle.participants
                                if any(mon is cell.pokemon for mon in part.active))
                    attack(part.player, position)
                    player, prompt, callback = prompts[-1]
                    if mode != "singles":
                        assert all(f"Echo ({slot})" in prompt for slot in cells), prompt
                    callback(player, prompt, "A " + targets[position])
                    assert session.state.declare[position]["target"] == targets[position]
                    assert cell.pokemon.moves[0].pp == 8  # Selection spends nothing.
                battle.run_move()
                expected_messages = Counter()
                for position, target in targets.items():
                    user, foe = cells[position].pokemon, cells[target].pokemon
                    expected = f"{names.name(user)} uses Thunderbolt on {names.name(foe)} and deals "
                    expected_messages[expected] += 1
                    assert user.moves[0].pp == 7
                for expected, count in expected_messages.items():
                    assert sum(expected in line for line in logs) == count, logs
                assert all((mon.name, mon.model_id) == (name, ref)
                           for mon, name, ref in originals)
                session._battle_ui_last_events = logs
                for viewer in session.trainers:
                    for accessible in (False, True):
                        viewer.db.ui_mode = "screenreader" if accessible else "unicode"
                        output = strip_ansi(display_battle_interface(
                            session.captainA, session.captainB, session.state,
                            viewer=viewer, session=session, total_width=78))
                        if mode != "singles":
                            assert all(f"Echo ({slot})" in output for slot in cells), output
                            assert "Echo (Pikachu) (B2)" in output, output
                        if mode == "multi":
                            assert "Alex (Pikachu) (A1)" in output, output
                            assert "FUSION" in output
                print(f"{mode}: matching-name selectors and resolved results passed")

            session, _players = fixture(doubles=True)
            battle = session.battle
            logs = []
            battle.log_action = logs.append
            part = battle.participants[0]
            user = part.active[1]
            user.name = "Echo"
            attack(part.player, "A2 D")  # Normal self-target Double Team.
            action = part.pending_action
            battle.use_move(action)
            assert any("Echo (A2) used Double Team!" in line for line in logs), logs
            assert any("Echo (A2)'s evasiveness rose!" in line for line in logs), logs
            logs.clear()
            battle.announce_status_change(user, "brn")
            battle.on_faint(user)
            assert all("Echo (A2)" in line for line in logs), logs
            assert any("fainted" in line for line in logs), logs
            print("self-target, status and faint messages retain the exact field position")


if __name__ == "__main__":
    main()
