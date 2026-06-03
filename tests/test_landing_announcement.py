import pytest

from utils import landing_announcement


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


class FakeAccount:
    def __init__(self, key="Wizard"):
        self.key = key


class FakeWrappedList:
    def __init__(self, values):
        self.values = list(values)

    def __iter__(self):
        return iter(self.values)


@pytest.fixture(autouse=True)
def fake_server_config(monkeypatch):
    FakeServerConfig.objects = FakeConfigManager()
    monkeypatch.setattr(landing_announcement, "_server_config", lambda: FakeServerConfig)


def test_missing_config_uses_default_landing_announcement():
    note = landing_announcement.get_landing_announcement()

    assert note.visible is True
    assert note.is_default is True
    assert note.label == "RECENT WORLD NEWS"
    assert note.title == "Development Server Notes"
    assert "Fusion 2 is actively evolving" in note.body
    assert len(note.bullets) == 3


def test_update_landing_announcement_persists_metadata_and_cleans_text():
    note = landing_announcement.update_landing_announcement(
        label="  Latest   News  ",
        title="  Alpha   Notes  ",
        body="  First line.  \n\n  Second   line.  ",
        bullets=[" One  item ", "", " Two\titem "],
        changed_by=FakeAccount("Admin"),
    )

    assert note.is_default is False
    assert note.label == "Latest News"
    assert note.title == "Alpha Notes"
    assert note.body_paragraphs == ("First line.", "Second line.")
    assert note.bullets == ("One item", "Two item")
    assert note.updated_at
    assert note.updated_by == "Admin"


def test_landing_announcement_can_hide_and_reset():
    hidden = landing_announcement.update_landing_announcement(visible=False, changed_by=FakeAccount("Admin"))

    assert hidden.visible is False
    assert landing_announcement.get_landing_announcement().visible is False

    reset = landing_announcement.reset_landing_announcement()

    assert reset.visible is True
    assert reset.is_default is True
    assert reset.title == "Development Server Notes"


def test_landing_announcement_bullet_helpers():
    added = landing_announcement.add_landing_bullet("  Watch for updates.  ", changed_by=FakeAccount("Admin"))

    assert added.bullets[-1] == "Watch for updates."

    cleared = landing_announcement.clear_landing_bullets(changed_by=FakeAccount("Admin"))

    assert cleared.bullets == ()


def test_landing_announcement_accepts_persistence_wrapped_bullets():
    FakeServerConfig.objects.conf(
        landing_announcement.ANNOUNCEMENT_CONFIG_KEY,
        {
            "title": "Wrapped List",
            "bullets": FakeWrappedList([" First ", "Second"]),
        },
    )

    note = landing_announcement.get_landing_announcement()

    assert note.bullets == ("First", "Second")


def test_empty_bullet_is_rejected():
    with pytest.raises(ValueError, match="Bullet text"):
        landing_announcement.add_landing_bullet("   ")
