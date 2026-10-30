"""Resumable, isolated full-catalog probes through real local player logins.

Only setup/observation use a separate staff account. Results distinguish direct
outcomes, smoke execution, expected failures and unresolved diagnoses. Network
access is fixed to localhost and the runner never downloads anything.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
import sys
import time
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path


if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.qa import live_battle_pilot as pilot
from tools.qa.live_dex_cases import catalog, from_dict, key, serializable

sys.path.insert(0, str(pilot.REPO))


COMPLETE = {"outcome_verified", "smoke_completed", "expected_failure"}
USER_WIP = {"commands/player/cmd_sheet.py", "tests/integration/cloud_gameplay_cases.py",
            "tests/ownership/test_sheet_pokemon_fusion.py", "utils/party_view.py"}


def has_server_error(text):
    """Recognize exceptions/severity without flagging a normal critical capture."""
    return bool(re.search(r"Traceback|\[EE\]|callback failure|\bUnhandled\b", text, re.I)
                or re.search(r"\bCRITICAL\b", text))


def now():
    """Return a sortable timestamp for reproducible evidence and progress."""
    return datetime.now(timezone.utc).isoformat()


class SweepClient(pilot.TelnetClient):
    """Keep command evidence bounded and use short local response quiet periods."""

    def read(self, timeout=2, quiet=.06, marker=None):
        """Staff responses remain framed; player completion is checked in state."""
        return super().read(timeout=timeout, quiet=quiet, marker=marker)

    def record(self, command, output):
        """Rotate redacted transcripts at 16 MiB inside the ignored run folder."""
        path = self.output / "transcript.jsonl"
        if path.exists() and path.stat().st_size >= 16 * 1024 * 1024:
            number = len(list(self.output.glob("transcript.*.jsonl.gz"))) + 1
            with path.open("rb") as source, gzip.open(self.output / f"transcript.{number:04d}.jsonl.gz", "wb") as dest:
                for block in iter(lambda: source.read(1024 * 1024), b""):
                    dest.write(block)
            path.unlink()
        return super().record(command, output)


def mon(state, side="A", index=0):
    """Read an active live Pokemon, falling back to persisted state after battle."""
    frame = state.get("battle") or state.get("ended_battle")
    if frame:
        active = frame["sides"][side]["active"]
        if len(active) > index:
            return active[index]
    player = state["players"]["a" if side == "A" else "b"]
    stored = player["pokemon"][index]
    return stored | {"boosts": {}, "volatiles": [], "ability_state": {}, "max_hp": stored.get("stats", {}).get("hp", 0)}


def pp(state, name):
    """Read the real owned Pokemon's selected move slot PP."""
    for move in state["players"]["a"]["pokemon"][0]["moves"]:
        if key(move["move__name"]) == key(name):
            return move["current_pp"]
    raise AssertionError("The selected move is missing from the real owned moveset.")


def original_mon(state, start, side="A", index=0):
    """Follow the original HP subject after a normal switch replaces its slot."""
    original = mon(start, side, index)
    current = mon(state, side, index)
    identity = original.get("id")
    if not identity or current.get("id") == identity:
        return current
    frame = state.get("battle") or state.get("ended_battle") or {}
    for candidate in frame.get("sides", {}).get(side, {}).get("pokemon", []):
        if candidate.get("id") == identity:
            return candidate
    for candidate in state["players"]["a" if side == "A" else "b"]["pokemon"]:
        if str(candidate.get("id")) == str(identity).removeprefix("owned:"):
            return candidate
    raise AssertionError("The original HP subject disappeared from battle and owned observations.")


def side_pp(state, side, name, index=0):
    """Read either ordinary player's exact real moveslot PP."""
    for move in state["players"]["a" if side == "A" else "b"]["pokemon"][index]["moves"]:
        if key(move["move__name"]) == key(name):
            return move["current_pp"]
    raise AssertionError("Missing observed moveslot " + name)


def observed_move_use(case, start, end, move_name):
    """Distinguish a real PP debit from Sketch's permanent slot replacement."""
    if case.pp_source == "runtime":
        label = "a" if case.pp_actor == "A" else "b"
        old, new = (state["players"][label]["pokemon"][0] for state in (start, end))
        if any(old[field] != new[field] for field in ("id", "species", "moves")):
            raise AssertionError("Temporary copied move use changed the owned identity or moveset.")
        actors = [mon(state, case.pp_actor) for state in (start, end)]
        if actors[0].get("id") != actors[1].get("id") or not actors[0].get("id"):
            raise AssertionError("Temporary PP observations must follow the same runtime actor.")
        values = []
        for actor in actors:
            matches = [move["pp"] for move in actor.get("runtime_moves", []) if key(move["name"]) == key(move_name)]
            if len(matches) != 1 or not isinstance(matches[0], int) or matches[0] < 0:
                raise AssertionError("Missing or invalid temporary moveslot PP.")
            values.append(matches[0])
        return *values, False
    if case.pp_source != "owned":
        raise AssertionError("Unknown PP observation source: " + case.pp_source)
    before = side_pp(start, case.pp_actor, move_name)
    try:
        after = side_pp(end, case.pp_actor, move_name)
        return before, after, False
    except AssertionError:
        if key(move_name) != "sketch":
            raise
    label = "a" if case.pp_actor == "A" else "b"
    old, new = (state["players"][label]["pokemon"][0] for state in (start, end))
    expected = {key(expectation["value"]) for expectation in case.assertions
                if expectation["type"] == "stored_move" and expectation.get("side", "A") == case.pp_actor
                and expectation.get("index", 0) == 0}
    selected = next(index for index, move in enumerate(old["moves"]) if key(move["move__name"]) == "sketch")
    replacement = new["moves"][selected] if len(new["moves"]) > selected else {}
    if (old["id"] != new["id"] or before <= 0
            or replacement.get("slot") != old["moves"][selected].get("slot")
            or key(replacement.get("move__name")) not in expected
            or key(replacement.get("move__name")) == "sketch"):
        raise AssertionError("The owned Sketch slot was not replaced by the declared copied move.")
    return before, None, True


def expected_blockers(case, states, outputs):
    """Explain only directly evidenced legal blockers, without hiding mismatches."""
    text = "\n".join(outputs).lower()
    reasons = []
    # Accuracy misses are observed outcomes, not defects or successful effect proof.
    missed = any(("missed" in line or "failed to hit" in line)
                 and key(case.subject) in key(line) for line in text.splitlines())
    if missed:
        accuracy = case.raw.get("accuracy")
        if isinstance(accuracy, (int, float)) and accuracy is not True and accuracy < 100:
            reasons.append(f"The {accuracy}% accurate move missed; retry needed for its positive outcome.")
    start = states[0]
    target_types = mon(start, "B").get("types", [])
    move_type = case.raw.get("type")
    immunities = {"Normal": {"Ghost"}, "Fighting": {"Ghost"}, "Ghost": {"Normal"},
                  "Electric": {"Ground"}, "Ground": {"Flying"}, "Poison": {"Steel"},
                  "Psychic": {"Dark"}, "Dragon": {"Fairy"}}
    if case.kind == "move" and case.raw.get("category") != "Status" and set(target_types) & immunities.get(move_type, set()):
        reasons.append(f"{move_type} is ineffective against the target's {target_types} typing.")
    if "unable to move" in text:
        initial_status = mon(start).get("status")
        if initial_status in {"slp", "par", "frz"} or key(case.a[0].ability) == "truant":
            reasons.append("The observed initial status/Truant can legally prevent movement.")
    if case.subject in {"Splash", "Celebrate", "Happy Hour", "Hold Hands"}:
        reasons.append("This move has no direct combat effect in this PvP fixture.")
    return reasons


def observed_stat(pokemon, name):
    """Read the actual computed battle stat under its supported aliases."""
    values = pokemon.get("stats", {})
    aliases = {"atk": "attack", "def": "defense", "spa": "special_attack", "spd": "special_defense", "spe": "speed"}
    return values[name] if name in values else values.get(aliases.get(name, name))


def observed_present_healing_cap(case, states, outputs):
    """Qualify a selected healing branch in the isolated one-turn Present probe.

    A full target and a no-effect message alone cannot identify Present's random
    branch. Require its actual modified move, exact PP debit and stable full-HP
    target, with no other fixture action or effect that could explain the null.
    This supplies expected-negative proof, never positive healing proof.
    """
    if (case.kind != "move" or key(case.subject) != "present" or case.assertions
            or case.pp_actor != "A" or case.pp_source != "owned" or case.mode != "single"
            or len(case.a) != 1 or len(case.b) != 1 or len(states) != 2
            or tuple(tuple(tuple(command) for command in turn) for turn in case.turns)
            != ((("a", "+attack Present"), ("b", "+attack Splash")),)
            or key(case.a[0].moves[0]) != "present" or key(case.b[0].moves[0]) != "splash"):
        return False
    start, end = states
    move = mon(end).get("last_executed_move", {})
    before_pp, after_pp = (side_pp(state, "A", "Present") for state in states)
    if (move.get("name") != "Present" or move.get("type") != "Normal"
            or move.get("power") != 0 or move.get("heal") != .25
            or before_pp <= 0 or after_pp < 0 or before_pp - after_pp != 1):
        return False
    for state in states:
        frame = state.get("battle")
        if not frame or not frame.get("id") or frame["id"] != start["battle"].get("id"):
            return False
        field = frame.get("field", {})
        if (any(key(field.get(name, "")) not in {"", "none"} for name in ("weather", "terrain"))
                or field.get("pseudo_weather")):
            return False
        for side, label in (("A", "a"), ("B", "b")):
            actor, initial = mon(state, side), mon(start, side)
            owned = state["players"][label]["pokemon"][0]
            allowed = {"noability", "noguard"} if side == "A" else {"noability"}
            if (not actor.get("id") or actor["id"] != initial.get("id")
                    or actor["id"] != "owned:" + str(owned["id"])
                    or actor.get("species") != initial.get("species")
                    or actor.get("status") or actor.get("volatiles") or actor.get("item")
                    or key(actor.get("ability", "")) not in allowed
                    or frame["sides"][side].get("conditions") or frame["sides"][side].get("slot_conditions")):
                return False
        target = mon(state, "B")
        if (target.get("hp", 0) <= 0 or target["hp"] != target.get("max_hp")
                or target["max_hp"] != mon(start, "B").get("max_hp")
                or "Ghost" in target.get("types", [])):
            return False
    failures = [line for line in "\n".join(outputs).splitlines()
                if re.search(r"\bfailed\b|doesn't affect|does not affect|no effect|missed|failed to hit", line, re.I)
                and "splash" not in line.lower()]
    return bool(failures) and all(re.search(r"\bPresent\b.*\bno effect\b", line, re.I) for line in failures)


def evaluate(case, states, outputs):
    """Assert owned identity, actual turns/PP, and explicitly declared outcomes."""
    if len(states) != len(case.turns) + 1:
        raise AssertionError("Missing complete turn observations.")
    for state in states:
        if not all(player["ordinary"] for player in state["players"].values()):
            raise AssertionError("A battling account acquired staff privileges.")
        frame = state.get("battle") or state.get("ended_battle") or {}
        if frame.get("callback_failures"):
            raise AssertionError("The live battle recorded callback exceptions: " + json.dumps(frame["callback_failures"], default=str))
        if state.get("ended_battle"):
            for side, label in (("A", "a"), ("B", "b")):
                stored = {pokemon["id"]: pokemon for pokemon in state["players"][label]["pokemon"]}
                for pokemon in frame["sides"][side]["pokemon"]:
                    model_id = pokemon["id"].removeprefix("owned:")
                    if model_id in stored and pokemon["hp"] != stored[model_id]["hp"]:
                        raise AssertionError("Ended battle HP differs from persisted owned HP; inspect observer freshness and persistence.")
    for previous, current in zip(states, states[1:]):
        if current["battle"] and previous["battle"] and current["battle"]["turn"] <= previous["battle"]["turn"]:
            raise AssertionError("Normal commands did not resolve a complete turn.")
    start, end = states[0], states[-1]
    move_name = (case.b[0].moves[0] if case.pp_actor == "B" else
                 case.subject if case.kind == "move" else case.a[0].moves[0])
    before_pp, after_pp, replaced_sketch = observed_move_use(case, start, end, move_name)
    spent_pp = replaced_sketch or after_pp < before_pp
    reasons = expected_blockers(case, states, outputs)
    if not spent_pp and key(move_name) != "struggle":
        if not reasons:
            raise AssertionError("The tested move did not spend PP; execution is unproven.")
    mismatches = []
    for expectation in case.assertions:
        selected = states[expectation["after_turn"]] if "after_turn" in expectation else start if expectation.get("initial") else end
        side = expectation.get("side", "A")
        index = expectation.get("index", 0)
        actor, old = mon(selected, side, index), mon(start, side, index)
        kind = expectation["type"]
        if expectation.get("original") or kind in {"damage", "heal", "immune", "hp_loss_range", "hp_loss_fraction"}:
            actor = original_mon(selected, start, side, index)
        valid = True
        if kind == "species_identity":
            # This probe declares entry identity. A native ability may legally
            # change typing or forme after the selected move (e.g. Protean or
            # Stance Change); that does not invalidate the observed entry.
            actor = mon(start)
            stored = start["players"]["a"]["pokemon"][0]
            valid = key(stored["species"]) == key(case.subject) and actor["max_hp"] > 0
            if key(actor["species"]) != key(expectation.get("entry_form", case.subject)):
                mismatches.append("Entry changed the prepared form; investigate whether the native ability legitimately caused it.")
            expected_types = expectation.get("entry_types", list(case.raw.get("types", [])))
            if actor.get("types") != expected_types:
                mismatches.append(f"Entry types {actor.get('types')} differ from prepared form {expected_types}.")
        elif kind == "native_stats":
            from types import SimpleNamespace
            from pokemon.helpers.pokemon_helpers import get_max_hp, get_stats

            prepared = (case.a if side == "A" else case.b)[index]
            data = SimpleNamespace(species=expectation["value"], level=prepared.level,
                                   ivs=[0] * 6, evs=[0] * 6, nature="Hardy")
            expected = get_stats(data)
            valid = actor["max_hp"] == get_max_hp(data) and all(
                observed_stat(actor, short) == expected[long] for short, long in
                {"atk": "attack", "def": "defense", "spa": "special_attack",
                 "spd": "special_defense", "spe": "speed"}.items())
        elif kind == "damage":
            valid = actor["hp"] < old["hp"]
        elif kind == "heal":
            valid = actor["hp"] > old["hp"]
        elif kind == "immune":
            valid = actor["hp"] >= old["hp"]
        elif kind in {"status", "not_status"}:
            valid = (actor.get("status") == expectation["value"]) == (kind == "status")
        elif kind == "boosts":
            valid = all(pilot.stage(actor, stat) == value for stat, value in expectation["values"].items())
        elif kind in {"weather", "terrain"}:
            actual = (selected.get("battle") or selected.get("ended_battle") or {}).get("field", {}).get(kind, "")
            valid = key(actual) == key(expectation["value"])
        elif kind == "side_condition":
            frame = selected.get("battle") or selected.get("ended_battle") or {}
            actual = frame.get("sides", {}).get(side, {}).get("conditions", [])
            valid = (key(expectation["value"]) in {key(value) for value in actual}) == expectation.get("present", True)
        elif kind == "slot_condition":
            frame = selected.get("battle") or selected.get("ended_battle") or {}
            actual = frame.get("sides", {}).get(side, {}).get("slot_conditions", {}).get(str(expectation.get("slot", 0)), [])
            valid = (key(expectation["value"]) in {key(value) for value in actual}) == expectation.get("present", True)
        elif kind == "pseudo_weather":
            frame = selected.get("battle") or selected.get("ended_battle") or {}
            actual = frame.get("field", {}).get("pseudo_weather", [])
            valid = (key(expectation["value"]) in {key(value) for value in actual}) == expectation.get("present", True)
        elif kind == "types":
            valid = actor.get("types") == expectation["value"]
        elif kind == "types_one_of":
            valid = actor.get("types") in expectation["values"]
        elif kind == "has_type":
            valid = expectation["value"] in actor.get("types", [])
        elif kind == "active_species":
            valid = key(actor.get("species", "")) == key(expectation["value"])
        elif kind == "ability":
            valid = key(actor.get("ability", "")) == key(expectation["value"])
        elif kind == "item":
            valid = key(actor.get("item", "")) in ({"", "none"} if not expectation["value"] else {key(expectation["value"])})
        elif kind == "hp_fraction":
            valid = expectation["minimum"] <= actor["hp"] / actor["max_hp"] <= expectation["maximum"]
        elif kind == "runtime_move":
            moves = actor.get("runtime_moves", [])
            valid = any(key(move["name"]) == key(expectation["value"]) and move.get("pp") == expectation["pp"] for move in moves)
        elif kind == "executed_move":
            move = actor.get("last_executed_move", {})
            valid = key(move.get("name", "")) == key(expectation["value"]) and move.get("type") == expectation["move_type"]
        elif kind == "stored_move":
            moves = selected["players"]["a" if side == "A" else "b"]["pokemon"][index]["moves"]
            valid = any(key(move["move__name"]) == key(expectation["value"]) for move in moves)
        elif kind in {"stat_average", "stat_swapped"}:
            other_side = "B" if side == "A" else "A"
            other = mon(start, other_side)
            for stat in expectation["values"]:
                left, right = observed_stat(old, stat), observed_stat(other, stat)
                expected = (left + right) // 2 if kind == "stat_average" and left is not None and right is not None else right
                valid = valid and expected is not None and observed_stat(actor, stat) == expected
        elif kind == "volatile":
            valid = (key(expectation["value"]) in {key(value) for value in actor.get("volatiles", [])}) == expectation.get("present", True)
        elif kind == "ability_state":
            valid = actor.get("ability_state", {}).get(expectation["value"]) is True
        elif kind == "pp_cost":
            valid = side_pp(start, side, expectation["move"]) - side_pp(end, side, expectation["move"]) == expectation["value"]
        elif kind == "stored_pp":
            valid = side_pp(selected, side, expectation["move"], index) == expectation["value"]
        elif kind == "hp_loss_range":
            loss = original_mon(states[-2], start, side, index)["hp"] - actor["hp"]
            valid = expectation.get("minimum", float("-inf")) <= loss <= expectation.get("maximum", float("inf"))
        elif kind == "hp_loss_fraction":
            valid = old["hp"] - actor["hp"] == old["max_hp"] * expectation["numerator"] // expectation["denominator"]
        elif kind == "volatile_hp":
            value = actor.get("volatile_state", {}).get(expectation["value"], {})
            hp = value.get("hp") if isinstance(value, dict) else None
            numerator, denominator = expectation["below_fraction"]
            valid = isinstance(hp, (int, float)) and expectation["minimum"] <= hp < actor["max_hp"] * numerator // denominator
        elif kind == "retaliation":
            received = mon(start)["hp"] - mon(end)["hp"]
            returned = mon(start, "B")["hp"] - mon(end, "B")["hp"]
            valid = received > 0 and returned == int(received * expectation["multiplier"])
        else:
            raise AssertionError("Unknown outcome assertion: " + kind)
        if not valid:
            mismatches.append("Declared outcome not observed: " + json.dumps(expectation, sort_keys=True))
    if case.kind == "ability":
        observed = mon(start).get("ability", "")
        expected = case.entry_ability or case.subject
        if key(observed) != key(expected) and (case.entry_ability or key(case.subject) not in {"trace", "receiver", "powerofalchemy", "imposter"}):
            mismatches.append(f"Prepared ability {case.subject} became {observed} on entry.")
    if mismatches and not reasons:
        raise AssertionError("; ".join(mismatches))
    text = "\n".join(outputs)
    if re.search(r"Traceback|An untrapped error|Unhandled|Error in", text, re.I):
        raise AssertionError("The real game reported an exception; inspect retained output and server logs.")
    if not reasons and observed_present_healing_cap(case, states, outputs):
        return {"status": "expected_failure", "positive_outcome_verified": False,
                "expected_healing_cap_verified": True,
                "explanations": ["Present selected its quarter-HP healing branch; the same target was already at full HP, so healing was capped at zero."],
                "proof_scope": "Observed full-HP healing cap; does not prove positive healing or a damage branch."}
    if reasons:
        if case.assertions and not mismatches and spent_pp:
            return {"status": "outcome_verified", "explanations": reasons,
                    "positive_outcome_verified": True, "partial_or_explained_negative_observed": True,
                    "proof_scope": "Declared outcomes observed; an explained partial/other failure does not prove every hit or branch."}
        return {"status": "expected_failure", "explanations": reasons, "positive_outcome_verified": False}
    # Generic failure messages require diagnosis even if a turn completed.
    if re.search(r"\bfailed\b|doesn't affect|does not affect|no effect", text, re.I):
        # Splash is the harmless opponent; it must not falsely flag every case.
        lines = [line for line in text.splitlines() if re.search(r"\bfailed\b|doesn't affect|does not affect|no effect", line, re.I)
                 and "splash" not in line.lower()]
        if case.kind == "ability" and "Ghost" in mon(start).get("types", []) and key(case.b[0].moves[0]) == "tackle":
            # The native carrier's typing explains this opponent attack. It
            # supplies no defensive-ability proof; the ordinary probe remains
            # smoke unless another explicit outcome was independently checked.
            target_name = str(mon(start).get("name", mon(start).get("species", ""))).lower()
            lines = [line for line in lines if not (
                target_name in line.lower() and ("doesn't affect" in line.lower()
                                                or "does not affect" in line.lower()
                                                or ("tackle" in line.lower() and "no effect" in line.lower())))]
        if lines and not case.assertions:
            return {"status": "needs_diagnosis", "error": "Unexplained move failure: " + " / ".join(lines)[:800]}
    return {"status": "outcome_verified" if case.assertions else "smoke_completed",
            "positive_outcome_verified": bool(case.assertions),
            "proof_scope": "Only declared assertions" if case.assertions else "Real entry and command/PP smoke"}


class DexRunner(pilot.PilotRunner):
    """Run each subject through ordinary players, retaining every failed attempt."""

    def __init__(self, manifest, port=4000):
        super().__init__(manifest, port)
        self.clients = {label: SweepClient(client.label, client.credential, client.output, port, client.all_secrets)
                        for label, client in self.clients.items()}

    def clean(self):
        """Use normal concession, record guarded fallback, and drain only QA sockets."""
        state = self.api.call("snapshot")
        if state["battle"]:
            self.clients["a"].send("+concede yes")
            self.clients["b"].record("[RECEIVE concession]", self.clients["b"].read(timeout=.15, quiet=.02))
        return self.api.call("finish")

    def run_case(self, case, seed_offset=0):
        """Observe independently prepared fixtures and actual command effects."""
        result = {"key": case.key, "kind": case.kind, "subject": case.subject, "started_utc": now(),
                  "seed": case.seed + seed_offset, "status": "blocked", "snapshots": [], "outputs": [],
                  "assertions": case.assertions, "limitations": case.limitations}
        result["case"] = asdict(case)
        log_offsets = {path: path.stat().st_size for path in (pilot.REPO / "server/logs").glob("*.log")}
        try:
            result["preparation"] = self.api.call("setup", {"a": [asdict(m) for m in case.a], "b": [asdict(m) for m in case.b]})
            for label, command in (("a", "+pvp/create " + case.mode),
                                   ("b", "+pvp/join " + self.data["players"]["a"]["name"]), ("a", "+pvp/start")):
                result["outputs"].append(self.clients[label].send(command))
            self.api.call("seed", {"seed": result["seed"]})
            state = self.api.call("snapshot")
            if not state["battle"]:
                raise RuntimeError("Normal PvP entry did not create a battle.")
            result["snapshots"].append(state)
            for turn_index, commands in enumerate(case.turns):
                if not result["snapshots"][-1]["battle"]:
                    raise AssertionError("Battle ended before all declared move phases completed.")
                if case.seed_each_turn:
                    self.api.call("seed", {"seed": result["seed"] + turn_index})
                for label, command in commands:
                    result["outputs"].append(self.clients[label].send(command))
                for label in ("a", "b"):
                    result["outputs"].append(self.clients[label].record("[RECEIVE turn]", self.clients[label].read(timeout=.15, quiet=.02)))
                result["snapshots"].append(self.api.call("snapshot"))
            result.update(evaluate(case, result["snapshots"], result["outputs"]))
        except AssertionError as error:
            result.update(status="needs_diagnosis", error=str(error))
        except Exception as error:
            result["error"] = str(error)
        finally:
            try:
                cleanup = self.clean()
                result["cleanup"] = {"staff_cleanup_required": cleanup["staff_cleanup_required"],
                                     "room_clear": not cleanup["battle"] and not cleanup["room_battles"],
                                     "locks_clear": all(not p["battle_lock"] and not p["battle_id"] for p in cleanup["players"].values())}
                if cleanup["staff_cleanup_required"]:
                    result.update(status="needs_diagnosis", cleanup_error="Normal concession required guarded staff fallback.")
            except Exception as error:
                result.update(status="blocked", cleanup_error=str(error))
            if result["status"] in {"needs_diagnosis", "blocked"}:
                result["failure_review"] = pilot.review_failure(case, result["snapshots"], "\n".join(result["outputs"]))
            result["completed_utc"] = now()
            errors = []
            for path, offset in log_offsets.items():
                if not path.exists():
                    continue
                with path.open("rb") as stream:
                    stream.seek(offset if path.stat().st_size >= offset else 0)
                    new_text = stream.read().decode("utf-8", errors="replace")
                if has_server_error(new_text):
                    errors.append({"file": path.name, "new_output": new_text[-16000:]})
            if errors:
                result["server_errors"] = errors
                result["log_error"] = "Server exception during this isolated case; correlate retained battle IDs before declaring a defect."
                if result["status"] != "blocked":
                    result["status"] = "needs_diagnosis"
            folder = self.output / "evidence"
            folder.mkdir(exist_ok=True)
            target = folder / (case.key + ".json.gz")
            if target.exists():
                attempts = self.output / "attempts"
                attempts.mkdir(exist_ok=True)
                target.replace(attempts / (case.key + "-" + str(time.time_ns()) + ".json.gz"))
            with gzip.open(target, "wt", encoding="utf-8") as stream:
                json.dump(result, stream, default=str, ensure_ascii=False)
        return result

    def run(self, cases, selected=None, limit=None, retry=False, seed_offset=0):
        """Resume deterministically, stop on unresolved cleanup, persist progress."""
        path = self.output / "results.json"
        results = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
        by_key = {row["key"]: row for row in results}
        count = 0
        started = now()
        batch_total = len(selected) if selected else sum(case.key not in by_key or (retry and by_key[case.key]["status"] not in COMPLETE) for case in cases)
        try:
            for label in ("staff", "a", "b"):
                self.clients[label].open()
            self.api = pilot.StaffAPI(self.clients["staff"], self.manifest, pilot.REPO / "tools/qa/live_dex_server.py")
            self.clean()
            for case in cases:
                if (self.output / "stop-requested").exists():
                    print("Stopped between cases at the requested safe boundary.", flush=True)
                    break
                if selected and case.key not in selected:
                    continue
                if not selected and case.key in by_key and (not retry or by_key[case.key]["status"] in COMPLETE):
                    continue
                result = self.run_case(case, seed_offset)
                summary = {name: result[name] for name in ("key", "kind", "subject", "status", "completed_utc")}
                summary.update({name: result[name] for name in ("error", "cleanup_error", "log_error", "proof_scope", "explanations") if name in result})
                by_key[case.key] = summary
                pilot.save(path, list(by_key.values()))
                count += 1
                pilot.save(self.output / "progress.json", {"updated_utc": now(), "attempted": len(by_key),
                           "batch_started_utc": started, "batch_executed": count, "batch_total": batch_total,
                           "total": len(cases), "counts": dict(Counter(row["status"] for row in by_key.values())), "current": summary})
                print(json.dumps(summary, ensure_ascii=True), flush=True)
                if count % 25 == 0:
                    report(self.output, cases)
                    safety = verify(self.output, audit=False, quiet=True)
                    if not safety["protected_rows_unchanged"] or not safety["user_wip_unchanged"]:
                        raise RuntimeError("Protected data/source mismatch; stop the sweep.")
                if result["status"] == "blocked" and "cleanup_error" in result:
                    break
                if limit and count >= limit:
                    break
        finally:
            for client in self.clients.values():
                client.close()
            report(self.output, cases)
        return list(by_key.values())


def report(output, cases):
    """Publish honest per-entry coverage and a separate diagnosis queue."""
    path = output / "results.json"
    results = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    counts = Counter(row["status"] for row in results)
    lines = ["# Local logged-in dex sweep", "", f"Updated {now()}. {len(results)}/{len(cases)} entries attempted.", "",
             "Two ordinary QA players use real PvP commands. A separate staff account prepares only new, tagged fixtures and observes state.", "",
             "`outcome_verified` proves only the declared assertions. `smoke_completed` proves real entry/action/PP, "
             "not every mechanic. `expected_failure` is an explained negative outcome and still needs positive coverage. "
             "`needs_diagnosis` and `blocked` are not automatically game defects.", "",
             "| Catalog | Total | Attempted | Direct outcomes | Smoke | Expected failure | Diagnose | Blocked |",
             "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for kind in ("pokemon", "move", "ability", "regression"):
        subset = [row for row in results if row["kind"] == kind]
        tally = Counter(row["status"] for row in subset)
        values = [sum(c.kind == kind for c in cases), len(subset)] + [tally[s] for s in ("outcome_verified", "smoke_completed", "expected_failure", "needs_diagnosis", "blocked")]
        lines.append("| " + kind + " | " + " | ".join(map(str, values)) + " |")
    progress_path = output / "progress.json"
    if progress_path.exists():
        progress = json.loads(progress_path.read_text(encoding="utf-8"))
        if "batch_executed" in progress:
            lines += ["", f"Latest catalog batch: {progress['batch_executed']}/{progress.get('batch_total', len(cases))} "
                      f"fresh executions since {progress.get('batch_started_utc', 'unknown')}. "
                      "Until a fresh pass finishes, the table can include retained outcomes from earlier builds."]
    supporting = (("coverage-scope.md", "Exact coverage and remaining ability trigger gaps"),
                  ("ability-probes.md", "Matched ability/control experiments"),
                  ("wild-probes.md", "Wild escape and trapping experiments"),
                  ("diagnoses.md", "Reviewed diagnoses and repair evidence"),
                  ("closeout.md", "Final validation, safety and cleanup"))
    links = [f"- [{label}]({name})" for name, label in supporting if (output / name).exists()]
    if links:
        lines += ["", "## Supporting evidence", "", *links]
    pilots = sorted((path for path in output.glob("pilot-*/evidence-audit.json")), key=lambda path: path.stat().st_mtime)
    if pilots:
        latest = pilots[-1]
        audit = json.loads(latest.read_text(encoding="utf-8"))
        lines += ["", f"Latest pilot: `{latest.parent.name}`; {audit.get('audited_passes', 0)}/20 retained passes audited; "
                  f"{len(audit.get('errors', []))} audit errors. This is separate from catalog coverage."]
    lines += ["", "All logs, compressed per-case observations, prior attempts and database backups are under the Git-ignored `.codex-artifacts` folder. "
              "Transcripts rotate and compress at 16 MiB. No files are downloaded.", "",
              "The prepared moves/abilities test battle mechanics independently of natural learnsets and legal form/Z/Max activation. "
              "There is no claim of all pairwise interactions, probability distributions, browser UI or production readiness.", "",
              "## Diagnosis queue", "", "| Subject | Observation |", "| --- | --- |"]
    queue = [row for row in results if row["status"] in {"needs_diagnosis", "blocked"}]
    pilot.save(output / "diagnosis-queue.json", queue)
    for row in queue:
        observation = row.get("error", row.get("cleanup_error", "Needs review")).replace("|", "/").replace("\n", " ")
        lines.append(f"| {row['kind']}: {row['subject']} | {observation} |")
    safety_path = output / "safety-verification.json"
    if safety_path.exists():
        safety = json.loads(safety_path.read_text(encoding="utf-8"))
        lines += ["", f"Protected baseline: {safety['protected_baseline_rows']} rows. Unchanged: {safety['protected_rows_unchanged']}. "
                  f"Original unrelated source WIP unchanged: {safety['user_wip_unchanged']}."]
    if (output / "accounts-disabled.json").exists():
        lines += ["", "All QA account credentials have been invalidated and temporary staff access removed."]
    (output / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return dict(counts)


def verify(output, audit=True, quiet=False):
    """Hash all protected pre-run rows and preserve the user's unrelated WIP."""
    connection, _, _ = pilot.configure_database()
    before = json.loads((output / "protected-baseline.json").read_text(encoding="utf-8"))
    changes = pilot.compare_fingerprints(before, pilot.fingerprint(connection))
    source = json.loads((output / "source-baseline.json").read_text(encoding="utf-8"))["wip"]
    source_unchanged = {name: (pilot.REPO / name).is_file() and hashlib.sha256((pilot.REPO / name).read_bytes()).hexdigest() == digest
                        for name, digest in source.items()}
    errors, audited = [], 0
    if audit:
        pinned = json.loads((output / "catalog.json").read_text(encoding="utf-8"))
        lookup = {data["key"]: from_dict(data) for data in pinned}
        path = output / "results.json"
        for row in json.loads(path.read_text(encoding="utf-8")) if path.exists() else []:
            if row["status"] not in COMPLETE:
                continue
            try:
                with gzip.open(output / "evidence" / (row["key"] + ".json.gz"), "rt", encoding="utf-8") as stream:
                    evidence = json.load(stream)
                case = from_dict(evidence["case"]) if "case" in evidence else lookup[row["key"]]
                result = evaluate(case, evidence["snapshots"], evidence["outputs"])
                if result["status"] != row["status"] or not evidence["cleanup"]["room_clear"] or not evidence["cleanup"]["locks_clear"]:
                    raise AssertionError("Retained proof/cleanup does not support the result.")
                audited += 1
            except Exception as error:
                errors.append({"key": row["key"], "error": str(error)})
    result = {"verified_utc": now(), "protected_baseline_rows": sum(map(len, before.values())),
              "protected_rows_unchanged": not changes, "protected_changes": changes,
              "user_wip_unchanged": all(source_unchanged.get(name, False) for name in USER_WIP),
              "source_unchanged": source_unchanged, "evidence_audited": audited, "evidence_errors": errors}
    pilot.save(output / "safety-verification.json", result)
    if not quiet:
        print(json.dumps(result, indent=2))
    return result


def reassess(output, cases):
    """Re-evaluate exact retained fixtures, keeping observer corrections auditable."""
    path = output / "results.json"
    rows = json.loads(path.read_text(encoding="utf-8"))
    pinned = {data["key"]: from_dict(data) for data in json.loads((output / "catalog.json").read_text(encoding="utf-8"))}
    changes = []
    for row in rows:
        file = output / "evidence" / (row["key"] + ".json.gz")
        with gzip.open(file, "rt", encoding="utf-8") as stream:
            evidence = json.load(stream)
        case = from_dict(evidence["case"]) if "case" in evidence else pinned[row["key"]]
        try:
            assessment = evaluate(case, evidence["snapshots"], evidence["outputs"])
            cleanup = evidence["cleanup"]
            if not cleanup["room_clear"] or not cleanup["locks_clear"]:
                raise RuntimeError("Retained cleanup is incomplete.")
            if cleanup["staff_cleanup_required"] or evidence.get("server_errors"):
                continue  # These require a fresh reproduction or separate log diagnosis.
        except AssertionError as error:
            assessment = {"status": "needs_diagnosis", "error": str(error)}
        except Exception:
            continue  # Do not turn a blocked setup into an executed scenario.
        if assessment["status"] == row["status"] and assessment.get("error") == row.get("error"):
            continue
        before = dict(row)
        for name in ("error", "explanations", "proof_scope"):
            row.pop(name, None)
        row.update(assessment)
        row["reassessed_utc"] = now()
        changes.append({"key": row["key"], "evidence_sha256": hashlib.sha256(file.read_bytes()).hexdigest(),
                        "before": before, "after": dict(row),
                        "note": "Observer reassessment of the original saved fixture; no new gameplay execution and no substituted fixture."})
    directory = output / "reassessments"
    directory.mkdir(exist_ok=True)
    pilot.save(directory / (str(time.time_ns()) + ".json"),
               {"time_utc": now(), "evaluator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "changes": changes})
    pilot.save(path, rows)
    report(output, cases)
    print(json.dumps({"reassessed_entries": len(changes), "counts": dict(Counter(row["status"] for row in rows))}))
    return rows


def main():
    """Explicit local-only preparation, bounded/resumable execution and closeout."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("catalog", "prepare", "run", "verify", "reassess", "report", "disable"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--kind", choices=("pokemon", "move", "ability", "regression"))
    parser.add_argument("--case", action="append", default=[])
    parser.add_argument("--limit", type=int)
    parser.add_argument("--retry", action="store_true")
    parser.add_argument("--rerun-all", action="store_true", help="Freshly execute every selected catalog entry, retaining prior evidence.")
    parser.add_argument("--seed-offset", type=int, default=0)
    parser.add_argument("--order", nargs="+", choices=("pokemon", "move", "ability", "regression"))
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(pilot.ARTIFACTS) or output == pilot.ARTIFACTS:
        parser.error("Output must be a run folder inside .codex-artifacts.")
    cases = catalog()
    if args.order:
        priority = {kind: index for index, kind in enumerate(args.order)}
        cases = tuple(sorted(cases, key=lambda case: priority.get(case.kind, len(priority))))
    selected = set(args.case)
    if args.rerun_all:
        selected.update(case.key for case in cases if not args.kind or case.kind == args.kind)
    if args.kind:
        selected.update(case.key for case in cases if case.kind == args.kind)
        if not args.case and not args.rerun_all and args.action == "run":
            existing = output / "results.json"
            rows = json.loads(existing.read_text(encoding="utf-8")) if existing.exists() else []
            attempted = {row["key"] for row in rows if not args.retry or row["status"] in COMPLETE}
            selected -= attempted
            if not selected:
                print("No matching pending entries.")
                return
    if set(args.case) - {case.key for case in cases}:
        parser.error("Unknown case key.")
    if args.action == "prepare":
        pilot.prepare(output)
        pilot.save(output / "catalog.json", serializable(cases))
        report(output, cases)
    elif args.action == "catalog":
        output.mkdir(parents=True, exist_ok=True)
        pilot.save(output / "catalog.json", serializable(cases))
        print(json.dumps(dict(Counter(case.kind for case in cases))))
    elif args.action == "run":
        with pilot.run_lock(output):
            DexRunner(output / "manifest.json").run(cases, selected, args.limit, args.retry, args.seed_offset)
    elif args.action == "verify":
        result = verify(output)
        report(output, cases)
        if not result["protected_rows_unchanged"] or not result["user_wip_unchanged"] or result["evidence_errors"]:
            raise SystemExit(1)
    elif args.action == "reassess":
        with pilot.run_lock(output):
            reassess(output, cases)
    elif args.action == "disable":
        with pilot.run_lock(output):
            pilot.disable(output / "manifest.json", write_summary=False)
        report(output, cases)
    else:
        print(json.dumps(report(output, cases)))


if __name__ == "__main__":
    main()
