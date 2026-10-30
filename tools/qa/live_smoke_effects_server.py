"""Guarded QA preparation and read-only effect observations for localhost tests."""

import hashlib
import importlib.util
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("smoke_effect_guarded_base", REPO / "tools/qa/live_dex_server.py")
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)


def observe(path, result):
    """Read effect state without invoking or replacing any mechanic callback."""
    from pokemon.models.core import OwnedPokemon

    _, _, _, players, trainers = base._pilot.guarded_context(path)
    for label, trainer in trainers.items():
        owned = {str(pokemon.pk): pokemon for pokemon in OwnedPokemon.objects.filter(trainer=trainer)}
        for item in result["players"][label]["pokemon"]:
            item["friendship"] = owned[item["id"]].friendship
    session = base._pilot.active_session(players)
    last = players["staff"].ndb.live_dex_last_observed
    battle = session.battle if session else last.get("battle") if last else None
    frame = result.get("battle") or result.get("ended_battle")
    if battle is not None and frame:
        frame["called_moves"] = list(getattr(battle, "called_moves", []) or [])
        for participant in battle.participants:
            side = frame["sides"][participant.team]
            side["hazards"] = list(getattr(participant.side, "hazards", {}) or {})
            side["screens"] = list(getattr(participant.side, "screens", {}) or {})
            for collection, live in (("active", participant.active), ("pokemon", participant.pokemons)):
                for observed, pokemon in zip(side[collection], live):
                    move = getattr(pokemon, "last_move", None)
                    observed["executed_move"] = {name: getattr(move, name, None) for name in ("name", "type", "category", "power", "magnitude", "heal", "pp")}
                    observed["effect_state"] = {name: getattr(pokemon, name, None) for name in ("stockpile_layers", "happiness", "friendship", "weightkg")}
                    stockpile = getattr(pokemon, "volatiles", {}).get("stockpile", {})
                    if isinstance(stockpile, dict) and "layers" in stockpile:
                        observed["effect_state"]["stockpile_layers"] = stockpile["layers"]
    result["effect_observer_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    return result


def dispatch(path, action, payload=None):
    """Allow canonical pre-battle friendship/PP only on freshly guarded QA rows."""
    payload = payload or {}
    fixture = payload.get("effect_fixture", {}) if action == "setup" else {}
    assert set(fixture) <= {"friendship", "move_pp"}
    result = base.dispatch(path, action, payload)
    if fixture:
        from django.db import transaction
        from pokemon.models.core import OwnedPokemon

        _, _, _, players, trainers = base._pilot.guarded_context(path)
        assert base._pilot.active_session(players) is None
        with transaction.atomic():
            for label in set(fixture.get("friendship", {})) | set(fixture.get("move_pp", {})):
                assert label in {"a", "b"}
                owned = list(OwnedPokemon.objects.filter(trainer=trainers[label]).order_by("created_at"))
                for index, friendship in fixture.get("friendship", {}).get(label, {}).items():
                    assert isinstance(friendship, int) and 0 <= friendship <= 255
                    pokemon = owned[int(index)]
                    pokemon.friendship = friendship
                    pokemon.save(update_fields=["friendship"])
                for index, moves in fixture.get("move_pp", {}).get(label, {}).items():
                    for name, pp in moves.items():
                        normalize = lambda text: "".join(char for char in text.casefold() if char.isalnum())
                        matches = [slot for slot in owned[int(index)].activemoveslot_set.select_related("move") if normalize(slot.move.name) == normalize(name)]
                        assert len(matches) == 1, "Prepared PP fixture must identify exactly one normalized moveslot."
                        slot = matches[0]
                        assert isinstance(pp, int) and 0 <= pp <= slot.current_pp
                        slot.current_pp = pp
                        slot.save(update_fields=["current_pp"])
        result = base.snapshot(path)
    return observe(path, result) if action in {"snapshot", "setup"} else result
