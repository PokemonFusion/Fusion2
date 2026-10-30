"""Check real ANSI/HTML output without any database; optionally save a preview."""

import argparse
import html
import os
import re
import sys
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")

from django.conf import settings
from django.db.backends.base.base import BaseDatabaseWrapper

settings.DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}


def no_database(*args, **kwargs):
    """Refuse every database connection, including accidentally inherited settings."""
    raise AssertionError("Compact rendering must not connect to a database")


def main():
    """Render synthetic battle state through production parsers and public UI."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preview", type=Path)
    arguments = parser.parse_args()
    with patch.object(BaseDatabaseWrapper, "ensure_connection", no_database):
        import django

        django.setup()
        from evennia.utils.ansi import parse_ansi
        from evennia.utils.text2html import parse_html
        from pokemon.battle.battledata import Move, Pokemon
        from pokemon.battle.interface import display_battle_interface
        from pokemon.helpers.pokemon_helpers import get_max_hp
        from pokemon.services.pp_capacity import PPCapacity
        from utils.battle_display import strip_ansi

        moves = [Move(name) for name in ("thunderbolt", "quickattack", "thunderwave", "doubleteam")]
        for move, remaining in zip(moves, (8, 0, 15, 15)):
            move.pp = remaining
            move.max_pp = PPCapacity.for_move(move.name).base
        own = Pokemon("Pikachu", level=20, moves=moves)
        foe = Pokemon("Pidgeotto", level=18)
        for pokemon, percent in ((own, 70), (foe, 60)):
            pokemon.max_hp = get_max_hp(pokemon)
            pokemon.hp = pokemon.max_hp * percent // 100
        own.status = "par"
        own._pf2_active_fusion = True
        own.boosts = {"atk": 2}
        own.volatiles = {"confusion": True}
        reserves = [Pokemon(name, level=20) for name in ("Eevee", "Bulbasaur", "Squirtle")]
        player = NS(
            name="Alex",
            key="Alex",
            pk=1,
            active_pokemon=own,
            team=[*reserves, own],
            db=NS(battle_ascii_symbols=False),
            ndb=NS(),
        )
        wild = NS(
            name="Wild", key="Wild", pk=None, active_pokemon=foe, team=[foe], db=NS(), ndb=NS()
        )
        state = NS(
            turn=3,
            encounter_kind="wild",
            declare={},
            multi={},
            flee_allowed=True,
            roomweather="clear",
            field="-",
        )
        session = NS(
            captainA=player,
            captainB=wild,
            teamA=[player],
            teamB=[wild],
            state=state,
            data=NS(turndata=NS(positions={"A1": NS(pokemon=own), "B1": NS(pokemon=foe)})),
            battle=NS(
                participants=[
                    NS(player=player, active=[own], pokemons=player.team),
                    NS(player=wild, active=[foe], pokemons=[foe]),
                ]
            ),
            _battle_ui_last_events=("Alex used Thunderbolt!", "It's super effective!"),
        )
        count = 0
        for width in (24, 40, 60, 78, 100):
            for mode in ("unicode", "ascii", "sr"):
                player.db.ui_mode = mode
                player.db.battle_ascii_symbols = mode == "ascii"
                raw = display_battle_interface(
                    player, wild, state, session=session, viewer=player, total_width=width
                )
                visible = parse_ansi(raw, strip_ansi=True)
                parsed_html = parse_html(raw)
                html_text = re.sub(r"<br\s*/?>", "\n", parsed_html)
                html_text = html.unescape(re.sub(r"<[^>]+>", "", html_text)).replace("\xa0", " ")
                assert visible == strip_ansi(raw) == html_text, (width, mode)
                assert max(map(len, visible.splitlines())) <= width, (width, mode)
                assert f"{own.hp}/{own.max_hp}" in visible
                assert f"{foe.hp}/{foe.max_hp}" not in visible
                assert "A1" in visible and "B1" in visible
                assert "[YOU / FUSION]" in visible
                assert "NO PP" in visible and "UNAVAILABLE" not in visible
                if mode == "ascii":
                    assert visible.isascii()
                if mode == "sr":
                    assert "----" not in visible and "█" not in visible and "|" not in raw
                count += 1

        if arguments.preview:
            player.db.ui_mode = "fancy"
            player.db.battle_ascii_symbols = False
            raw = display_battle_interface(
                player, wild, state, session=session, viewer=player, total_width=78
            )
            output = arguments.preview.resolve()
            output.mkdir(parents=True, exist_ok=True)
            (output / "compact-battle.txt").write_text(
                parse_ansi(raw, strip_ansi=True), encoding="utf-8"
            )
            palette = (
                "#000000",
                "#800000",
                "#008000",
                "#808000",
                "#000080",
                "#800080",
                "#008080",
                "#c0c0c0",
                "#808080",
                "#ff0000",
                "#00ff00",
                "#ffff00",
                "#0000ff",
                "#ff00ff",
                "#00ffff",
                "#ffffff",
            )
            colors = "".join(
                f".color-{index:03d}{{color:{color}}}" for index, color in enumerate(palette)
            )
            document = (
                "<!doctype html><meta charset='utf-8'><title>Compact battle - local fixture preview</title>"
                "<style>body{background:#0a1210;color:#e6eee8;margin:0;padding:32px;}"
                ".preview{width:max-content;background:#101b18;border:1px solid #38594b;padding:26px 32px;}"
                "pre{font:18px/1.42 Consolas,'DejaVu Sans Mono',monospace;margin:0;white-space:pre;}"
                ".note{font:13px sans-serif;color:#9bb4a6;margin-bottom:18px;}"
                + colors
                + "</style>"
                "<div class='note'>LOCAL RENDERED PREVIEW / SYNTHETIC BATTLE FIXTURE</div>"
                "<div class='preview'><pre>" + parse_html(raw) + "</pre></div>"
            )
            (output / "compact-battle.html").write_text(document, encoding="utf-8")
            print(f"Preview saved to {output}")
        print(
            f"Compact real rendering: {count} width/mode cases passed; ANSI and HTML agree; no database access."
        )


if __name__ == "__main__":
    main()
