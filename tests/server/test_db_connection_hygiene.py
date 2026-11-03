from utils import db_connection_hygiene


def test_command_hygiene_closes_connections_around_command_hooks(monkeypatch):
    calls = []

    class Command:
        def at_pre_cmd(self):
            calls.append("pre")
            return "pre-result"

        def at_post_cmd(self):
            calls.append("post")
            return "post-result"

    monkeypatch.setattr(
        db_connection_hygiene,
        "close_stale_connections",
        lambda: calls.append("close"),
    )

    db_connection_hygiene._patch_command_class(Command)

    command = Command()
    assert command.at_pre_cmd() == "pre-result"
    assert command.at_post_cmd() == "post-result"
    assert calls == ["close", "pre", "post", "close"]


def test_command_hygiene_install_is_idempotent(monkeypatch):
    calls = []

    class Command:
        def at_pre_cmd(self):
            calls.append("pre")

        def at_post_cmd(self):
            calls.append("post")

    monkeypatch.setattr(
        db_connection_hygiene,
        "close_stale_connections",
        lambda: calls.append("close"),
    )

    db_connection_hygiene._patch_command_class(Command)
    db_connection_hygiene._patch_command_class(Command)

    command = Command()
    command.at_pre_cmd()
    command.at_post_cmd()
    assert calls == ["close", "pre", "post", "close"]
