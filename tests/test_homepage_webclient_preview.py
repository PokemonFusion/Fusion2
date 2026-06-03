import importlib
import sys
import types
from pathlib import Path


def _import_homepage_index(monkeypatch):
    evennia = types.ModuleType("evennia")
    evennia_web = types.ModuleType("evennia.web")
    evennia_website = types.ModuleType("evennia.web.website")
    evennia_views = types.ModuleType("evennia.web.website.views")
    evennia_index = types.ModuleType("evennia.web.website.views.index")

    class EvenniaIndexView:
        pass

    evennia_index.EvenniaIndexView = EvenniaIndexView
    evennia.web = evennia_web
    evennia_web.website = evennia_website
    evennia_website.views = evennia_views
    evennia_views.index = evennia_index

    monkeypatch.setitem(sys.modules, "evennia", evennia)
    monkeypatch.setitem(sys.modules, "evennia.web", evennia_web)
    monkeypatch.setitem(sys.modules, "evennia.web.website", evennia_website)
    monkeypatch.setitem(sys.modules, "evennia.web.website.views", evennia_views)
    monkeypatch.setitem(sys.modules, "evennia.web.website.views.index", evennia_index)
    module_path = Path(__file__).resolve().parents[1] / "web" / "website" / "views" / "index.py"
    spec = importlib.util.spec_from_file_location("homepage_index_under_test", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None

    spec.loader.exec_module(module)
    return module


def _flatten_preview(lines):
    return "\n".join("".join(segment["text"] for segment in line) for line in lines)


def test_webclient_preview_uses_splash_excerpt_without_login_instructions(monkeypatch):
    index = _import_homepage_index(monkeypatch)
    screen = "\n".join(
        (
            "|b==============================================================|n",
            "|rPOKEMON|n",
            "|wFUSION|n",
            " |yBest Viewed in UTF8 - Unicode|n",
            " Welcome to |gPokemon Fusion 2|n, Powered by Evennia 6.0.0!",
            "",
            " If you have an existing account, connect to it by typing:",
            "      |wconnect <username> <password>|n",
        )
    )

    lines = index.build_webclient_preview_lines(screen)
    text = _flatten_preview(lines)

    assert "POKEMON" in text
    assert "FUSION" in text
    assert "Welcome to Pokemon Fusion 2, Powered by Evennia 6.0.0!" in text
    assert "connect <username>" not in text
    assert any(
        segment["text"] == "Pokemon Fusion 2" and segment["class"] == "ansi-green"
        for line in lines
        for segment in line
    )


def test_webclient_preview_commands_match_real_topbar(monkeypatch):
    index = _import_homepage_index(monkeypatch)

    assert index.WEBCLIENT_PREVIEW_COMMANDS == (
        "look",
        "map",
        "party",
        "sheet",
        "inventory",
        "help",
    )
