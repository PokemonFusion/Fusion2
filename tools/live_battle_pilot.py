"""Run an isolated 20-scenario pilot through real local player connections.

Preparation backs up the local database before creating new QA identities.
The runner uses normal player commands for all battle choices. A separate
staff session prepares owned teams and observes results. No restart is needed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
import select
import socket
import subprocess
import sys
import tempfile
import time
from contextlib import contextmanager
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from live_battle_pilot_cases import SCENARIOS

REPO = Path(__file__).resolve().parents[1]
ARTIFACTS = REPO / ".codex-artifacts"


def save(path, data):
    """Atomically replace one local JSON artifact."""
    path = Path(path)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, indent=2, default=str, ensure_ascii=False), encoding="utf-8")
    # Windows readers and indexers can briefly hold a file without delete
    # sharing. Keep the previous complete result and retry the atomic replace.
    for attempt in range(9):
        try:
            temporary.replace(path)
            break
        except PermissionError:
            if attempt == 8:
                raise
            time.sleep(min(.02 * 2 ** attempt, .5))


def sha(data):
    """Return a stable digest without exposing protected row contents."""
    return hashlib.sha256(json.dumps(data, sort_keys=True, default=str).encode()).hexdigest()


@contextmanager
def run_lock(output):
    """Refuse overlapping runners using the same QA identities."""
    path = output / "pilot-run.lock"
    descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    try:
        os.write(descriptor, str(os.getpid()).encode())
        yield
    finally:
        os.close(descriptor)
        path.unlink()


def configure_database():
    """Load the local game ORM, refusing a remote database before any mutation."""
    sys.path.insert(0, str(REPO))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
    import django
    from django.conf import settings

    config = settings.DATABASES["default"]
    if config["ENGINE"] != "django.db.backends.postgresql" or config.get("HOST", "") not in ("", "localhost", "127.0.0.1", "::1"):
        raise RuntimeError("Pilot requires the explicitly local PostgreSQL game database.")
    django.setup()
    import evennia
    evennia._init()
    from django.db import connection

    with connection.cursor() as cursor:
        cursor.execute("SELECT current_database(), host(inet_server_addr()), current_schema()")
        database, address, schema = cursor.fetchone()
    if address not in (None, "127.0.0.1", "::1") or schema != "public":
        raise RuntimeError("Local public game database identity check failed.")
    return connection, config, database


def fingerprint(connection):
    """Hash every gameplay row, object and object-linked attribute by primary key."""
    tables = {}
    with connection.cursor() as cursor:
        cursor.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename LIKE 'pokemon_%' ORDER BY tablename")
        names = [row[0] for row in cursor.fetchall()]
        names.append("objects_objectdb")
        for name in names:
            cursor.execute("SELECT a.attname FROM pg_index i JOIN pg_attribute a ON a.attrelid=i.indrelid AND a.attnum=ANY(i.indkey) WHERE i.indrelid=%s::regclass AND i.indisprimary", [name])
            columns = [row[0] for row in cursor.fetchall()]
            if len(columns) != 1:
                raise RuntimeError("Expected a single primary key for " + name)
            cursor.execute("SELECT to_jsonb(t) FROM " + connection.ops.quote_name(name) + " t")
            rows = [json.loads(row[0]) if isinstance(row[0], str) else row[0] for row in cursor.fetchall()]
            tables[name] = {str(row[columns[0]]): sha(row) for row in rows}
        cursor.execute("SELECT a.id, to_jsonb(a) FROM typeclasses_attribute a JOIN objects_objectdb_db_attributes link ON link.attribute_id=a.id")
        tables["object_attributes"] = {str(pk): sha(row) for pk, row in cursor.fetchall()}
    return tables


def compare_fingerprints(before, after):
    """Report updates/deletions of baseline records; new QA rows are permitted."""
    changes = []
    for table, rows in before.items():
        current = after.get(table, {})
        for pk, digest in rows.items():
            if current.get(pk) != digest:
                changes.append({"table": table, "pk": pk,
                                "change": "missing" if pk not in current else "modified"})
    return changes


def backup_database(output, config):
    """Create and inspect a custom-format pg_dump without putting secrets in argv."""
    binary = Path("C:/Program Files/PostgreSQL/16/bin")
    backup = output / "before-qa.dump"
    environment = dict(os.environ)
    environment["PGPASSWORD"] = str(config.get("PASSWORD", ""))
    command = [str(binary / "pg_dump.exe"), "--format=custom", "--file", str(backup),
               "--host", config.get("HOST") or "localhost", "--dbname", config["NAME"]]
    for flag, key in (("--username", "USER"), ("--port", "PORT")):
        if config.get(key):
            command.extend([flag, str(config[key])])
    result = subprocess.run(command, env=environment, capture_output=True)
    if result.returncode:
        raise RuntimeError("Local pg_dump failed; no QA fixtures were created.")
    listing = subprocess.check_output([str(binary / "pg_restore.exe"), "--list", str(backup)])
    if not backup.stat().st_size or b"pokemon_ownedpokemon" not in listing:
        raise RuntimeError("Database backup verification failed.")
    (output / "backup-contents.txt").write_bytes(listing)
    return {"path": str(backup), "bytes": backup.stat().st_size,
            "sha256": hashlib.sha256(backup.read_bytes()).hexdigest(), "list_verified": True}


def prepare(output):
    """Back up protected data, then create three new accounts and a private room."""
    from live_battle_pilot_server import load_manifest

    if output.exists():
        raise RuntimeError("Choose a new output directory; preparation never overwrites a run.")
    output.mkdir(parents=True)
    connection, config, database = configure_database()
    backup = backup_database(output, config)
    before = fingerprint(connection)
    save(output / "protected-baseline.json", before)
    status = subprocess.check_output(["git", "status", "--porcelain"], cwd=REPO).decode()
    wip = {}
    for line in status.splitlines():
        file = REPO / line[3:]
        if file.is_file() and not (line[3:].startswith("tools/live_battle_pilot")
                                   or line[3:] == "tests/test_live_battle_pilot.py"):
            wip[line[3:]] = hashlib.sha256(file.read_bytes()).hexdigest()
    save(output / "source-baseline.json", {"head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO).decode().strip(), "status": status, "wip": wip})
    log_offsets = {}
    for file in (REPO / "server/logs").glob("*.log"):
        log_offsets[str(file)] = file.stat().st_size
    save(output / "log-offsets.json", log_offsets)
    from django.db import transaction
    from evennia.accounts.models import AccountDB
    from evennia.objects.models import ObjectDB
    from evennia.utils.create import create_account, create_object

    from pokemon.models.storage import UserStorage
    from pokemon.models.trainer import Trainer

    token = secrets.token_hex(4)
    data = {"tag": "battle-pilot-" + token, "database": database, "players": {},
            "baseline_max_object_id": max(ObjectDB.objects.values_list("pk", flat=True)),
            "baseline_max_account_id": max(AccountDB.objects.values_list("pk", flat=True)),
            "backup": backup, "created_utc": datetime.now(timezone.utc).isoformat()}
    credentials = {}
    credential_path = Path(tempfile.gettempdir()) / ("fusion2-" + data["tag"] + "-credentials.json")
    with transaction.atomic():
        room = create_object("typeclasses.rooms.FusionRoom", key="Private Battle Pilot " + token)
        room.db.battle_pilot_tag = data["tag"]
        room.db.desc = "Private automated local battle fixtures. No exits or public encounter changes."
        data["room_id"] = room.pk
        for label in ("a", "b", "staff"):
            name = "Pilot" + label.title() + token
            password = secrets.token_urlsafe(32)
            perms = ["Developer"] if label == "staff" else ["Player"]
            account = create_account(name, email=None, password=password, permissions=perms,
                                     typeclass="typeclasses.accounts.Account")
            if label == "staff":
                account.is_superuser = account.is_staff = True
                account.save(update_fields=["is_superuser", "is_staff"])
            player, errors = account.create_character(key=name, location=room, home=room, permissions=perms)
            if not player or errors:
                raise RuntimeError("QA character creation failed.")
            player.db.battle_pilot_tag = data["tag"]
            player.db.chargen_complete = True
            identity = {"name": name, "id": player.pk, "account_id": account.pk}
            if label != "staff":
                trainer, _ = Trainer.objects.get_or_create(user=player, defaults={"trainer_number": 910000 + player.pk})
                UserStorage.objects.get_or_create(user=player)
                identity["trainer_id"] = trainer.pk
            data["players"][label] = identity
            credentials[label] = {"account": name, "password": password}
        credential_path.write_text(json.dumps(credentials), encoding="utf-8")
        data["credential_path"] = str(credential_path)
        save(output / "manifest.json", data)
        load_manifest(output / "manifest.json")
    changes = compare_fingerprints(before, fingerprint(connection))
    save(output / "after-preparation-safety.json", {"protected_rows_unchanged": not changes, "changes": changes})
    if changes:
        raise RuntimeError("Protected records changed during preparation; stop and inspect.")
    print(json.dumps({"prepared": True, "manifest": str(output / "manifest.json"),
                      "players": data["players"], "room_id": room.pk, "backup": backup,
                      "protected_rows_unchanged": True}), flush=True)


class TelnetClient:
    """A real localhost client with incremental Telnet parsing and redacted logs."""

    def __init__(self, label, credential, output, port, all_secrets):
        self.label, self.credential, self.output = label, credential, output
        self.port, self.all_secrets = port, all_secrets
        self.sock = None
        self.pending = b""

    def record(self, command, output):
        """Persist command-level evidence with every pilot password removed."""
        for secret in self.all_secrets:
            command, output = command.replace(secret, "[REDACTED]"), output.replace(secret, "[REDACTED]")
        row = {"time_utc": datetime.now(timezone.utc).isoformat(), "client": self.label,
               "command": command, "output": output}
        with (self.output / "transcript.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")
        return output

    def parse(self, data):
        """Strip negotiations while preserving fragmented Telnet control sequences."""
        data = self.pending + data
        self.pending = b""
        payload, index = bytearray(), 0
        while index < len(data):
            if data[index] != 255:
                payload.append(data[index])
                index += 1
                continue
            if index + 1 >= len(data):
                self.pending = data[index:]
                break
            command = data[index + 1]
            if command == 255:
                payload.append(255)
                index += 2
            elif command in (251, 252, 253, 254):
                if index + 2 >= len(data):
                    self.pending = data[index:]
                    break
                if command in (251, 253):
                    self.sock.sendall(bytes((255, 254 if command == 251 else 252, data[index + 2])))
                index += 3
            elif command == 250:
                end = data.find(b"\xff\xf0", index + 2)
                if end < 0:
                    self.pending = data[index:]
                    break
                index = end + 2
            else:
                index += 2
        return bytes(payload)

    def read(self, timeout=5, quiet=.35, marker=None):
        """Wait for a complete staff response or an ordinary-player quiet interval."""
        deadline, last = time.monotonic() + timeout, time.monotonic()
        payload = bytearray()
        while time.monotonic() < deadline:
            if select.select([self.sock], [], [], .05)[0]:
                data = self.sock.recv(65536)
                if not data:
                    raise ConnectionError("Local game closed the QA connection.")
                payload.extend(self.parse(data))
                last = time.monotonic()
            if marker and marker.encode() in bytes(payload).replace(b"\r", b""):
                break
            if not marker and payload and time.monotonic() - last >= quiet:
                break
        return re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", payload.decode("utf-8", errors="replace")).replace("\r", "")

    def send(self, command, label=None, marker=None):
        """Send exactly one command and record the response."""
        self.sock.sendall((command + "\r\n").encode("utf-8"))
        options = {"timeout": 15} if marker else {}
        return self.record(label or command, self.read(marker=marker, **options))

    def open(self):
        """Log into this run's new account and puppet only its own character."""
        self.sock = socket.create_connection(("127.0.0.1", self.port), timeout=5)
        self.record("[OPEN localhost]", self.read())
        self.send(f"connect {self.credential['account']} {self.credential['password']}", "[LOGIN own QA account]")
        self.send("goic " + self.credential["account"])

    def close(self):
        """Close this runner's socket only."""
        if self.sock:
            self.sock.close()
            self.sock = None


class StaffAPI:
    """Invoke only the narrow fixture module through the dedicated QA staff login."""

    def __init__(self, client, manifest, module_path=None):
        self.client, self.manifest = client, str(manifest)
        module = str(module_path or REPO / "tools/live_battle_pilot_server.py")
        ready = "PF2PILOT_READY_" + secrets.token_hex(8)
        command = ("@py import importlib.util; _ps=importlib.util.spec_from_file_location('pf2_pilot_staff', "
                   + repr(module) + "); _pm=importlib.util.module_from_spec(_ps); _ps.loader.exec_module(_pm); "
                   "me.ndb.battle_pilot_module=_pm; print('PF2PILOT_' + " + repr(ready.removeprefix("PF2PILOT_")) + ")")
        response = client.send(command, "[STAFF load isolated pilot helper]", marker=ready)
        if not re.search(r"(?m)^" + re.escape(ready) + r"$", response):
            raise RuntimeError("Staff helper could not load; see redacted transcript.")

    def call(self, action, payload=None):
        """Return a framed JSON observation, rejecting failed or truncated responses."""
        token = "PF2PILOT_" + secrets.token_hex(8)
        marker = ":END" + token
        command = ("@py import json; print(" + repr(token + ":") + " + json.dumps(me.ndb.battle_pilot_module.dispatch("
                   + repr(self.manifest) + ", " + repr(action) + ", " + repr(payload or {})
                   + "), default=str) + ':END' + " + repr(token) + ")")
        response = self.client.send(command, "[STAFF " + action + "]", marker=marker)
        match = re.search(r"(?m)^" + re.escape(token) + r":(\{[^\n]*\})" + re.escape(marker) + r"$", response)
        if not match:
            raise RuntimeError("Staff " + action + " did not return complete evidence; see transcript.")
        return json.loads(match.group(1))


def stage(mon, name):
    """Read conventional or long-form stat-stage keys."""
    aliases = {"atk": "attack", "def": "defense", "spa": "special_attack",
               "spd": "special_defense", "spe": "speed"}
    return mon["boosts"].get(name, mon["boosts"].get(aliases.get(name, name), 0))


def evaluate(case, snapshots, text):
    """Assert explicit behavioral outcomes from independently observed state."""
    start, end = snapshots[0], snapshots[-1]
    def active(state, side="A", index=0):
        return state["battle"]["sides"][side]["active"][index]
    def hp(state, side="A", index=0):
        return active(state, side, index)["hp"]
    def check(condition, message):
        if not condition:
            raise AssertionError(message)
    kind = case.check
    if kind == "damage_pp":
        check(hp(end, "B") < hp(start, "B"), "Tackle did not reduce target HP")
        before = start["players"]["a"]["pokemon"][0]["moves"][0]["current_pp"]
        after = end["players"]["a"]["pokemon"][0]["moves"][0]["current_pp"]
        check(after == before - 1, f"Expected PP {before - 1}, observed {after}")
    elif kind == "type_immunity":
        check(hp(end) == hp(start) and hp(end, "B") == hp(start, "B"), "Immune attack changed HP")
    elif kind == "stat_drop":
        check(stage(active(end, "B"), "atk") == -1, "Growl did not set target Attack stage to -1")
    elif kind == "self_boost":
        check(stage(active(end), "atk") == 2, "Swords Dance did not set Attack stage to +2")
    elif kind in {"recover", "water_absorb", "leftovers"}:
        divisor = {"recover": 2, "water_absorb": 4, "leftovers": 16}[kind]
        maximum = active(start)["max_hp"]
        expected = min(maximum, hp(start) + max(1, maximum // divisor))
        check(hp(end) == expected, f"Expected HP {expected}, observed {hp(end)}")
    elif kind in {"burn", "paralysis"}:
        expected = "brn" if kind == "burn" else "par"
        check(active(end, "B")["status"] == expected, f"Expected status {expected}, observed {active(end, 'B')['status']}")
        if kind == "burn":
            check(hp(end, "B") < hp(start, "B"), "Burn did not cause residual HP loss")
    elif kind in {"protect", "levitate", "flash_fire"}:
        check(hp(end) == hp(start), "Expected incoming attack to cause zero HP loss")
        if kind == "protect":
            check("protect" in text.lower(), "Protection was not shown to the players")
        if kind == "flash_fire":
            check(all(active(state)["ability_state"].get("flashfire") is True for state in snapshots[1:]),
                  "Flash Fire boost state was not retained after each turn")
            check(hp(end, "B") < hp(start, "B"), "The armed holder did not execute its next Fire attack")
        if kind == "levitate":
            before = start["players"]["b"]["pokemon"][0]["moves"][0]["current_pp"]
            after = end["players"]["b"]["pokemon"][0]["moves"][0]["current_pp"]
            check(after == before - 1, "The Ground move was not actually attempted")
    elif kind == "intimidate":
        check(stage(active(start, "B"), "atk") == -1, "Intimidate did not lower opposing Attack on entry")
    elif kind == "stealth_rock":
        mon = active(end, "B")
        check("Charizard" in mon["species"], "Party slot 2 did not switch in")
        check(mon["hp"] == mon["max_hp"] - mon["max_hp"] // 2, "Expected half maximum HP lost to Stealth Rock")
    elif kind == "switch":
        check(active(end)["id"].removeprefix("owned:") == start["players"]["a"]["pokemon"][1]["id"], "Canonical slot 2 did not become active")
        check(len(end["players"]["a"]["pokemon"]) == 2, "Switch changed party ownership")
    elif kind == "fly":
        check(hp(snapshots[1], "B") == hp(start, "B"), "Fly damaged its target on the charging turn")
        check(hp(end, "B") < hp(start, "B"), "Fly did not damage its target on the second turn")
        check("fly" not in active(end)["volatiles"], "Fly retained its charge after the strike")
        before_pp = start["players"]["a"]["pokemon"][0]["moves"][0]["current_pp"]
        after_pp = end["players"]["a"]["pokemon"][0]["moves"][0]["current_pp"]
        check(after_pp == before_pp - 1, "Fly did not spend exactly one PP for its two turns")
    elif kind == "doubles":
        for index in (0, 1):
            check(hp(end, "B", index) < hp(start, "B", index), f"Surf did not hit opposing slot {index + 1}")
        mon = active(start, "A", 1)
        check(hp(end, "A", 1) == min(mon["max_hp"], mon["hp"] + mon["max_hp"] // 4), "Ally Water Absorb did not heal correctly")
    elif kind in {"flee", "capture"}:
        check(end["battle"] is None and not end["players"]["a"]["battle_lock"], "Battle did not end and clear locks")
        if kind == "flee":
            check("fled" in text.lower(), "Successful escape was not shown to the player")
        else:
            before_ids = {mon["id"] for mon in start["players"]["a"]["pokemon"]}
            caught = [mon for mon in end["players"]["a"]["pokemon"] if mon["id"] not in before_ids]
            check(len(caught) == 1 and caught[0]["species"] == "Rattata", "Capture did not create exactly one owned Rattata")
            check(any(str(p["pokemon_id"]) == caught[0]["id"] for p in end["players"]["a"]["placements"]), "Captured Pokemon lacks canonical placement")
            check(not any(row["item_name"] == "Master Ball" and row["quantity"] > 0 for row in end["players"]["a"]["inventory"]), "Master Ball was not consumed")
    elif kind == "trainer_flee":
        check(end["battle"] is not None and end["players"]["a"]["battle_lock"], "Flee incorrectly ended the trainer battle")
        check("flee" in text.lower() or "run" in text.lower(), "Flee attempt was not observable")
    else:
        raise ValueError("Missing expected-outcome evaluator: " + kind)


def review_failure(case, snapshots, text):
    """Gather rule/precondition evidence without declaring every mismatch a bug."""
    markers = ("missed", "protected itself", "unable to move", "can't use", "no pp", "immune", "trapped")
    messages = sorted({line.strip() for line in text.splitlines()
                       if any(marker in line.lower() for marker in markers)})
    conditions = []
    for index, state in enumerate(snapshots):
        battle = state.get("battle")
        if not battle:
            continue
        for side, part in battle["sides"].items():
            for mon in part["active"]:
                conditions.append({"observation": index, "side": side, "species": mon["species"],
                                   "hp": mon["hp"], "status": mon["status"],
                                   "ability": mon["ability"], "ability_state": mon["ability_state"],
                                   "volatiles": mon["volatiles"], "moves": mon["moves"],
                                   "diagnostic_flags": mon.get("diagnostic_flags", {}),
                                   "field": battle.get("field", {})})
    return {"classification": "possible_expected_failure" if messages else "requires_diagnosis",
            "confirmed_game_defect": False, "seed": case.seed,
            "expected_failure_conditions": list(case.failure_conditions),
            "observed_blocker_messages": messages, "preconditions_and_outcomes": conditions,
            "required_review": "Check intended rules, fixture/runner validity and RNG; reproduce with fresh fixtures before changing mechanics. A failed assertion alone does not confirm a game defect."}


class PilotRunner:
    """Run independent scenarios and retain evidence even when an outcome fails."""

    def __init__(self, manifest, port, server_helper=None):
        from live_battle_pilot_server import load_manifest
        self.manifest, self.data = load_manifest(manifest)
        self.output = self.manifest.parent
        credentials = json.loads(Path(self.data["credential_path"]).read_text(encoding="utf-8"))
        passwords = [entry["password"] for entry in credentials.values()]
        self.clients = {label: TelnetClient(label, entry, self.output, port, passwords)
                        for label, entry in credentials.items()}
        self.api = None
        self.server_helper = server_helper

    def clean(self):
        """Prefer normal player concession; separately record any staff fallback."""
        state = self.api.call("snapshot")
        outputs = []
        if state["battle"]:
            outputs.append(self.clients["a"].send("+concede yes"))
            self.clients["b"].record("[RECEIVE other player's concession]", self.clients["b"].read(timeout=.6, quiet=.15))
        result = self.api.call("finish")
        if "nickname" in " ".join(outputs).lower():
            self.clients["a"].send("no")
        return result

    def run_case(self, case):
        """Prepare fixtures, fight through player sessions, and evaluate observations."""
        result = {"key": case.key, "purpose": case.purpose, "expected": case.expected,
                  "mode": case.mode, "seed": case.seed, "status": "blocked", "snapshots": [], "outputs": []}
        try:
            result["preparation"] = self.api.call("setup", {"a": [asdict(mon) for mon in case.a],
                                                           "b": [asdict(mon) for mon in case.b],
                                                           "inventory": case.inventory})
            if case.mode in {"single", "double"}:
                for label, command in (("a", "+pvp/create " + case.mode),
                                       ("b", "+pvp/join " + self.data["players"]["a"]["name"]),
                                       ("a", "+pvp/start")):
                    result["outputs"].append(self.clients[label].send(command))
            else:
                name = self.data["players"]["a"]["name"]
                result["outputs"].append(self.clients["staff"].send(f"@testbattle/start {name}={case.opponent}, 5, {case.mode}"))
            self.api.call("seed", {"seed": case.seed})
            state = self.api.call("snapshot")
            if not state["battle"]:
                raise RuntimeError("Normal battle entry failed.")
            result["snapshots"].append(state)
            for commands in case.turns:
                for label, command in commands:
                    result["outputs"].append(self.clients[label].send(command))
                for label in ("a", "b"):
                    result["outputs"].append(self.clients[label].record("[RECEIVE turn result]", self.clients[label].read(timeout=.6, quiet=.15)))
                observed = self.api.call("snapshot")
                previous = result["snapshots"][-1]
                result["snapshots"].append(observed)
                if case.mode in {"single", "double"} and observed["battle"]:
                    if observed["battle"]["turn"] <= previous["battle"]["turn"]:
                        raise AssertionError("Player commands did not advance a complete battle turn.")
            evaluate(case, result["snapshots"], "\n".join(result["outputs"]))
            result["status"] = "passed"
        except AssertionError as error:
            result["status"], result["error"] = "failed", str(error)
            result["failure_review"] = review_failure(case, result["snapshots"], "\n".join(result["outputs"]))
        except Exception as error:
            result["error"] = str(error)
        finally:
            try:
                if case.check == "capture" and "nickname" in "\n".join(result["outputs"]).lower():
                    self.clients["a"].send("no")
                result["cleanup"] = self.clean()
                if result["cleanup"]["staff_cleanup_required"]:
                    result["status"] = "failed"
                    result["cleanup_error"] = "Normal concession did not finish the QA battle; staff cleanup was required."
            except Exception as error:
                result["cleanup_error"] = str(error)
                result["status"] = "blocked"
            save(self.output / (case.key + ".json"), result)
            attempts = self.output / "attempts"
            attempts.mkdir(exist_ok=True)
            save(attempts / (case.key + "-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f") + ".json"), result)
        return result

    def run(self, selected):
        """Always close only our clients; stop on a cleanup failure."""
        results_path = self.output / "results.json"
        results = json.loads(results_path.read_text(encoding="utf-8")) if results_path.exists() else []
        try:
            for label in ("staff", "a", "b"):
                self.clients[label].open()
            self.api = StaffAPI(self.clients["staff"], self.manifest, self.server_helper)
            self.clean()
            for case in SCENARIOS:
                if selected and case.key not in selected:
                    continue
                if not selected and any(item["key"] == case.key and item["status"] == "passed" for item in results):
                    continue
                result = self.run_case(case)
                results = [item for item in results if item["key"] != case.key]
                results.append({key: result[key] for key in ("key", "purpose", "status", "expected")}
                               | {key: result[key] for key in ("error", "cleanup_error") if key in result})
                save(self.output / "results.json", results)
                print(json.dumps(results[-1]), flush=True)
                if "cleanup_error" in result and result["status"] == "blocked":
                    break
        finally:
            for client in self.clients.values():
                client.close()
        write_report(self.output)
        return results


def write_report(output):
    """Publish a compact index of latest outcomes and separately recorded safety."""
    path = output / "results.json"
    if not path.exists():
        return
    results = json.loads(path.read_text(encoding="utf-8"))
    by_key = {item["key"]: item for item in results}
    counts = {status: sum(item["status"] == status for item in results)
              for status in ("passed", "failed", "blocked")}
    lines = ["# Local logged-in battle pilot", "",
             f"Latest observations: {counts['passed']} passed, {counts['failed']} failed, "
             f"{counts['blocked']} blocked; {20 - len(results)} untested.", "",
             "Two ordinary QA players issued normal commands through localhost Telnet. "
             "A separate QA staff session prepared teams and observed state. "
             "These results cover the declared scenarios, not the whole dex or production readiness.", "",
             "| Scenario | Result | Observation |", "| --- | --- | --- |"]
    for case in SCENARIOS:
        result = by_key.get(case.key, {})
        observation = result.get("error", result.get("cleanup_error", case.expected))
        lines.append(f"| [{case.key}]({case.key}.json) | {result.get('status', 'untested')} | {observation.replace('|', '/')} |")
    safety_path = output / "safety-verification.json"
    if safety_path.exists():
        safety = json.loads(safety_path.read_text(encoding="utf-8"))
        lines += ["", f"Protected baseline rows: {safety['protected_baseline_rows']}. "
                  f"All unchanged: {safety['protected_rows_unchanged']}. "
                  f"Existing source WIP unchanged: {safety['wip_unchanged']}.",
                  f"New server log error lines: {len(safety['new_log_error_lines'])}."]
    lines += ["", "Evidence: [transcript](transcript.jsonl), [latest results](results.json), "
              "[safety](safety-verification.json), and timestamped attempts in `attempts/`."]
    lines += ["", "A failed assertion is a scenario mismatch, not automatically a mechanics defect. "
              "Review the per-case `failure_review`, intended rules, preconditions, RNG and fresh "
              "reproductions before changing gameplay; valid failures must remain valid."]
    if (output / "accounts-disabled.json").exists():
        lines += ["", "All three QA accounts are disabled, their passwords invalidated, "
                  "and temporary staff privileges removed in the running server. "
                  "Only the final QA teams and private room remain for inspection."]
    (output / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def audit_passed_evidence(output):
    """Re-evaluate retained passes, including evidence created by an earlier runner."""
    path = output / "results.json"
    if not path.exists():
        return {"audited_passes": 0, "errors": []}
    results = json.loads(path.read_text(encoding="utf-8"))
    by_key = {case.key: case for case in SCENARIOS}
    audited, errors = 0, []
    for result in results:
        if result["status"] != "passed":
            continue
        try:
            case = by_key[result["key"]]
            evidence = json.loads((output / (case.key + ".json")).read_text(encoding="utf-8"))
            snapshots = evidence["snapshots"]
            if len(snapshots) != len(case.turns) + 1:
                raise AssertionError("Missing initial or post-turn observation")
            if not all(player["ordinary"] for state in snapshots for player in state["players"].values()):
                raise AssertionError("Battling account was not ordinary")
            if case.mode in {"single", "double"}:
                for previous, current in zip(snapshots, snapshots[1:]):
                    if current["battle"] and current["battle"]["turn"] <= previous["battle"]["turn"]:
                        raise AssertionError("Commands did not advance a full turn")
            evaluate(case, snapshots, "\n".join(evidence["outputs"]))
            if evidence["cleanup"].get("staff_cleanup_required") or evidence.get("cleanup_error"):
                raise AssertionError("Normal player cleanup did not pass")
            audited += 1
        except Exception as error:
            errors.append({"key": result["key"], "error": str(error)})
    return {"audited_passes": audited, "errors": errors}


def verify(output):
    """Verify pre-existing data/WIP and inspect only new log bytes."""
    connection, _, _ = configure_database()
    before = json.loads((output / "protected-baseline.json").read_text(encoding="utf-8"))
    changes = compare_fingerprints(before, fingerprint(connection))
    baseline = json.loads((output / "source-baseline.json").read_text(encoding="utf-8"))
    wip = {name: (REPO / name).is_file() and hashlib.sha256((REPO / name).read_bytes()).hexdigest() == digest
           for name, digest in baseline["wip"].items()}
    offsets = json.loads((output / "log-offsets.json").read_text(encoding="utf-8"))
    errors = []
    for name, offset in offsets.items():
        file = Path(name)
        with file.open("rb") as stream:
            stream.seek(offset)
            text = stream.read().decode("utf-8", errors="replace")
        for line in text.splitlines():
            if re.search(r"Traceback|\[EE\]|Unhandled|CRITICAL", line):
                errors.append({"file": file.name, "line": line[:500]})
    result = {"protected_rows_unchanged": not changes, "protected_baseline_rows": sum(map(len, before.values())),
              "protected_changes": changes, "wip_unchanged": all(wip.values()),
              "wip_files": wip, "new_log_error_lines": errors,
              "evidence_audit": audit_passed_evidence(output)}
    save(output / "safety-verification.json", result)
    write_report(output)
    print(json.dumps(result, indent=2))
    return result


def disable(manifest, port=4000, write_summary=True):
    """Disable only this run's accounts and remove the temporary staff privileges."""
    from live_battle_pilot_server import load_manifest

    manifest, data = load_manifest(manifest)
    credentials = json.loads(Path(data["credential_path"]).read_text(encoding="utf-8"))
    passwords = [entry["password"] for entry in credentials.values()]
    clients = {label: TelnetClient(label, entry, manifest.parent, port, passwords)
               for label, entry in credentials.items()}
    try:
        # The same live ownership checks as a battle run require all three
        # characters to be puppeted by their own accounts during this action.
        for label in ("staff", "a", "b"):
            clients[label].open()
        result = StaffAPI(clients["staff"], manifest).call("disable")
    finally:
        for client in clients.values():
            client.close()
    Path(data["credential_path"]).unlink(missing_ok=True)
    result["credential_file_removed"] = True
    save(manifest.parent / "accounts-disabled.json", result)
    if write_summary:
        write_report(manifest.parent)
    print(json.dumps({"qa_accounts_disabled": True, "staff_privileges_removed": True}))


def main():
    """Dispatch explicit local-only preparation, execution and verification steps."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "run", "verify", "disable", "catalog"))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--port", type=int, default=4000)
    parser.add_argument("--case", action="append", default=[])
    args = parser.parse_args()
    if args.action == "catalog":
        print(json.dumps([asdict(case) for case in SCENARIOS], indent=2))
        return
    if args.output is None:
        parser.error("--output is required")
    output = args.output.resolve()
    if not output.is_relative_to(ARTIFACTS) or output == ARTIFACTS:
        parser.error("--output must name a run directory inside this checkout's .codex-artifacts")
    if args.case and set(args.case) - {case.key for case in SCENARIOS}:
        parser.error("Unknown scenario key")
    if args.action == "prepare":
        prepare(output)
    elif args.action == "run":
        with run_lock(output):
            results = PilotRunner(output / "manifest.json", args.port).run(set(args.case))
        if any(item["status"] != "passed" for item in results):
            raise SystemExit(1)
    elif args.action == "verify":
        result = verify(output)
        if not result["protected_rows_unchanged"] or not result["wip_unchanged"] or result["evidence_audit"]["errors"]:
            raise SystemExit(1)
    elif args.action == "disable":
        with run_lock(output):
            disable(output / "manifest.json", args.port)


if __name__ == "__main__":
    main()
