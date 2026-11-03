"""Bounded ordinary-player Telnet acceptance in task-owned game processes.

Requires an explicit PF2_TEST_POSTGRES_DSN. Creates production model tables in
a disposable schema without migrations. No shared game processes are touched.
"""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import socket
import subprocess
import sys
import telnetlib
import time
import traceback
from pathlib import Path

from isolated_postgres import IsolatedPostgres

REPO = Path(__file__).resolve().parents[2]


def free_port():
    """Choose a loopback port for a new fixture, never an existing game port."""
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


class SocketAcceptance:
    """Run real account login, character commands and reconnect over Telnet/AMP."""

    def __init__(self):
        from psycopg2.extensions import parse_dsn

        self.database = IsolatedPostgres()
        self.root = REPO.parent / ".codex-artifacts" / "nov-w1-20261102" / ("socket-" + secrets.token_hex(6))
        self.root.mkdir(parents=True)
        self.telnet_port, self.amp_port = free_port(), free_port()
        self.children, self.streams, self.clients = [], [], []
        self.report = {"status": "starting", "events": [], "checks": [], "schema": self.database.schema,
                       "limits": ["Disposable schema and task-owned Portal/Server; production model tables without migrations",
                                  "Fixture-only characters, rooms and parties; no shared world or deployment proof",
                                  "No clock patch, staff gameplay, or battle/result failure injection"]}
        params = parse_dsn(self.database.dsn)
        database = {"ENGINE": "django.db.backends.postgresql", "NAME": params.get("dbname", "postgres"),
                    "USER": params.get("user", ""), "PASSWORD": params.get("password", ""),
                    "HOST": params.get("host", ""), "PORT": params.get("port", ""), "CONN_MAX_AGE": 0,
                    "OPTIONS": {"options": self.database.options, "connect_timeout": 5}}
        settings = (
            "import ast, pathlib\n"
            + "_source = pathlib.Path(" + repr(str(REPO / "server/conf/settings.py")) + ")\n"
            + "_tree = ast.parse(_source.read_text(encoding='utf-8'), filename=str(_source))\n"
            + "_tree.body = [node for node in _tree.body if not (isinstance(node, ast.Try) and any(isinstance(child, ast.ImportFrom) and child.module == 'server.conf.secret_settings' for child in ast.walk(node)))]\n"
            + "exec(compile(_tree, str(_source), 'exec'), globals())\n"
            + "DATABASES = " + repr({"default": database}) + "\n"
            + "GAME_DIR = " + repr(str(self.root)) + "\nLOG_DIR = GAME_DIR\nSTATIC_ROOT = GAME_DIR + '/static'\n"
            + "SECRET_KEY = " + repr(secrets.token_hex(32)) + "\n"
            + f"TELNET_PORTS = [{self.telnet_port}]\nAMP_PORT = {self.amp_port}\n"
            + "TELNET_INTERFACES = ['127.0.0.1']\nAMP_INTERFACE = AMP_HOST = '127.0.0.1'\n"
            + "SERVERNAME = 'Private Adventure acceptance'\nLOCKDOWN_MODE = True\n"
            + "WEBSERVER_ENABLED = WEBCLIENT_ENABLED = WEBSOCKET_CLIENT_ENABLED = False\n"
            + "SSL_ENABLED = SSH_ENABLED = False\nTELNET_ENABLED = True\n"
            + "DEV_MODE = ALPHA_TEST_COMMANDS_ENABLED = False\nGLOBAL_SCRIPTS = {}\n"
            + "SERVER_SERVICES_PLUGIN_MODULES = []\nPORTAL_SERVICES_PLUGIN_MODULES = []\n"
            + "AT_SERVER_STARTSTOP_MODULE = SERVER_STARTSTOP_MODULE = 'pf2_adventure_socket_hooks'\n"
            + "CACHES = {key: {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache', 'LOCATION': 'private-' + key} for key in ('default', 'throttle')}\n"
            + "TEST_ENVIRONMENT = False\n")
        for name in ("SERVER_LOG_FILE", "PORTAL_LOG_FILE", "HTTP_LOG_FILE", "LOCKWARNING_LOG_FILE"):
            settings += name + " = " + repr(str(self.root / (name.lower() + ".log"))) + "\n"
        (self.root / "pf2_adventure_socket_settings.py").write_text(settings, encoding="utf-8")
        hooks = '"""Fixture hooks deliberately omit shared-world startup work."""\n'
        for name in ("at_server_init", "at_server_start", "at_server_stop", "at_server_cold_start",
                     "at_server_cold_stop", "at_server_reload_start", "at_server_reload_stop"):
            hooks += f"def {name}():\n    pass\n"
        (self.root / "pf2_adventure_socket_hooks.py").write_text(hooks, encoding="utf-8")
        sys.path.insert(0, str(self.root))
        os.environ["DJANGO_SETTINGS_MODULE"] = "pf2_adventure_socket_settings"

    def save(self):
        """Save redacted command-level evidence throughout the bounded run."""
        (self.root / "evidence.json").write_text(json.dumps(self.report, indent=2, default=str), encoding="utf-8")

    def check(self, name, condition):
        """Stop at the first failed player/state assertion with its transcript intact."""
        self.report["checks"].append({"name": name, "passed": bool(condition)})
        self.save()
        assert condition, name

    def read(self, client, seconds=0.6):
        """Read the actual socket response without interpreting game behavior."""
        deadline, output = time.monotonic() + seconds, []
        while time.monotonic() < deadline:
            try:
                chunk = client.read_very_eager()
            except EOFError:
                break
            if chunk:
                output.append(chunk.decode("utf-8", errors="replace"))
            time.sleep(0.03)
        return "".join(output)

    def send(self, client, command, *, private=False, seconds=0.7):
        """Execute one ordinary command and retain its response before proceeding."""
        client.write(command.encode("utf-8") + b"\r\n")
        output = self.read(client, seconds)
        self.report["events"].append({"command": "connect <fixture credentials>" if private else command,
                                      "output": output})
        self.save()
        assert "Traceback (most recent call last)" not in output, output
        return output

    def login(self, credentials, character):
        """Authenticate an ordinary account and puppet its actual fixture character."""
        client = telnetlib.Telnet("127.0.0.1", self.telnet_port, timeout=3)
        self.clients.append(client)
        self.read(client, 1)
        self.send(client, "connect " + " ".join(credentials), private=True, seconds=1.5)
        self.send(client, "goic " + character.key, seconds=1.5)
        self.send(client, "look")
        return client

    def run(self):
        """Set up fixtures, then exercise gameplay solely through socket commands."""
        self.database.__enter__()
        self.database.create_model_tables()
        import evennia
        from django.apps import apps
        from django.conf import settings
        from django.contrib.contenttypes.models import ContentType
        from evennia.accounts.models import AccountDB
        from evennia.server import initial_setup
        from evennia.server.models import ServerConfig

        from pokemon.helpers.pokemon_helpers import create_owned_pokemon
        from pokemon.models.adventures import AdventureSession
        from pokemon.models.core import EncounterPokemon
        from pokemon.services.battle_rewards import BattleRewards

        ContentType.objects.get_for_models(*apps.get_models(), for_concrete_models=False)
        evennia._init()
        AccountDB.objects.create_superuser("PrivateSetup", password=secrets.token_urlsafe(32))
        settings.TEST_ENVIRONMENT = True
        initial_setup.handle_setup()
        settings.TEST_ENVIRONMENT = False
        assert ServerConfig.objects.conf("last_initial_setup_step") == "done"
        accounts, credentials, players = [], [], []
        for i in range(2):
            pair = ("Adventure" + secrets.token_hex(4), secrets.token_urlsafe(24))
            account = evennia.create_account(*pair[:1], email="fixture@example.invalid", password=pair[1],
                                             permissions=["Player"], typeclass="typeclasses.accounts.Account")
            accounts.append(account)
            credentials.append(pair)
            for j in range(2 if i == 0 else 1):
                player, errors = account.create_character(key="AdventurePlayer" + secrets.token_hex(4))
                assert not errors, errors
                player.permissions.add("Player")
                player.db.validated, player.db.chargen_completed = True, True
                create_owned_pokemon("Squirtle", player.trainer, 20, nature="Hardy", ivs=[0] * 6, evs=[0] * 6,
                                     active_move_names=["Watergun"])
                players.append(player)
        owner, sibling, outsider = players
        hall = evennia.create_object("typeclasses.rooms.FusionRoom", key="Private Adventure Hall", nohome=True)
        rooms = [evennia.create_object("typeclasses.rooms.FusionRoom", key="Private Instance " + str(i), nohome=True)
                 for i in range(2)]
        hall.db.adventure_hall = True
        hall.db.adventure_instance_rooms = rooms
        for room in rooms:
            room.db.adventure_instance = True
        evennia.create_object("typeclasses.exits.Exit", key="instance", location=hall, destination=rooms[0])
        for player in players:
            player.move_to(hall, quiet=True)
            player.home = hall
        self.report["fixtures"] = {"characters": [player.pk for player in players], "accounts": [a.pk for a in accounts],
                                    "same_account_characters": [owner.pk, sibling.pk],
                                    "account_permissions": [list(a.permissions.all()) for a in accounts],
                                    "character_permissions": [list(p.permissions.all()) for p in players]}
        self.check("accounts and characters are ordinary Players", all(
            not account.is_superuser and not account.is_staff
            and {str(p).casefold() for p in account.permissions.all()} == {"player"}
            for account in accounts) and all({str(p).casefold() for p in player.permissions.all()} == {"player"}
                                           for player in players))
        tracked = ["pokemon/adventures/sessions.py", "pokemon/adventures/privacy.py", "pokemon/models/adventures.py"]
        self.report["source_sha256"] = {path: hashlib.sha256((REPO / path).read_bytes()).hexdigest() for path in tracked}
        environment = os.environ.copy()
        environment.update(PYTHONPATH=os.pathsep.join([str(self.root), str(REPO)]), PYTHONUNBUFFERED="1")
        package = Path(evennia.__file__).parent
        entry = "import site; site.addsitedir(" + repr(str(Path(sys.prefix) / "Lib/site-packages")) + "); from twisted.scripts.twistd import run; run()"
        for label, source in (("portal", "server/portal/portal.py"), ("server", "server/server.py")):
            stream = (self.root / (label + "-console.log")).open("wb")
            self.streams.append(stream)
            self.children.append(subprocess.Popen([sys._base_executable, "-c", entry, "--nodaemon", "--logfile",
                str(self.root / (label + "-twisted.log")), "--python", str(package / source)], cwd=self.root,
                env=environment, stdout=stream, stderr=subprocess.STDOUT,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)))
        deadline = time.monotonic() + 60
        while True:
            assert all(child.poll() is None for child in self.children), "Fixture process stopped during startup"
            try:
                with socket.create_connection(("127.0.0.1", self.telnet_port), timeout=1):
                    break
            except (ConnectionRefusedError, TimeoutError):
                assert time.monotonic() < deadline, "Fixture startup timed out"
                time.sleep(0.3)
        time.sleep(3)
        a = self.login(credentials[0], owner)
        b = self.login(credentials[1], outsider)

        def attr(player, key):
            return BattleRewards.stored_attribute(player, key)

        self.send(a, "+adventure/start alpha_meadow")
        session = AdventureSession.objects.get(leader=owner, holds_instance=True)
        self.send(a, "north")
        self.send(a, "+adventure/choose wild", seconds=1.5)
        original_battle = attr(owner, "battle_id")
        self.check("wild encounter launched through socket", bool(original_battle))
        state = AdventureSession.objects.values("current_node", "objective_progress", "metadata").get(pk=session.pk)
        encounters = list(EncounterPokemon.objects.values_list("pk", flat=True))
        for command in ("north", "+adventure/search", "+adventure/start alpha_meadow", "+adventure/choose trainer", "+adventure/leave"):
            self.send(a, command)
            self.check("wild interlock: " + command, state == AdventureSession.objects.values(
                "current_node", "objective_progress", "metadata").get(pk=session.pk))
        self.send(a, "+adventure/look")
        self.send(a, "+adventure/objectives")
        for command in ("instance", "+watch " + owner.key, "+status @" + owner.key):
            output = self.send(b, command)
            self.check("outsider denied: " + command, "private" in output.lower() or "battle not found" in output.lower())
        self.send(b, "+adventure/start alpha_meadow")
        other_run = AdventureSession.objects.get(leader=outsider, holds_instance=True)
        self.check("two players own different rooms", other_run.instance_room_id != session.instance_room_id)
        self.send(b, "+adventure/leave")
        a.close()
        time.sleep(0.5)
        a = self.login(credentials[0], sibling)
        for command in ("instance", "+watch " + owner.key, "+status @" + owner.key):
            output = self.send(a, command)
            self.check("same-account outsider denied: " + command, "private" in output.lower() or "battle not found" in output.lower())
        self.send(a, "+adventure/start alpha_meadow")
        sibling_run = AdventureSession.objects.get(leader=sibling, holds_instance=True)
        self.check("same-account characters own distinct runs", sibling_run.pk != session.pk
                   and sibling_run.instance_room_id != session.instance_room_id)
        self.send(a, "+adventure/leave")
        a.close()
        time.sleep(0.5)
        a = self.login(credentials[0], owner)
        self.check("reconnect retained original wild battle", attr(owner, "battle_id") == original_battle
                   and list(EncounterPokemon.objects.values_list("pk", flat=True)) == encounters)
        for _ in range(20):
            if not attr(owner, "battle_id"):
                break
            self.send(a, "+attack Water Gun", seconds=0.9)
        self.check("wild battle finished normally", not attr(owner, "battle_id"))
        self.send(a, "north")
        self.send(a, "+adventure/search")
        self.send(a, "south")
        self.send(a, "south")
        self.send(a, "+adventure/leave")
        self.send(a, "+adventure/claim")
        self.send(a, "+adventure/claim")
        self.send(a, "+adventure/start alpha_meadow")
        self.send(a, "north")
        self.send(a, "+adventure/choose trainer", seconds=1.5)
        self.check("NPC encounter launched through socket", bool(attr(owner, "battle_id")))
        trainer_run = AdventureSession.objects.get(leader=owner, holds_instance=True)
        for command in ("north", "+adventure/search", "+adventure/leave"):
            self.send(a, command)
            self.check("NPC battle retained: " + command, bool(attr(owner, "battle_id")))
        self.send(a, "+concede yes", seconds=1.5)
        self.check("NPC concession recorded original loss", AdventureSession.objects.get(pk=trainer_run.pk).metadata.get("encounter_result") == "loss")
        self.send(a, "north")
        self.send(a, "+adventure/leave")
        self.check("all fixture reservations released", not AdventureSession.objects.filter(holds_instance=True).exists())
        self.check("fixture runtime logs contain no tracebacks", all(
            "Traceback (most recent call last)" not in path.read_text(encoding="utf-8", errors="replace")
            for path in self.root.glob("*-twisted.log")))
        self.report["status"] = "passed"

    def close(self):
        """Stop only fixture children and remove only the generated SQL schema."""
        for client in self.clients:
            client.close()
        for child in reversed(self.children):
            if child.poll() is None:
                child.terminate()
            try:
                child.wait(timeout=15)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait(timeout=5)
        for stream in self.streams:
            stream.close()
        self.database.close()
        self.report["fixture_processes_stopped"] = all(child.poll() is not None for child in self.children)
        self.report["schema_cleanup_called"] = True
        self.save()


if __name__ == "__main__":
    acceptance = SocketAcceptance()
    try:
        acceptance.run()
    except BaseException:
        acceptance.report.update(status="failed", error=traceback.format_exc())
        raise
    finally:
        acceptance.close()
        print(json.dumps({"root": str(acceptance.root), "status": acceptance.report["status"],
                          "checks": len(acceptance.report["checks"]),
                          "fixture_processes_stopped": acceptance.report["fixture_processes_stopped"]}))
