"""Read-only extra observations for the guarded local dex sweep.

Fixture mutations delegate to the pilot's exact ownership guards. No battle
choice, callback replacement, global RNG mutation or public setup is exposed.
"""

import hashlib
import importlib
import importlib.util
import inspect
import json
import types
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "pf2_dex_guarded_pilot", Path(__file__).with_name("live_battle_pilot_server.py")
)
_pilot = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_pilot)
_VERSIONS = None


def code_fingerprint(code):
    """Hash immutable code content without marshal's reference-count flags."""
    def canonical(value):
        if isinstance(value, types.CodeType):
            fields = ("co_argcount", "co_posonlyargcount", "co_kwonlyargcount", "co_nlocals", "co_stacksize",
                      "co_flags", "co_code", "co_consts", "co_names", "co_varnames", "co_freevars", "co_cellvars",
                      "co_name", "co_qualname", "co_firstlineno", "co_linetable", "co_exceptiontable")
            return {name: canonical(getattr(value, name)) for name in fields if hasattr(value, name)}
        if isinstance(value, bytes):
            return ["bytes", value.hex()]
        if isinstance(value, (tuple, frozenset)):
            values = [canonical(item) for item in value]
            if isinstance(value, frozenset):
                values.sort(key=lambda item: json.dumps(item, sort_keys=True))
            return [type(value).__name__, values]
        return [type(value).__name__, repr(value)]
    return hashlib.sha256(json.dumps(canonical(code), sort_keys=True).encode("utf-8")).hexdigest()


def loaded_code_versions():
    """Fingerprint loaded callback code once, without reading newer source files."""
    global _VERSIONS
    if _VERSIONS is None:
        result = {}
        names = ("pokemon.battle.engine", "pokemon.battle.damage", "pokemon.battle.battledata",
                 "pokemon.battle.turns", "pokemon.battle.logic", "pokemon.battle.conditions",
                 "pokemon.battle.legal_actions", "pokemon.battle.retaliation", "pokemon.dex.entities",
                 "pokemon.dex.functions.abilities_funcs", "pokemon.dex.functions.conditions_funcs",
                 "pokemon.dex.functions.items_funcs",
                 "pokemon.dex.functions.moves.damage_moves", "pokemon.dex.functions.moves.status_moves",
                 "pokemon.dex.functions.moves.misc_moves", "pokemon.utils.boosts",
                 "pokemon.battle._shared", "pokemon.battle.utils", "pokemon.battle.indirect_damage",
                 "pokemon.battle.effect_context", "pokemon.battle.stat_activation", "pokemon.battle.action_queue",
                 "pokemon.battle.item_effects", "pokemon.services.battle_items", "pokemon.battle.actions", "commands.player.cmd_battle_item",
                 "pokemon.battle.called_moves", "pokemon.battle.delayed_moves", "pokemon.battle.copied_moves",
                 "pokemon.battle.terastallization", "pokemon.battle.player_choices", "commands.player.cmd_battle_tera",
                 "pokemon.services.sketch", "pokemon.models.stats", "pokemon.helpers.pokemon_helpers",
                 "pokemon.battle.battleinstance", "pokemon.battle.appearance", "pokemon.battle.native_forms",
                 "pokemon.services.post_battle_items", "pokemon.battle.accuracy", "pokemon.battle.state", "pokemon.ui.battle_render",
                 "pokemon.battle.status.status_core", "pokemon.battle.status.burn", "pokemon.battle.status.freeze",
                 "pokemon.battle.status.paralysis", "pokemon.battle.status.poison", "pokemon.battle.status.sleep",
                 "pokemon.battle.protection", "utils.pokemon_utils")
        for name in names:
            module = importlib.import_module(name)
            digest = hashlib.sha256()
            for label, value in sorted(vars(module).items()):
                if getattr(value, "__module__", None) != name:
                    continue
                functions = [(label, value)] if inspect.isfunction(value) else []
                if inspect.isclass(value):
                    functions = []
                    for member, function in sorted(vars(value).items()):
                        if isinstance(function, (staticmethod, classmethod)):
                            function = function.__func__
                        if isinstance(function, property):
                            for suffix, accessor in (("get", function.fget), ("set", function.fset), ("delete", function.fdel)):
                                if accessor is not None:
                                    functions.append((label + "." + member + "." + suffix, accessor))
                        elif inspect.isfunction(function):
                            functions.append((label + "." + member, function))
                for label, function in functions:
                    digest.update(label.encode("utf-8"))
                    digest.update(code_fingerprint(function.__code__).encode("ascii"))
            result[name] = digest.hexdigest()
        result["qa_observer_algorithm"] = code_fingerprint(code_fingerprint.__code__)
        result["qa_observer_snapshot"] = code_fingerprint(snapshot.__code__)
        _VERSIONS = result
    return dict(_VERSIONS)


def snapshot(path):
    """Include field, side, species stats and item observations for diagnostics."""
    from pokemon.helpers.pokemon_helpers import get_stats
    from pokemon.models.core import OwnedPokemon

    result = _pilot.snapshot(path)
    result["code_fingerprint_method"] = "structural-v2-reference-independent"
    result["loaded_code_versions"] = loaded_code_versions()
    _, _, _, players, trainers = _pilot.guarded_context(path)
    for label, trainer in trainers.items():
        stored = {str(mon.pk): mon for mon in OwnedPokemon.objects.filter(trainer=trainer)}
        for mon in result["players"][label]["pokemon"]:
            model = stored[mon["id"]]
            mon["stats"] = get_stats(model)
            mon["item"] = model.held_item
    inst = _pilot.active_session(players)
    from pokemon.battle import damage
    from pokemon.battle.engine import Battle, BattleMove, _apply_move_damage
    from pokemon.battle.legal_actions import LegalActions
    from pokemon.dex.entities import _invoke_raw_callback
    from pokemon.dex.functions import conditions_funcs
    from pokemon.dex.functions.abilities_funcs import Disguise, Filter, Sheerforce, Zenmode

    result["runtime"]["pressure_target_scope_loaded"] = "target" in Battle.deduct_pp.__code__.co_varnames
    result["runtime"]["scripted_target_selection_loaded"] = "scripted" in LegalActions.automatic_targets
    result["runtime"]["named_ability_damage_resolution_loaded"] = hasattr(damage, "_pokemon_ability")
    result["runtime"]["retaliation_ledger_fix_loaded"] = "last_opposing_damage" in damage.apply_damage.__code__.co_consts
    result["runtime"]["damage_modifier_ownership_loaded"] = "scoped_modifiers" in damage.apply_damage.__code__.co_varnames
    result["runtime"]["zen_mode_lifecycle_fix_loaded"] = hasattr(Zenmode, "_base_form")
    result["runtime"]["snow_handler_fix_loaded"] = hasattr(conditions_funcs, "Snow")
    result["runtime"]["type_modifier_arg_order_fix_loaded"] = Filter.onSourceModifyDamage.__code__.co_varnames[1:4] == ("damage", "source", "target")
    result["runtime"]["sheer_force_raw_secondary_fix_loaded"] = "secondary" in Sheerforce.onModifyMove.__code__.co_consts
    keyword_sets = [set(value) for value in _apply_move_damage.__code__.co_consts if isinstance(value, tuple) and all(isinstance(k, str) for k in value)]
    result["runtime"]["base_power_context_fix_loaded"] = any({"user", "target", "move", "battle"} <= values for values in keyword_sets)
    result["runtime"]["base_power_attacker_alias_loaded"] = any({"attacker", "defender", "move", "battle"} <= values for values in keyword_sets)
    result["runtime"]["literal_ability_hooks_loaded"] = "bool" in _invoke_raw_callback.__code__.co_names
    result["runtime"]["consumable_form_guards_loaded"] = hasattr(Disguise, "_break_disguise")
    result["runtime"]["direct_move_effect_type_loaded"] = getattr(BattleMove, "effectType", None) == "Move"
    result["runtime"]["side_protection_gate_loaded"] = hasattr(Battle, "_passes_side_protection")
    result["runtime"]["side_duration_expiry_loaded"] = hasattr(Battle, "_handle_side_condition_durations")
    result["runtime"]["faint_source_event_fix_loaded"] = "AfterFaint" in Battle.on_faint.__code__.co_consts
    result["runtime"]["prepare_hit_ability_event_loaded"] = "PrepareHit" in Battle.use_move.__code__.co_consts
    result["runtime"]["authoritative_pp_drain_loaded"] = hasattr(Battle, "reduce_move_pp")
    result["runtime"]["per_use_ability_move_flags_loaded"] = "_ability_move_prepared" in Battle.use_move.__code__.co_names
    result["runtime"]["guarded_recoil_loaded"] = "apply_recoil_damage" in BattleMove.execute.__code__.co_names
    result["runtime"]["weather_damage_suppression_loaded"] = "weather_suppressed" in damage.damage_calc.__code__.co_names
    result["runtime"]["status_sacrifice_hit_context_loaded"] = "_primary_hit_successful" in BattleMove.execute.__code__.co_names
    result["runtime"]["owned_pp_restoration_loaded"] = hasattr(Battle, "restore_move_pp")
    result["runtime"]["revival_switch_protocol_fix_loaded"] = "revivalblessing" in Battle._queue_self_switch.__code__.co_consts
    result["runtime"]["faint_replacement_slot_hooks_loaded"] = "_run_slot_swap_events" in Battle.run_faint.__code__.co_names
    result["runtime"]["single_secondary_phase_loaded"] = "_engine_secondaries" in _apply_move_damage.__code__.co_names
    result["runtime"]["guarded_healing_inversion_loaded"] = "apply_indirect_damage" in Battle.heal.__code__.co_names
    from pokemon.dex.functions.abilities_funcs import Berserk, Merciless, Soulheart

    result["runtime"]["berserk_actual_hit_ledger_loaded"] = "last_damaged_by" in Berserk.onAfterMoveSecondary.__code__.co_consts
    result["runtime"]["merciless_guaranteed_poison_crit_loaded"] = 5 in Merciless.onModifyCritRatio.__code__.co_consts
    result["runtime"]["soulheart_faint_signature_loaded"] = Soulheart.onAnyFaint.__code__.co_varnames[1] == "target"
    from pokemon.battle.battledata import Pokemon
    from pokemon.battle.turns import TurnProcessor
    from pokemon.dex.functions.abilities_funcs import Forecast, Zerotohero
    from pokemon.dex.functions.moves.damage_moves import Stuffcheeks

    result["runtime"]["wild_escape_exceptions_loaded"] = "_grounded_for_escape" in TurnProcessor.attempt_flee.__code__.co_names
    result["runtime"]["ability_state_checkpoint_loaded"] = "ability_state" in Pokemon.from_dict.__code__.co_consts
    result["runtime"]["weather_form_context_loaded"] = Forecast.onWeatherChange.__code__.co_argcount >= 4
    result["runtime"]["zero_to_hero_switch_form_loaded"] = "formeChange" in Zerotohero.onSwitchOut.__code__.co_names
    result["runtime"]["forced_berry_moves_loaded"] = ("source", "effect", "force") in Stuffcheeks.onHit.__code__.co_consts
    observed_battle = inst.battle if inst and inst.battle else None
    frame = result["battle"]
    if observed_battle is not None:
        # A bounded reference to this QA battle permits read-only observation
        # after normal battle end detaches the session. No callback is patched.
        players["staff"].ndb.live_dex_last_observed = {"id": frame["id"], "battle": observed_battle}
    else:
        last = players["staff"].ndb.live_dex_last_observed
        if last:
            observed_battle = last["battle"]
            allowed = {players[label].pk for label in ("a", "b")}
            if any(getattr(getattr(part, "player", None), "pk", None) not in allowed | {None}
                   for part in observed_battle.participants):
                raise RuntimeError("Refusing an ended observation with a non-QA participant.")
            field = observed_battle.field
            frame = {"id": last["id"], "turn": observed_battle.turn_count, "sides": {},
                     "field": {"weather": str(field.weather), "terrain": str(field.terrain),
                               "pseudo_weather": list(field.pseudo_weather or {})}}
            for part in observed_battle.participants:
                frame["sides"][part.team] = {"active": [_pilot.mon_snapshot(mon) for mon in part.active],
                                             "pokemon": [_pilot.mon_snapshot(mon) for mon in part.pokemons]}
            result["ended_battle"] = frame
    if observed_battle is not None:
        flee = getattr(observed_battle, "_flee_result", {}) or {}
        frame["flee_result"] = {name: flee[name] for name in ("success", "reason", "message") if name in flee}
        frame["battle_over"] = bool(getattr(observed_battle, "battle_over", False))
        frame["callback_failures"] = list(getattr(observed_battle, "_callback_failures", []) or [])
        for part in observed_battle.participants:
            side = frame["sides"][part.team]
            side["conditions"] = list(getattr(part.side, "conditions", {}) or {})
            side["slot_conditions"] = {str(slot): list(conditions)
                                        for slot, conditions in (getattr(part.side, "slot_conditions", {}) or {}).items()}
            for collection, live in (("active", part.active), ("pokemon", part.pokemons)):
                for observed, mon in zip(side[collection], live):
                    item = getattr(mon, "item", "")
                    observed["item"] = str(getattr(item, "name", item) or "")
                    observed["stats"] = dict(getattr(mon, "stats", {}) or {})
                    observed["tera"] = {
                        "type": getattr(mon, "terastallized", None),
                        "configured": getattr(mon, "tera_type", ""),
                        "original_types": list(getattr(mon, "tera_original_types", [])),
                        "spent_types": list(getattr(mon, "stellar_boosted_types", [])),
                    }
                    if callable(getattr(mon, "getStat", None)):
                        observed["cached_stats"] = dict(observed["stats"])
                        observed["stats"].update({name: mon.getStat(name, True, True)
                                                  for name in ("atk", "def", "spa", "spd", "spe")})
                    observed["last_move"] = str(getattr(getattr(mon, "last_move", None), "name", ""))
                    executed = getattr(mon, "last_move", None)
                    observed["last_executed_move"] = {
                        name: getattr(executed, name, None)
                        for name in ("name", "type", "power", "heal")
                    }
                    observed["runtime_moves"] = [{"name": getattr(move, "name", str(move)), "pp": getattr(move, "pp", getattr(move, "current_pp", None))}
                                                 for move in getattr(mon, "moves", [])]
                    observed["volatile_state"] = dict(getattr(mon, "volatiles", {}) or {})
                    last_hit = (getattr(mon, "tempvals", {}) or {}).get("last_damaged_by")
                    if isinstance(last_hit, dict):
                        observed["last_damaged_by"] = {
                            "damage": last_hit.get("damage"), "this_turn": last_hit.get("this_turn"),
                            "turn": last_hit.get("turn"),
                            "source": str(getattr(last_hit.get("source"), "model_id", "")),
                            "move": str(getattr(last_hit.get("move"), "name", "")),
                            "category": str(getattr(last_hit.get("move"), "category", "")),
                        }
    return result


def dispatch(path, action, payload=None):
    """Use the same narrow staff API, with richer read-only snapshots."""
    if action == "snapshot":
        return snapshot(path)
    if action == "connections":
        from evennia import SESSION_HANDLER

        _, data, _, _, _ = _pilot.guarded_context(path)
        qa_ids = {entry["account_id"] for entry in data["players"].values()}
        others = []
        for session in SESSION_HANDLER.get_sessions():
            account = session.get_account()
            if account is not None and account.pk not in qa_ids:
                others.append({"account_id": account.pk, "character_id": getattr(session.get_puppet(), "pk", None)})
        return {"other_authenticated_sessions": others, "safe_for_local_reload": not others}
    if action == "setup":
        _, _, _, players, _ = _pilot.guarded_context(path)
        if _pilot.active_session(players) is None:
            players["staff"].ndb.live_dex_last_observed = None
    result = _pilot.dispatch(path, action, payload)
    if action == "finish" and not result.get("battle"):
        players = _pilot.guarded_context(path)[3]
        players["staff"].ndb.live_dex_last_observed = None
    if action == "setup":
        return snapshot(path)
    return result
