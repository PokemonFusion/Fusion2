"""Exercise real battle UI commands with synthetic battlers and no database."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import random
import sys
from types import SimpleNamespace as NS
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")

from django.conf import settings
from django.db.backends.base.base import BaseDatabaseWrapper

settings.DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}


def refuse_database(*_args, **_kwargs):
    """Refuse inherited game databases as well as the uninitialized memory DB."""
    raise AssertionError("UI command checks must not access a database")


class PresentationPlayer:
    """Capture an ordinary controller's transport and presentation preferences."""

    def __init__(self, name, identifier):
        self.name = self.key = name
        self.id = self.pk = identifier
        self.db, self.ndb = NS(battle_control=True), NS()
        self.messages = []

    def msg(self, text, **_kwargs):
        """Capture production command output instead of opening a game socket."""
        self.messages.append(str(text))


def fixture(*, doubles=False, multi=False):
    """Build real engine, position and choice objects without owned SQL rows."""
    from pokemon.battle.battledata import BattleData, Move, Pokemon, Team, TurnData, PositionData
    from pokemon.battle.battleinstance import BattleSession
    from pokemon.battle.engine import Battle, BattleParticipant, BattleType
    from pokemon.battle.logic import BattleLogic
    from pokemon.battle.state import BattleState
    from pokemon.helpers.pokemon_helpers import get_max_hp

    players = [
        PresentationPlayer(name, index + 1)
        for index, name in enumerate(("Alex", "Blair", "Casey", "Dee"))
    ]
    parts = []
    for index, player in enumerate(players if multi else [players[0], players[2]]):
        side = ("A" if index < 2 else "B") if multi else "AB"[index]
        roster = []
        for slot in range(2 if doubles else 1):
            moves = [
                Move(name) for name in ("thunderbolt", "quickattack", "thunderwave", "doubleteam")
            ]
            for move, pp in zip(moves, (8, 5, 0, 7)):
                move.pp = pp
            pokemon = Pokemon("Pikachu", level=30, moves=moves)
            pokemon.model_id = f"encounter:ui-{index}-{slot}"
            pokemon.max_hp = get_max_hp(pokemon)
            pokemon.hp = pokemon.max_hp - index - slot - 1
            roster.append(pokemon)
        player.team, player.active_pokemon = roster, roster[0]
        part = BattleParticipant(
            player.name, roster, player=player, max_active=len(roster), team=side
        )
        part.active[:] = roster
        part._active_slots = dict(enumerate(roster))
        if multi:
            part.field_position = side + str(index % 2 + 1)
        parts.append(part)
    engine = Battle(BattleType.PVP, parts, rng=random.Random(17))
    data = BattleData(
        *[
            Team(side, [mon for part in parts if part.team == side for mon in part.pokemons])
            for side in "AB"
        ]
    )
    data.turndata = TurnData(data.teams, teamslots=2 if doubles or multi else 1)
    if multi:
        data.turndata.positions = {
            part.field_position: PositionData(part.active[0]) for part in parts
        }
    state = BattleState.from_battle_data(data, ai_type="PVP")
    session = BattleSession.__new__(BattleSession)
    session.logic = BattleLogic(engine, data, state)
    session.teamA = [part.player for part in parts if part.team == "A"]
    session.teamB = [part.player for part in parts if part.team == "B"]
    session.trainers = session.teamA + session.teamB
    session.observers, session.turn_state = [], {}
    session.ndb = NS(watchers_live=[])
    session.battle_id = 701
    session.storage = NS(set=lambda *_args: None)
    session.maybe_run_turn = lambda **_kwargs: None
    for player in session.trainers:
        player.ndb.battle_instance = session
    return session, players


def main():
    """Exercise actual command parsing, selectors, ownership and safe redraws."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path)
    arguments = parser.parse_args()
    transcript = []
    with patch.object(BaseDatabaseWrapper, "ensure_connection", refuse_database):
        import django

        django.setup()
        import evennia
        from evennia.commands.command import Command
        from evennia.commands.cmdset import CmdSet

        # Expose real flat API classes without bootstrapping server services.
        evennia.Command, evennia.CmdSet = Command, CmdSet
        from commands.player.cmd_battle_attack import CmdBattleAttack
        from commands.player.cmd_battleuistyle import CmdBattleUiStyle
        from commands.player.cmd_showbattle import CmdShowBattle
        from commands.player.cmd_uimode import CmdUiMode
        from pokemon.battle.interface import display_battle_interface
        from utils.battle_display import strip_ansi

        count = 0

        def command(kind, player, args=""):
            """Run the production command; no permission elevation is supplied."""
            nonlocal count
            instance = kind()
            start = len(player.messages)
            instance.caller, instance.args, instance.switches = player, args, []
            if kind is CmdBattleAttack:
                instance.parse()
            instance.func()
            count += 1
            transcript.append(
                {
                    "route": "command",
                    "player": player.name,
                    "input": kind.key + (" " + args if args else ""),
                    "messages": player.messages[start:],
                }
            )
            return strip_ansi(player.messages[-1])

        prompts = []

        def capture_input(player, prompt, callback, **_kwargs):
            """Replace only interactive transport; keep the real input callback."""
            player.msg(prompt)

            def reply(caller, original_prompt, text):
                """Retain exact interactive inputs and their resulting messages."""
                start = len(caller.messages)
                result = callback(caller, original_prompt, text)
                transcript.append(
                    {
                        "route": "selector",
                        "player": caller.name,
                        "input": text,
                        "keep_prompt": result,
                        "messages": caller.messages[start:],
                    }
                )
                return result

            prompts.append((player, reply))

        with (
            patch("evennia.utils.evmenu.get_input", capture_input),
            patch(
                "commands.player.cmd_battle_attack.get_system", return_value=NS(battle_manager=None)
            ),
        ):
            session, players = fixture()
            own, foe = (
                session.battle.participants[0].active[0],
                session.battle.participants[1].active[0],
            )
            output = command(CmdShowBattle, players[0])
            assert "POKEMON FUSION 2" in output and f"{own.hp}/{own.max_hp}" in output
            assert f"{foe.hp}/{foe.max_hp}" not in output
            for style in ("legacy", "classic_modern", "pf1"):
                command(CmdBattleUiStyle, players[0], style)
                assert players[0].db.battle_ui_style == style
                assert "POKEMON FUSION 2" not in command(CmdShowBattle, players[0])
            command(CmdUiMode, players[0], "screenreader")
            output = command(CmdShowBattle, players[0])
            assert "HP: " in output and "----" not in output and "|" not in players[0].messages[-1]
            command(CmdUiMode, players[0], "ascii")
            command(CmdBattleUiStyle, players[0], "default")
            assert command(CmdShowBattle, players[0]).isascii()
            command(CmdUiMode, players[0], "unicode")
            assert "█" in command(CmdShowBattle, players[0])
            own.moves[1].disabled = True
            output = command(CmdBattleAttack, players[0])
            assert "UNAVAILABLE" in output and "NO PP" in output, output
            player, callback = prompts[-1]
            assert callback(player, "", "?") is True and session.state.declare == {}
            assert "Move details:" in player.messages[-1]
            assert callback(player, "", "? A") is True and session.state.declare == {}
            assert "Power: 90" in strip_ansi(player.messages[-1])
            assert callback(player, "", "cancel") is False and session.state.declare == {}
            command(CmdBattleAttack, player, "B B1")
            assert session.state.declare == {} and "cannot use" in player.messages[-1]
            command(CmdBattleAttack, player, "C B1")
            assert session.state.declare == {} and "cannot use" in player.messages[-1]
            command(CmdBattleAttack, player)
            player, callback = prompts[-1]
            callback(player, "", "A B1")
            assert (
                session.state.declare["A1"]["move"].lower() == "thunderbolt"
            ), session.state.declare
            assert own.moves[0].pp == 8
            assert "ACTION QUEUED" in command(CmdShowBattle, player)
            before = dict(session.state.declare)
            command(CmdBattleAttack, player, "A B1")
            assert session.state.declare == before and "already" in player.messages[-1]

            session, players = fixture(doubles=True)
            assert "Choose your acting slot" in command(CmdBattleAttack, players[0])
            command(CmdBattleAttack, players[0], "A2")
            player, callback = prompts[-1]
            callback(player, "", "A B1")
            assert set(session.state.declare) == {"A2"}
            output = command(CmdShowBattle, player)
            assert "Your slots: A1" in output and all(
                label in output for label in ("A1", "A2", "B1", "B2")
            )
            command(CmdBattleAttack, player, "A1")
            player, callback = prompts[-1]
            session.battle.turn_count += 1
            callback(player, "", "? A")
            assert "earlier turn" in player.messages[-1] and set(session.state.declare) == {"A2"}

            session, players = fixture()
            for move in session.battle.participants[0].active[0].moves:
                move.pp = 0
            output = command(CmdBattleAttack, players[0])
            assert "Struggle" in output and "NO PP" not in output
            player, callback = prompts[-1]
            callback(player, "", "A B1")
            assert session.state.declare["A1"]["move"].lower() == "struggle"

            session, players = fixture(multi=True)
            for player in players:
                output = command(CmdShowBattle, player)
                owned = next(
                    part.active[0] for part in session.battle.participants if part.player is player
                )
                assert f"{owned.hp}/{owned.max_hp}" in output
                for part in session.battle.participants:
                    mon = part.active[0]
                    if part.player is not player:
                        assert f"{mon.hp}/{mon.max_hp}" not in output
            watcher = PresentationPlayer("Observer", 99)
            with patch("commands.player.cmd_showbattle.search_object", return_value=[players[0]]):
                output = command(CmdShowBattle, watcher, "Alex")
            assert "WATCHING" in output and "Fight:" not in output
            assert all(
                f"{part.active[0].hp}/{part.active[0].max_hp}" not in output
                for part in session.battle.participants
            )
            before = session.logic.to_dict()
            rng = session.battle.rng.getstate()
            for width in (24, 40, 78):
                output = display_battle_interface(
                    session.captainA,
                    session.captainB,
                    session.state,
                    viewer=players[1],
                    session=session,
                    total_width=width,
                )
                assert max(map(len, strip_ansi(output).splitlines())) <= width
            assert session.logic.to_dict() == before and session.battle.rng.getstate() == rng
        if arguments.evidence:
            with arguments.evidence.open("x", encoding="utf-8") as output:
                json.dump(
                    {
                        "commands": count,
                        "selector_inputs": len(transcript) - count,
                        "limit": "Synthetic controllers, captured transport and session registry; real commands/engine; no SQL or socket",
                        "transcript": transcript,
                    },
                    output,
                    indent=2,
                    ensure_ascii=False,
                )
                output.write("\n")
        print(
            f"Compact player flow: {count} production command inputs passed; "
            f"{len(transcript) - count} selector replies; real choices/engine; no database or socket."
        )


if __name__ == "__main__":
    main()
