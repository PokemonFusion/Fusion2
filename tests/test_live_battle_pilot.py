"""Safety boundaries and false-pass prevention for the logged-in pilot runner."""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[1] / "tools"


def load(name):
    """Load the standalone tool without initializing a game database."""
    spec = importlib.util.spec_from_file_location(name, TOOLS / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


cases = load("live_battle_pilot_cases")
server = load("live_battle_pilot_server")
runner = load("live_battle_pilot")


def test_protected_row_comparison_catches_updates_and_deletions():
    before = {"pokemon": {"human": "old", "missing": "digest"}}
    after = {"pokemon": {"human": "changed", "new_qa": "new"}}
    changes = runner.compare_fingerprints(before, after)
    assert changes == [{"table": "pokemon", "pk": "human", "change": "modified"},
                       {"table": "pokemon", "pk": "missing", "change": "missing"}]
    assert runner.compare_fingerprints(before, {"pokemon": before["pokemon"] | {"qa": "new"}}) == []


def test_manifest_refuses_outside_artifacts(tmp_path):
    with pytest.raises(ValueError, match="inside"):
        server.load_manifest(tmp_path / "manifest.json")


def test_manifest_rejects_preexisting_character_ids(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "REPO", tmp_path)
    folder = tmp_path / ".codex-artifacts" / "pilot"
    folder.mkdir(parents=True)
    path = folder / "manifest.json"
    path.write_text(json.dumps({"tag": "battle-pilot-test", "baseline_max_object_id": 100,
                                "players": {"a": {"id": 1}, "b": {"id": 102}, "staff": {"id": 103}}}))
    with pytest.raises(ValueError, match="newer"):
        server.load_manifest(path)


def test_catalog_is_twenty_distinct_scenarios_and_all_checks_are_explicit():
    assert len(cases.SCENARIOS) == 20
    assert len({case.key for case in cases.SCENARIOS}) == 20
    assert {case.mode for case in cases.SCENARIOS} == {"single", "double", "wild", "trainer"}
    assert all(case.expected for case in cases.SCENARIOS)
    assert all(command.startswith(("+attack ", "+switch ", "+item ", "+flee"))
               for case in cases.SCENARIOS for turn in case.turns for _, command in turn)


def test_damage_message_without_actual_damage_is_a_failure():
    state = {"battle": {"sides": {"B": {"active": [{"hp": 100}]}}}}
    with pytest.raises(AssertionError, match="did not reduce"):
        runner.evaluate(cases.SCENARIOS[0], [state, state], "Tackle succeeded!")


def test_fragmented_telnet_negotiation_preserves_player_text(tmp_path):
    class Wire:
        def __init__(self):
            self.sent = []

        def sendall(self, value):
            self.sent.append(value)

    client = runner.TelnetClient("a", {}, tmp_path, 4000, [])
    client.sock = Wire()
    assert client.parse(b"Hello\xff\xfb") == b"Hello"
    assert client.parse(b"\x01world\xff\xff") == b"world\xff"
    assert client.sock.sent == [b"\xff\xfe\x01"]


def test_transcript_redacts_all_pilot_credentials(tmp_path):
    client = runner.TelnetClient("a", {}, tmp_path, 4000, ["secret-a", "secret-b"])
    client.record("connect secret-a", "echo secret-b")
    text = (tmp_path / "transcript.jsonl").read_text()
    assert "secret-a" not in text and "secret-b" not in text
    assert text.count("[REDACTED]") == 2


@pytest.mark.parametrize("write_summary", [True, False])
def test_disable_finishes_before_optional_pilot_report(tmp_path, monkeypatch, write_summary):
    """The dex caller must be able to supply its own report schema after teardown."""
    credential_path = tmp_path / "private-credentials.json"
    credential_path.write_text(json.dumps({name: {"password": "fake-" + name} for name in ("a", "b", "staff")}))
    manifest = tmp_path / "manifest.json"
    monkeypatch.setattr(server, "load_manifest", lambda path: (manifest, {"credential_path": str(credential_path)}))
    events = []

    class Client:
        def __init__(self, label, *args):
            self.label = label

        def open(self):
            events.append(("open", self.label))

        def close(self):
            events.append(("close", self.label))

    class API:
        def __init__(self, *args):
            pass

        def call(self, action):
            assert action == "disable"
            return {"disabled_account_ids": [25, 26, 27], "staff_privileges_removed": True}

    monkeypatch.setattr(runner, "TelnetClient", Client)
    monkeypatch.setattr(runner, "StaffAPI", API)
    monkeypatch.setattr(runner, "write_report", lambda path: events.append(("report", path)))
    runner.disable(manifest, write_summary=write_summary)
    assert not credential_path.exists()
    assert json.loads((tmp_path / "accounts-disabled.json").read_text())["credential_file_removed"]
    assert {label for action, label in events if action == "close"} == {"a", "b", "staff"}
    assert sum(action == "report" for action, _ in events) == int(write_summary)


def test_staff_code_echo_is_not_accepted_as_success():
    class Client:
        def send(self, *args, **kwargs):
            return ">>> print('PF2PILOT_READY')\nNameError: helper failed\n"

    with pytest.raises(RuntimeError, match="could not load"):
        runner.StaffAPI(Client(), "manifest.json")


def test_late_response_from_a_previous_staff_request_is_rejected():
    class Client:
        def send(self, *args, **kwargs):
            return 'PF2PILOT_old:{"battle_id": 1}:ENDPF2PILOT_old\n'

    api = runner.StaffAPI.__new__(runner.StaffAPI)
    api.client, api.manifest = Client(), "manifest.json"
    with pytest.raises(RuntimeError, match="complete evidence"):
        api.call("snapshot")


def test_current_staff_response_is_selected_after_an_old_delayed_response():
    class Client:
        def send(self, command, label=None, marker=None):
            token = marker.removeprefix(":END")
            return ('PF2PILOT_old:{"battle_id": 1}:ENDPF2PILOT_old\n'
                    + token + ':{"battle": null}' + marker + '\n')

    api = runner.StaffAPI.__new__(runner.StaffAPI)
    api.client, api.manifest = Client(), "manifest.json"
    assert api.call("snapshot") == {"battle": None}


def test_overlapping_runner_is_refused_and_lock_is_released(tmp_path):
    with runner.run_lock(tmp_path):
        with pytest.raises(FileExistsError):
            with runner.run_lock(tmp_path):
                pytest.fail("A second runner acquired the same identities")
    assert not (tmp_path / "pilot-run.lock").exists()


def test_retained_pass_without_turn_evidence_fails_audit(tmp_path):
    case = cases.SCENARIOS[1]
    (tmp_path / "results.json").write_text(json.dumps([{"key": case.key, "status": "passed"}]))
    unchanged = {"players": {"a": {"ordinary": True}, "b": {"ordinary": True}},
                 "battle": {"turn": 1, "sides": {}}}
    (tmp_path / (case.key + ".json")).write_text(json.dumps({"snapshots": [unchanged, unchanged]}))
    audit = runner.audit_passed_evidence(tmp_path)
    assert audit["audited_passes"] == 0
    assert audit["errors"] == [{"key": case.key, "error": "Commands did not advance a full turn"}]


def test_expected_blocker_messages_require_review_instead_of_a_bug_claim():
    fly = next(case for case in cases.SCENARIOS if case.check == "fly")
    review = runner.review_failure(fly, [], "Target protected itself!")
    assert review["classification"] == "possible_expected_failure"
    assert review["confirmed_game_defect"] is False
    assert any("95 percent" in condition for condition in review["expected_failure_conditions"])


def test_generic_failure_message_does_not_confirm_a_mechanics_defect():
    fly = next(case for case in cases.SCENARIOS if case.check == "fly")
    review = runner.review_failure(fly, [], "Pidgey's Fly failed!")
    assert review["classification"] == "requires_diagnosis"
    assert review["confirmed_game_defect"] is False
