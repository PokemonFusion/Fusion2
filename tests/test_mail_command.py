import importlib.util
import os
import sys
import types


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)


class FakeDefaultCharacter:
    pass


def load_cmd_module(characters=None):
    originals = {name: sys.modules.get(name) for name in (
        "evennia",
        "evennia.objects",
        "evennia.objects.objects",
        "evennia.utils",
        "evennia.utils.evtable",
    )}

    def search_object(query, *args, **kwargs):
        lowered = (query or "").strip().lower()
        return [character for character in characters or [] if character.key.lower() == lowered]

    fake_evennia = types.ModuleType("evennia")
    fake_evennia.Command = type("Command", (), {})
    fake_evennia.search_object = search_object
    sys.modules["evennia"] = fake_evennia

    fake_objects = types.ModuleType("evennia.objects")
    fake_objects_objects = types.ModuleType("evennia.objects.objects")
    fake_objects_objects.DefaultCharacter = FakeDefaultCharacter
    sys.modules["evennia.objects"] = fake_objects
    sys.modules["evennia.objects.objects"] = fake_objects_objects

    class FakeEvTable:
        def __init__(self, *cols):
            self.cols = cols
            self.rows = []

        def add_row(self, *vals):
            self.rows.append(vals)

        def __str__(self):
            return repr((self.cols, self.rows))

    fake_evtable = types.ModuleType("evennia.utils.evtable")
    fake_evtable.EvTable = FakeEvTable
    fake_utils = types.ModuleType("evennia.utils")
    fake_utils.evtable = fake_evtable
    sys.modules["evennia.utils"] = fake_utils
    sys.modules["evennia.utils.evtable"] = fake_evtable

    path = os.path.join(ROOT, "commands", "player", "cmd_mail.py")
    spec = importlib.util.spec_from_file_location("commands.player.cmd_mail", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)

    def restore():
        sys.modules.pop("commands.player.cmd_mail", None)
        for name, original in originals.items():
            if original is not None:
                sys.modules[name] = original
            else:
                sys.modules.pop(name, None)

    return mod, restore


class FakeTags:
    def __init__(self, tags=()):
        self.tags = set(tags)

    def add(self, key, category=None):
        self.tags.add((key, category))

    def remove(self, key, category=None):
        self.tags.discard((key, category))

    def has(self, key, category=None):
        return (key, category) in self.tags


class FakeMessage:
    def __init__(self, ident, sender, recipient, subject, body):
        self.id = ident
        self.senders = [sender]
        self.receivers = [recipient]
        self.header = subject
        self.message = body
        self.date_created = ident
        self.tags = FakeTags((("character_mail", "pf2_mail"), ("unread", "pf2_mail")))
        self.hidden_for = set()


class FakeQuerySet(list):
    def filter(self, db_tags__db_key=None, db_tags__db_category=None):
        return FakeQuerySet(
            message
            for message in self
            if message.tags.has(db_tags__db_key, category=db_tags__db_category)
        )

    def distinct(self):
        return self

    def order_by(self, field):
        return FakeQuerySet(sorted(self, key=lambda message: message.date_created, reverse=True))


class FakeManager:
    def __init__(self):
        self.messages = []

    def get_messages_by_receiver(self, character):
        ident = character.id
        return FakeQuerySet(
            message
            for message in self.messages
            if any(receiver.id == ident for receiver in message.receivers) and ident not in message.hidden_for
        )


class FakeCharacter(FakeDefaultCharacter):
    def __init__(self, key, ident):
        self.key = key
        self.name = key
        self.id = ident
        self.messages = []

    def is_typeclass(self, cls, exact=False):
        return cls is FakeDefaultCharacter

    def msg(self, message):
        self.messages.append(message)


def install_fake_store(mod):
    manager = FakeManager()
    counter = {"id": 0}

    def create_message(sender, body, recipient, subject):
        counter["id"] += 1
        message = FakeMessage(counter["id"], sender, recipient, subject, body)
        manager.messages.append(message)
        return message

    mod.character_mail._msg_model = lambda: types.SimpleNamespace(objects=manager)
    mod.character_mail._create_message = create_message
    return manager


def call_mail(mod, caller, args="", switches=None, lhs="", rhs=""):
    cmd = mod.CmdMail()
    cmd.caller = caller
    cmd.args = args
    cmd.switches = switches or []
    cmd.lhs = lhs
    cmd.rhs = rhs
    cmd.func()
    return caller.messages[-1]


def test_mail_command_sends_and_lists_character_mail():
    sender = FakeCharacter("Ash", 1)
    recipient = FakeCharacter("Misty", 2)
    mod, restore = load_cmd_module([sender, recipient])
    install_fake_store(mod)

    try:
        sent = call_mail(mod, sender, switches=["send"], lhs="Misty", rhs="Hello/Meet at the lab.")
        listing = call_mail(mod, recipient)
    finally:
        restore()

    assert sent == "Mail #1 sent to Misty."
    assert "Mailbox for Misty" in listing
    assert "Hello" in listing
    assert "Unread" in listing


def test_mail_command_reads_replies_and_archives():
    sender = FakeCharacter("Ash", 1)
    recipient = FakeCharacter("Misty", 2)
    mod, restore = load_cmd_module([sender, recipient])
    install_fake_store(mod)

    try:
        call_mail(mod, sender, switches=["send"], lhs="Misty", rhs="Hello/Meet at the lab.")
        read = call_mail(mod, recipient, args="1", switches=["read"])
        reply = call_mail(mod, recipient, switches=["reply"], lhs="1", rhs="On my way.")
        archived = call_mail(mod, recipient, args="1", switches=["delete"])
        empty = call_mail(mod, recipient)
    finally:
        restore()

    assert "Meet at the lab." in read
    assert reply == "Reply sent as mail #2."
    assert archived == "Mail #1 archived."
    assert empty == "Your mailbox is empty."


def test_mail_command_can_mark_read_mail_unread():
    sender = FakeCharacter("Ash", 1)
    recipient = FakeCharacter("Misty", 2)
    mod, restore = load_cmd_module([sender, recipient])
    install_fake_store(mod)

    try:
        call_mail(mod, sender, switches=["send"], lhs="Misty", rhs="Hello/Meet at the lab.")
        call_mail(mod, recipient, args="1", switches=["read"])
        unread = call_mail(mod, recipient, args="1", switches=["unread"])
        listing = call_mail(mod, recipient)
    finally:
        restore()

    assert unread == "Mail #1 marked unread."
    assert "Unread" in listing
