"""Explicitly scoped staff setup/observation for the local logged-in pilot.

Loaded into the running server by the pilot's own staff session. This module
does not install commands, patch battle mechanics, or change global RNG state.
"""

import json
import random
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def load_manifest(path):
    """Reject paths outside the local artifact directory and invalid manifests."""
    path = Path(path).resolve()
    if not path.is_relative_to(REPO / ".codex-artifacts"):
        raise ValueError("Manifest must be inside this checkout's .codex-artifacts.")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not data.get("tag", "").startswith("battle-pilot-"):
        raise ValueError("Invalid pilot ownership tag.")
    if set(data.get("players", {})) != {"a", "b", "staff"}:
        raise ValueError("Exactly two players and one staff fixture are required.")
    ids = [item["id"] for item in data["players"].values()]
    if len(set(ids)) != 3 or min(ids) <= data["baseline_max_object_id"]:
        raise ValueError("Fixture IDs must be distinct and newer than the baseline.")
    return path, data


def guarded_context(path):
    """Resolve only tagged, newly created QA characters and their private room."""
    from django.db import connection
    from evennia.objects.models import ObjectDB

    from pokemon.models.trainer import Trainer

    path, data = load_manifest(path)
    with connection.cursor() as cursor:
        cursor.execute("SELECT host(inet_server_addr()), current_database()")
        address, database = cursor.fetchone()
    if address not in (None, "127.0.0.1", "::1") or database != data["database"]:
        raise RuntimeError("Refusing a non-loopback or different game database.")
    room = ObjectDB.objects.get(pk=data["room_id"])
    if room.pk <= data["baseline_max_object_id"] or room.db.battle_pilot_tag != data["tag"]:
        raise RuntimeError("Private room ownership check failed.")
    players, trainers = {}, {}
    for label, identity in data["players"].items():
        player = ObjectDB.objects.get(pk=identity["id"], db_key=identity["name"])
        if (player.db.battle_pilot_tag != data["tag"]
                or player.db_account_id != identity["account_id"]
                or player.home != room or player.location != room):
            raise RuntimeError("QA character identity/location check failed.")
        if label != "staff" and (player.account.is_superuser
                                  or set(str(p).lower() for p in player.permissions.all()) != {"player"}
                                  or set(str(p).lower() for p in player.account.permissions.all()) != {"player"}):
            raise RuntimeError("Battling accounts must retain ordinary Player permissions.")
        players[label] = player
        if label != "staff":
            trainers[label] = Trainer.objects.get(pk=identity["trainer_id"], user=player)
    allowed = {player.pk for player in players.values()}
    if any(obj.pk not in allowed for obj in room.contents):
        raise RuntimeError("A non-QA object entered the private room; stop testing.")
    return path, data, room, players, trainers


def active_session(players):
    """Return a QA-only session, refusing any participant from another account."""
    sessions = []
    for label in ("a", "b"):
        inst = players[label].ndb.battle_instance
        if inst is not None and inst not in sessions:
            sessions.append(inst)
    allowed = {players[label].pk for label in ("a", "b")}
    for inst in sessions:
        for participant in getattr(inst.battle, "participants", []):
            owner = getattr(participant, "player", None)
            if getattr(owner, "pk", None) is not None and owner.pk not in allowed:
                raise RuntimeError("Refusing to touch a battle containing a non-QA player.")
    if len(sessions) > 1:
        raise RuntimeError("Expected at most one pilot battle.")
    return sessions[0] if sessions else None


def mon_snapshot(mon):
    """Read live battle values without changing the Pokemon."""
    moves = []
    for move in getattr(mon, "moves", []):
        moves.append({"name": getattr(move, "name", str(move)),
                      "pp": getattr(move, "current_pp", None)})
    slots = getattr(mon, "activemoveslot_set", None)
    if slots is not None:
        try:
            moves = [{"name": getattr(slot.move, "name", str(slot.move)), "pp": slot.current_pp}
                     for slot in slots.all().order_by("slot")]
        except (AttributeError, TypeError):
            pass
    return {"id": str(getattr(mon, "model_id", "")), "species": str(getattr(mon, "species", "")),
            "name": mon.name, "hp": mon.hp, "max_hp": mon.max_hp,
            "status": getattr(mon, "status", None), "types": list(getattr(mon, "types", [])),
            "ability": str(getattr(getattr(mon, "ability", None), "name", getattr(mon, "ability", ""))),
            "ability_state": dict(getattr(mon, "ability_state", {}) or {}),
            "boosts": dict(getattr(mon, "boosts", {}) or {}),
            "volatiles": list(getattr(mon, "volatiles", {}) or {}), "moves": moves,
            "diagnostic_flags": {key: value for key, value in (getattr(mon, "tempvals", {}) or {}).items()
                                 if isinstance(value, (str, int, float, bool, type(None)))}}


def snapshot(path):
    """Observe both ordinary players, real stored Pokemon and live battle state."""
    from pokemon.battle.engine import Battle
    from pokemon.dex.entities import Ability
    from pokemon.models.core import OwnedPokemon
    from pokemon.models.storage import PokemonPlacement

    _, data, room, players, trainers = guarded_context(path)
    inst = active_session(players)
    result = {"players": {}, "battle": None, "room_battles": list(room.db.battles or []),
              "runtime": {"charge_phase_fix_loaded": any(isinstance(value, str) and "began charging" in value
                                                        for value in Battle.use_move.__code__.co_consts),
                          "ability_condition_adapter_loaded": "condition" in Ability.call.__code__.co_consts}}
    for label in ("a", "b"):
        player, trainer = players[label], trainers[label]
        result["players"][label] = {
            "id": player.pk, "ordinary": not player.account.is_superuser,
            "battle_id": player.db.battle_id, "battle_lock": bool(player.db.battle_lock),
            "battle_control": bool(player.db.battle_control),
            "pokemon": [{"id": str(mon.pk), "species": mon.species, "hp": mon.current_hp,
                         "status": mon.status, "ability": mon.ability,
                         "moves": list(mon.activemoveslot_set.order_by("slot").values("move__name", "current_pp"))}
                        for mon in OwnedPokemon.objects.filter(trainer=trainer).order_by("created_at")],
            "placements": list(PokemonPlacement.objects.filter(pokemon__trainer=trainer).values("pokemon_id", "slot", "location_type")),
            "inventory": list(trainer.inventory.order_by("pk").values("item_name", "quantity")),
        }
    if inst and inst.battle:
        result["battle"] = {"id": inst.battle_id, "turn": inst.battle.turn_count,
                            "type": str(getattr(inst.battle, "type", getattr(inst.battle, "battle_type", ""))), "sides": {}}
        field = getattr(inst.battle, "field", None)
        result["battle"]["field"] = {"weather": str(getattr(field, "weather", "")),
                                      "terrain": str(getattr(field, "terrain", "")),
                                      "pseudo_weather": list(getattr(field, "pseudo_weather", {}) or {})}
        for part in inst.battle.participants:
            result["battle"]["sides"][part.team] = {
                "active": [mon_snapshot(mon) for mon in part.active],
                "pokemon": [mon_snapshot(mon) for mon in part.pokemons],
            }
    return result


def setup(path, payload):
    """Replace only Pokemon belonging to the two newly created pilot trainers."""
    from django.db import transaction

    from pokemon.helpers.pokemon_helpers import create_owned_pokemon, get_max_hp
    from pokemon.models.core import OwnedPokemon
    from pokemon.models.storage import UserStorage

    path, data, room, players, trainers = guarded_context(path)
    if active_session(players) or room.db.battles or room.db.pvp_requests:
        raise RuntimeError("Previous battle/request must finish before replacing fixtures.")
    for label in ("a", "b"):
        if players[label].db.battle_lock or players[label].db.battle_id:
            raise RuntimeError("Battle locks remain; refusing fixture replacement.")
    with transaction.atomic():
        for label in ("a", "b"):
            trainer = trainers[label]
            # Every row owned by these trainers was created after the baseline.
            # The manifest pins exact new trainer/character identities above.
            OwnedPokemon.objects.filter(trainer=trainer).delete()
            players[label].db.pending_capture_nicknames = []
            trainer.inventory.all().delete()
            storage = UserStorage.objects.get(user=players[label])
            for spec in payload[label]:
                fraction = float(spec["hp_fraction"])
                if not 0 <= fraction <= 1:
                    raise ValueError("QA HP fraction must be between zero and one.")
                mon = create_owned_pokemon(
                    spec["species"], trainer, spec.get("level", 50), ability=spec["ability"],
                    gender=spec.get("gender", "M"), nature="Hardy", ivs=[0] * 6, evs=[0] * 6,
                    active_move_names=spec["moves"], flags=[data["tag"]], held_item=spec["item"],
                )
                mon.current_hp = max(1, int(get_max_hp(mon) * fraction)) if fraction else 0
                mon.save(update_fields=["current_hp"])
                if spec.get("status"):
                    mon.status = spec["status"]
                    mon.save(update_fields=["status"])
                actual = list(mon.activemoveslot_set.order_by("slot").values_list("move__name", flat=True))
                normalize = lambda name: "".join(char for char in name.casefold() if char.isalnum())
                if [normalize(name) for name in actual] != [normalize(name) for name in spec["moves"]]:
                    raise RuntimeError(f"Prepared moves differ for {spec['species']}: {actual}")
            if len(storage.get_party()) != len(payload[label]):
                raise RuntimeError("Canonical party placement failed.")
        for name, quantity in payload.get("inventory", {}).items():
            trainers["a"].add_item(name, quantity)
    return snapshot(path)


def seed(path, payload):
    """Assign a private RNG to this QA battle, without reseeding shared randomness."""
    _, _, _, players, _ = guarded_context(path)
    inst = active_session(players)
    if inst is None or not inst.battle:
        raise RuntimeError("No QA battle to seed.")
    rng = random.Random(payload["seed"])
    inst.rng = rng
    inst.ndb.rng = rng
    inst.battle.rng = rng
    return {"battle_id": inst.battle_id, "seed": payload["seed"], "global_rng_changed": False}


def finish(path):
    """End only this pilot's battle, after the runner attempted normal concession."""
    _, _, room, players, _ = guarded_context(path)
    inst = active_session(players)
    forced = bool(inst and inst.battle)
    if forced:
        inst.end()
    for label in ("a", "b"):
        player = players[label]
        if player.db.pvp_locked:
            from pokemon.battle.pvp import remove_request
            remove_request(player)
    if room.db.battles or room.db.pvp_requests:
        raise RuntimeError("Private room retains unresolved battle state.")
    result = snapshot(path)
    if any(p["battle_lock"] or p["battle_id"] for p in result["players"].values()):
        raise RuntimeError("QA battle locks did not clear.")
    result["staff_cleanup_required"] = forced
    return result


def disable_accounts(path):
    """Invalidate QA accounts in the live process, updating its identity cache."""
    from django.db import transaction

    _, data, room, players, _ = guarded_context(path)
    if active_session(players) or room.db.battles or room.db.pvp_requests:
        raise RuntimeError("Finish QA battles before disabling accounts.")
    identities = []
    with transaction.atomic():
        for player in players.values():
            account = player.account
            if account.pk <= data["baseline_max_account_id"]:
                raise RuntimeError("Refusing to disable a pre-existing account.")
            account.set_unusable_password()
            account.is_active = account.is_superuser = account.is_staff = False
            account.permissions.clear()
            account.permissions.add("Player")
            account.save(update_fields=["password", "is_active", "is_superuser", "is_staff"])
            player.permissions.clear()
            player.permissions.add("Player")
            identities.append(account.pk)
    return {"disabled_account_ids": identities, "staff_privileges_removed": True,
            "live_account_cache_updated": True}


def dispatch(path, action, payload=None):
    """Expose a narrow staff API; battle choices are deliberately absent."""
    payload = payload or {}
    if action == "snapshot":
        return snapshot(path)
    if action == "setup":
        return setup(path, payload)
    if action == "seed":
        return seed(path, payload)
    if action == "finish":
        return finish(path)
    if action == "disable":
        return disable_accounts(path)
    raise ValueError("Unknown pilot staff action.")
