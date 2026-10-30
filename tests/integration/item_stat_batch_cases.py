"""Replay the four pinned stat/type batches with real commands and owned models.

Only transport and explicitly declared native-stat fixtures are adapted. The
existing finite critical window is sampled without replacing outcomes. This
is fresh automated command/model proof, separate from live Telnet acceptance.
"""

import json
import os
from pathlib import Path
import random
import sys
import unittest

from isolated_postgres import IsolatedPostgres
import item_availability_cases as routes

ROOT = Path(__file__).resolve().parents[2]
PLAN = ROOT / "docs/testing/item-stat-type-plan-2026-10-22.json"
RESULTS = []


class ChanceUnobserved(Exception):
    """The allowed natural critical window has not qualified yet."""


def snapshot(fixture):
    """Read runtime and SQL values, including actual executed moves and PP."""
    from tools.qa.live_battle_pilot_server import mon_snapshot
    from pokemon.helpers.pokemon_helpers import get_stats

    session, players = fixture.session, fixture.players
    state = {"players": {}, "battle": None}
    for label, player in zip(("a", "b"), players):
        state["players"][label] = {"ordinary": True, "pokemon": []}
        for mon in routes.OwnedPokemon.objects.filter(trainer=player.trainer).order_by("created_at"):
            if mon.pk == fixture.boxed_id:
                continue
            row = routes.OwnedPokemon.objects.filter(pk=mon.pk).values("species", "current_hp", "held_item").get()
            state["players"][label]["pokemon"].append({"id": str(mon.pk), "species": row["species"],
                "hp": row["current_hp"], "item": row["held_item"], "stats": get_stats(mon),
                "moves": list(routes.ActiveMoveslot.objects.filter(pokemon=mon).order_by("slot").values("move__name", "current_pp"))})
    battle = fixture.last_battle
    frame = {"id": session.battle_id, "turn": battle.turn_count, "sides": {},
             "callback_failures": list(getattr(battle, "_callback_failures", []) or [])}
    for part in battle.participants:
        def observe(mon):
            """Detach observations from objects that will continue to mutate."""
            value = mon_snapshot(mon)
            value["item"] = str(getattr(mon.item, "name", mon.item) or "")
            value["stats"] = dict(getattr(mon, "stats", {}) or {})
            value["stats"].update({name: mon.getStat(name, True, True) for name in ("atk", "def", "spa", "spd", "spe")})
            value["last_executed_move"] = {name: getattr(getattr(mon, "last_move", None), name, None)
                                           for name in ("name", "type", "power")}
            return value
        frame["sides"][part.team] = {"active": [observe(mon) for mon in part.active],
                                    "pokemon": [observe(mon) for mon in part.pokemons]}
    state["ended_battle" if battle.battle_over else "battle"] = frame
    return json.loads(json.dumps(state, default=str))


def subject(record, index=-1, side="A", slot=0):
    """Follow original identity rather than assuming its active slot persists."""
    identity = record["snapshots"][0]["players"][side.lower()]["pokemon"][slot]["id"]
    state = record["snapshots"][index]
    frame = state.get("battle") or state.get("ended_battle")
    return next(mon for mon in frame["sides"][side]["pokemon"] if mon["id"].removeprefix("owned:") == identity)


def loss(record, side="B", start=0, end=-1):
    """Measure the actual HP change from detached observations."""
    return subject(record, start, side)["hp"] - subject(record, end, side)["hp"]


def assess(probe, records):
    """Apply only the seven unchanged rule kinds in the bounded original plan."""
    facts = []
    for rule in probe["rules"]:
        record = records[rule.get("case", -1)]
        side, index = rule.get("side", "A"), rule.get("after", -1)
        old, new = subject(record, rule.get("before", 0), side), subject(record, index, side)
        kind = rule["type"]
        fact = {"type": kind}
        if kind == "damage_relation":
            values = [loss(row, side, rule.get("before", 0), index) for row in records]
            assert min(values) > 0, values
            assert values[-1] < values[0] if rule["direction"] == "less" else values[-1] > values[0], values
            fact["damage"] = values
        elif kind == "held":
            from pokemon.names import normalize_name
            assert normalize_name(new["item"]) == normalize_name(rule["value"]), (new, rule)
            assert normalize_name(record["stored_item_after_cleanup"][side]) == normalize_name(rule["value"])
        elif kind == "executed_type":
            assert new["last_executed_move"]["type"] == rule["value"], (new, rule)
        elif kind == "critical_gain":
            control, variant = ("\n".join(row["outputs"]) for row in (records[0], records[-1]))
            assert "crit=" in control and "crit=" in variant
            if "crit=True" in control or "crit=True" not in variant:
                raise ChanceUnobserved()
            assert loss(records[-1], side) > loss(records[0], side)
        elif kind == "hp_loss_fraction":
            assert old["hp"] - new["hp"] == old["max_hp"] * rule["numerator"] // rule["denominator"]
        elif kind == "healing_relation":
            values = [subject(row, index, side)["hp"] - subject(row, 0, side)["hp"] for row in records]
            assert min(values) > 0 and values[-1] > values[0], values
            fact["healed"] = values
        elif kind == "series_growth":
            values = [loss(record, side, i, i + 1) for i in range(len(record["snapshots"]) - 1)]
            assert len(values) >= 3 and min(values) > 0 and values[1] > values[0] and values[2] > values[1], values
            fact["damage"] = values
        else:
            raise AssertionError("Unplanned rule: " + kind)
        facts.append(fact)
    return facts


def run_case(case, offset):
    """Run an unchanged fixture/seed through production command and SQL paths."""
    from tools.qa.live_dex_cases import from_dict
    from tools.qa.live_dex_runner import evaluate
    from pokemon.helpers.pokemon_helpers import get_max_hp

    fixture = routes.AcquisitionCases()
    fixture.setUp()
    fixture.boxed_id = fixture.mon.pk
    routes.PlacementService(fixture.player.storage).to_box(fixture.mon)
    record = {"key": case["key"], "case": case, "seed": case["seed"] + offset, "outputs": [], "snapshots": []}
    try:
        for side, player in zip(("a", "b"), fixture.players):
            for index, spec in enumerate(case[side]):
                mon = routes.create_owned_pokemon(spec["species"], player.trainer, spec["level"],
                    ability=spec["ability"], gender=spec["gender"], nature="Hardy", ivs=[0] * 6, evs=[0] * 6,
                    active_move_names=spec["moves"], held_item=spec["item"])
                routes.PlacementService(player.storage).to_party(mon, slot=index + 1)
                mon.current_hp = max(1, int(get_max_hp(mon) * spec["hp_fraction"])) if spec["hp_fraction"] else 0
                mon.status = spec["status"]
                mon.save(update_fields=["current_hp", "status"])
        fixture.session = routes.BattleSession(fixture.player, fixture.players[1])
        fixture.session.start()
        fixture.last_battle = fixture.session.battle
        fixture.last_battle.debug = True
        fixture.last_battle.rng = random.Random(record["seed"])
        record["snapshots"].append(snapshot(fixture))
        for turn_index, turn in enumerate(case["turns"]):
            if case.get("seed_each_turn"):
                fixture.last_battle.rng = random.Random(record["seed"] + turn_index)
            for label, command in turn:
                assert command.startswith("+attack "), command
                side = 0 if label == "a" else 1
                start = len(fixture.players[side].messages)
                fixture.command("attack", command.removeprefix("+attack "), side)
                record["outputs"].extend(map(str, fixture.players[side].messages[start:]))
            record["snapshots"].append(snapshot(fixture))
        record.update(evaluate(from_dict(case), record["snapshots"], record["outputs"]))
        fixture.session.end()
        record["stored_item_after_cleanup"] = {side: routes.OwnedPokemon.objects.filter(
            trainer=player.trainer).exclude(pk=fixture.boxed_id).order_by("created_at").values_list("held_item", flat=True).first()
            for side, player in zip(("A", "B"), fixture.players)}
        record["cleanup"] = {"room_clear": not fixture.room.db.battles,
                             "locks_clear": all(not player.db.battle_lock for player in fixture.players)}
        assert all(record["cleanup"].values())
        return record
    finally:
        fixture.tearDown()
        fixture.doCleanups()


class StatTypeBatchCases(unittest.TestCase):
    """Keep the established 25-item/50-template bounds and independent outcomes."""

    def test_pinned_batch(self):
        """Retain every attempt; chance misses never count as positive proof."""
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        batch = next(row for row in plan["batches"] if row["id"] == os.environ["PF2_ITEM_SUPPORT_BATCH"])
        self.assertLessEqual(len(batch["items"]), 25)
        self.assertLessEqual(len(batch["case_keys"]), 50)
        probes = {probe["label"]: probe for probe in plan["probes"]}
        for label in batch["checks"]:
            probe = probes[label]
            with self.subTest(label=label):
                for offset in range(40 if probe["chance"] else 1):
                    records = [run_case(case, offset) for case in probe["cases"]]
                    result = {"label": label, "item": probe["item"], "batch": batch["id"], "offset": offset, "records": records}
                    try:
                        result["facts"] = assess(probe, records)
                        result["status"] = "outcome_verified"
                    except ChanceUnobserved:
                        result["status"] = "chance_not_observed"
                    RESULTS.append(result)
                    if result["status"] == "outcome_verified":
                        break
                self.assertEqual(result["status"], "outcome_verified", label)


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT / "tools" / "audits"))
    with IsolatedPostgres() as database:
        database.create_model_tables()
        routes.load_runtime()
        try:
            result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(StatTypeBatchCases))
        finally:
            if os.environ.get("PF2_ITEM_BATCH_EVIDENCE"):
                Path(os.environ["PF2_ITEM_BATCH_EVIDENCE"]).write_text(json.dumps(RESULTS, indent=2, default=str) + "\n", encoding="utf-8")
        raise SystemExit(not result.wasSuccessful())
