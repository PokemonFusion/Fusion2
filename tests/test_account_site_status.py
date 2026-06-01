import importlib.util
import os
import sys
import types

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)


class FakeDefaultAccount:
    @classmethod
    def authenticate(cls, username, password, ip="", **kwargs):
        return object(), []

    def at_pre_login(self, **kwargs):
        return None


class FakeDefaultGuest:
    pass


class FakeHandler:
    def __init__(self, values):
        self.values = list(values)

    def all(self):
        return list(self.values)


def load_accounts_module():
    path = os.path.join(ROOT, "typeclasses", "accounts.py")
    spec = importlib.util.spec_from_file_location("typeclasses.accounts", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def install_fakes():
    original = {name: sys.modules.get(name) for name in (
        "django",
        "django.conf",
        "django.utils",
        "django.utils.translation",
        "evennia",
        "evennia.accounts",
        "evennia.accounts.accounts",
        "evennia.utils",
        "evennia.utils.utils",
    )}

    django = types.ModuleType("django")
    django_conf = types.ModuleType("django.conf")
    django_conf.settings = types.SimpleNamespace(MAX_NR_CHARACTERS=10)
    django_utils = types.ModuleType("django.utils")
    django_translation = types.ModuleType("django.utils.translation")
    django_translation.gettext = lambda text: text

    evennia = types.ModuleType("evennia")
    evennia_accounts = types.ModuleType("evennia.accounts")
    evennia_accounts_accounts = types.ModuleType("evennia.accounts.accounts")
    evennia_accounts_accounts.DefaultAccount = FakeDefaultAccount
    evennia_accounts_accounts.DefaultGuest = FakeDefaultGuest
    evennia_utils = types.ModuleType("evennia.utils")
    evennia_utils_utils = types.ModuleType("evennia.utils.utils")
    evennia_utils_utils.is_iter = lambda value: isinstance(value, (list, tuple))

    sys.modules.update(
        {
            "django": django,
            "django.conf": django_conf,
            "django.utils": django_utils,
            "django.utils.translation": django_translation,
            "evennia": evennia,
            "evennia.accounts": evennia_accounts,
            "evennia.accounts.accounts": evennia_accounts_accounts,
            "evennia.utils": evennia_utils,
            "evennia.utils.utils": evennia_utils_utils,
        }
    )
    return original


def restore_modules(original):
    for name, module in original.items():
        if module is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = module
    sys.modules.pop("typeclasses.accounts", None)


def test_account_authenticate_blocks_maintenance_login():
    original = install_fakes()
    try:
        mod = load_accounts_module()
        fake_account = object()
        FakeDefaultAccount.authenticate = classmethod(
            lambda cls, username, password, ip="", **kwargs: (fake_account, [])
        )
        mod.is_login_blocked = lambda account: True
        mod.get_login_block_message = lambda: "Maintenance window."

        account, errors = mod.Account.authenticate("player", "password")
    finally:
        restore_modules(original)

    assert account is None
    assert errors == ["|rMaintenance window.|n"]


def test_account_authenticate_allows_unblocked_login():
    original = install_fakes()
    try:
        mod = load_accounts_module()
        fake_account = object()
        FakeDefaultAccount.authenticate = classmethod(
            lambda cls, username, password, ip="", **kwargs: (fake_account, [])
        )
        mod.is_login_blocked = lambda account: False

        account, errors = mod.Account.authenticate("wizard", "password")
    finally:
        restore_modules(original)

    assert account is fake_account
    assert errors == []


def test_account_look_shows_unread_mail_by_character():
    original = install_fakes()
    try:
        mod = load_accounts_module()

        session = types.SimpleNamespace(sessid=1, protocol_key="web", address="127.0.0.1")
        char_with_mail = types.SimpleNamespace(
            id=10,
            name="Ash",
            permissions=FakeHandler([]),
            sessions=FakeHandler([]),
        )
        char_without_mail = types.SimpleNamespace(
            id=11,
            name="Misty",
            permissions=FakeHandler([]),
            sessions=FakeHandler([]),
        )
        account = mod.Account()
        account.name = "Tester"
        account.is_superuser = False
        account.sessions = FakeHandler([session])
        account.ndb = types.SimpleNamespace()
        mod.unread_mail_counts_for_characters = lambda chars: {10: 2}
        mod.character_identity = lambda char: char.id

        output = account.at_look(target=[char_with_mail, char_without_mail], session=session)
    finally:
        restore_modules(original)

    assert "Ash [] |y[2 unread mail]|n" in output
    assert "Misty []" in output
    assert "|yUnread mail:|n Ash (2). Use |wgoic|n, then |w+mail|n." in output
