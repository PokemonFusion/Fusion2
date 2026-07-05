import importlib.util
import os
import sys
import types


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)


def load_cmd_module(characters=None):
    originals = {name: sys.modules.get(name) for name in ("evennia",)}

    def search_object(query, *args, **kwargs):
        lowered = (query or "").strip().lower()
        exact = kwargs.get("exact", False)
        matches = []
        for character in characters or []:
            name = character.key.lower()
            if (exact and name == lowered) or (not exact and lowered in name):
                matches.append(character)
        return matches

    fake_evennia = types.ModuleType("evennia")
    fake_evennia.Command = type("Command", (), {})
    fake_evennia.search_object = search_object
    sys.modules["evennia"] = fake_evennia

    path = os.path.join(ROOT, "commands", "player", "cmd_page.py")
    spec = importlib.util.spec_from_file_location("commands.player.cmd_page_under_test", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)

    created_pages = []
    mod._create_page_message = (
        lambda sender, targets, message: created_pages.append((sender, list(targets), message))
    )
    mod._page_history = lambda character: []

    def restore():
        sys.modules.pop(spec.name, None)
        for name, original in originals.items():
            if original is not None:
                sys.modules[name] = original
            else:
                sys.modules.pop(name, None)

    return mod, created_pages, restore


class FakePermissions:
    def __init__(self, *perms):
        self._perms = perms

    def all(self):
        return list(self._perms)


class FakeSessions:
    def __init__(self, count=1):
        self._count = count

    def count(self):
        return self._count


class FakeCharacter:
    def __init__(self, key, ident, *, perms=(), online=True):
        self.key = key
        self.name = key
        self.id = ident
        self.db = types.SimpleNamespace()
        self.messages = []
        self.permissions = FakePermissions(*perms)
        self.sessions = FakeSessions(1 if online else 0)
        self.allow_msg = True

    def is_typeclass(self, typeclass, exact=False):
        return typeclass == "typeclasses.characters.Character"

    def access(self, caller, access_type, default=True):
        return self.allow_msg

    def msg(self, message):
        self.messages.append(message)


def call_page(mod, caller, args="", *, switches=None, lhs=None, rhs=None):
    if lhs is None and rhs is None and "=" in args:
        lhs, rhs = args.split("=", 1)
    cmd = mod.CmdPage()
    cmd.caller = caller
    cmd.args = args
    cmd.switches = switches or []
    cmd.lhs = lhs or ""
    cmd.rhs = rhs or ""
    cmd.func()
    return caller.messages[-1] if caller.messages else ""


def test_page_sends_pf1_equal_syntax_to_multiple_targets():
    ash = FakeCharacter("Ash", 1)
    misty = FakeCharacter("Misty", 2)
    brock = FakeCharacter("Brock", 3)
    mod, created_pages, restore = load_cmd_module([ash, misty, brock])

    try:
        result = call_page(mod, ash, "Misty Brock=Meet at the lab.")
    finally:
        restore()

    assert result == 'You page Misty and Brock with: "Meet at the lab.".'
    assert misty.messages == ['Ash pages, "Meet at the lab." (sent to Misty and Brock).']
    assert brock.messages == ['Ash pages, "Meet at the lab." (sent to Misty and Brock).']
    assert ash.db.page_last_paged == ["Misty", "Brock"]
    assert misty.db.page_last_sender == "Ash"
    assert misty.db.page_reply_group == ["Misty", "Brock"]
    assert created_pages == [(ash, [misty, brock], "Meet at the lab.")]


def test_page_sends_to_quoted_long_names():
    ash = FakeCharacter("Ash Ketchum", 1)
    misty = FakeCharacter("Misty Waterflower", 2)
    brock = FakeCharacter("Brock Slate", 3)
    mod, created_pages, restore = load_cmd_module([ash, misty, brock])

    try:
        result = call_page(mod, ash, '"Misty Waterflower" "Brock Slate"=Meet at the lab.')
    finally:
        restore()

    assert result == 'You page Misty Waterflower and Brock Slate with: "Meet at the lab.".'
    assert misty.messages == [
        'Ash Ketchum pages, "Meet at the lab." (sent to Misty Waterflower and Brock Slate).'
    ]
    assert brock.messages == [
        'Ash Ketchum pages, "Meet at the lab." (sent to Misty Waterflower and Brock Slate).'
    ]
    assert created_pages == [(ash, [misty, brock], "Meet at the lab.")]


def test_page_sends_to_quoted_long_name_space_syntax():
    ash = FakeCharacter("Ash Ketchum", 1)
    misty = FakeCharacter("Misty Waterflower", 2)
    mod, created_pages, restore = load_cmd_module([ash, misty])

    try:
        result = call_page(mod, ash, '"Misty Waterflower" Meet at the lab.')
    finally:
        restore()

    assert result == 'You page Misty Waterflower with: "Meet at the lab.".'
    assert misty.messages == ['Ash Ketchum pages, "Meet at the lab." (sent to Misty Waterflower).']
    assert created_pages == [(ash, [misty], "Meet at the lab.")]


def test_page_reply_sender_reply_all_and_last_target_shortcuts():
    ash = FakeCharacter("Ash", 1)
    misty = FakeCharacter("Misty", 2)
    brock = FakeCharacter("Brock", 3)
    mod, created_pages, restore = load_cmd_module([ash, misty, brock])

    try:
        call_page(mod, ash, "Misty Brock=Meet at the lab.")
        call_page(mod, misty, "#r=On my way.")
        call_page(mod, misty, "#R=Looping Brock in.")
        call_page(mod, ash, "Thanks.")
    finally:
        restore()

    assert any('Misty pages, "On my way."' in message for message in ash.messages)
    assert any('Misty pages, "Looping Brock in."' in message for message in ash.messages)
    assert any('Misty pages, "Looping Brock in."' in message for message in brock.messages)
    assert any('Ash pages, "Thanks."' in message for message in misty.messages)
    assert any('Ash pages, "Thanks."' in message for message in brock.messages)
    assert [entry[2] for entry in created_pages] == [
        "Meet at the lab.",
        "On my way.",
        "Looping Brock in.",
        "Thanks.",
    ]


def test_page_haven_and_ignore_block_nonstaff_pages():
    ash = FakeCharacter("Ash", 1)
    misty = FakeCharacter("Misty", 2)
    mod, created_pages, restore = load_cmd_module([ash, misty])

    try:
        assert call_page(mod, misty, "#haven") == "You are now stopping all pages."
        assert call_page(mod, ash, "Misty=Hello.") == "Misty is not receiving pages."
        assert call_page(mod, misty, "#!haven") == "You are now receiving pages."
        assert call_page(mod, misty, "#ignore Ash") == "Ash is now on your page ignore list."
        assert call_page(mod, ash, "Misty=Hello again.") == "Misty is ignoring your pages."
    finally:
        restore()

    assert misty.messages == [
        "You are now stopping all pages.",
        "You are now receiving pages.",
        "Ash is now on your page ignore list.",
    ]
    assert created_pages == []


def test_page_lock_blocks_nonstaff_but_staff_can_bypass():
    ash = FakeCharacter("Ash", 1)
    misty = FakeCharacter("Misty", 2)
    admin = FakeCharacter("Admin", 3, perms=("Admin",))
    mod, created_pages, restore = load_cmd_module([ash, misty, admin])

    try:
        assert call_page(mod, admin, "#lock Ash") == "Ash is now locked from page."
        assert call_page(mod, ash, "Misty=Can you hear me?") == (
            "Misty cannot receive your page while you are locked from page."
        )
        assert call_page(mod, admin, "Ash=Staff check.") == 'You page Ash with: "Staff check.".'
    finally:
        restore()

    assert ash.messages[-1] == 'Admin pages, "Staff check." (sent to Ash).'
    assert created_pages == [(admin, [ash], "Staff check.")]


def test_page_mail_routes_to_pf2_character_mail():
    ash = FakeCharacter("Ash", 1)
    misty = FakeCharacter("Misty", 2)
    mod, created_pages, restore = load_cmd_module([ash, misty])
    sent_mail = []

    class FakeMail:
        id = 7

    def send_character_mail(sender, recipient, subject, body):
        sent_mail.append((sender, recipient, subject, body))
        return FakeMail()

    original_send = mod.character_mail.send_character_mail
    original_mail_id = mod.character_mail.mail_id
    mod.character_mail.send_character_mail = send_character_mail
    mod.character_mail.mail_id = lambda message: message.id

    try:
        result = call_page(mod, ash, "#mail Misty=Running late.")
    finally:
        mod.character_mail.send_character_mail = original_send
        mod.character_mail.mail_id = original_mail_id
        restore()

    assert result == "Page-mail #7 sent to Misty."
    assert sent_mail == [(ash, misty, "Page-Mail from Ash", 'Ash says, "Running late."')]
    assert created_pages == []
