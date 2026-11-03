import pytest

from utils import site_status


class FakeConfigManager:
    def __init__(self):
        self.data = {}

    def conf(self, key=None, value=None, delete=False, default=None):
        if delete:
            self.data.pop(key, None)
            return None
        if value is not None:
            self.data[key] = value
            return None
        return self.data.get(key, default() if callable(default) else default)


class FakeServerConfig:
    objects = FakeConfigManager()


class FakePermissions:
    def __init__(self, is_wizard=False):
        self.is_wizard = is_wizard

    def check(self, *permissions, require_all=False):
        return self.is_wizard and "Wizards" in permissions


class FakeAccount:
    def __init__(self, is_wizard=False):
        self.permissions = FakePermissions(is_wizard=is_wizard)


@pytest.fixture(autouse=True)
def fake_server_config(monkeypatch):
    FakeServerConfig.objects = FakeConfigManager()
    monkeypatch.setattr(site_status, "_server_config", lambda: FakeServerConfig)


def test_missing_config_defaults_to_open():
    current = site_status.get_site_status()

    assert current.status == site_status.STATUS_OPEN
    assert current.label == "Open"
    assert current.message == "The world is ready."
    assert current.logins_enabled is True


def test_valid_statuses_save_and_load():
    current = site_status.set_site_status(site_status.STATUS_LIMITED, "Webclient updates in progress.")

    assert current.status == site_status.STATUS_LIMITED
    assert current.message == "Webclient updates in progress."
    assert site_status.get_site_status().status == site_status.STATUS_LIMITED


def test_invalid_status_is_rejected():
    with pytest.raises(ValueError):
        site_status.set_site_status("offline")

    assert site_status.get_site_status().status == site_status.STATUS_OPEN


def test_clear_status_resets_message_and_state():
    site_status.set_site_status(site_status.STATUS_MAINTENANCE, "Testing a patch.")

    current = site_status.clear_site_status()

    assert current.status == site_status.STATUS_OPEN
    assert current.message == "The world is ready."


def test_maintenance_blocks_non_wizards_only():
    site_status.set_site_status(site_status.STATUS_MAINTENANCE)

    assert site_status.is_login_blocked(FakeAccount(is_wizard=False)) is True
    assert site_status.is_login_blocked(FakeAccount(is_wizard=True)) is False


def test_limited_does_not_block_login():
    site_status.set_site_status(site_status.STATUS_LIMITED)

    assert site_status.is_login_blocked(FakeAccount(is_wizard=False)) is False
