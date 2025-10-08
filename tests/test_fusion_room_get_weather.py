import contextlib
import importlib.util
import os
import sys
import types

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)


class DummyDB(types.SimpleNamespace):
        def get(self, key, default=None):
                return getattr(self, key, default)


@contextlib.contextmanager
def load_rooms_module():
        module_names = [
                "evennia",
                "evennia.objects",
                "evennia.objects.objects",
                "evennia.utils",
                "evennia.utils.ansi",
                "evennia.utils.logger",
                "typeclasses",
                "typeclasses.objects",
                "typeclasses.rooms",
                "pokemon.battle.battleinstance",
        ]
        previous = {name: sys.modules.get(name) for name in module_names}

        evennia = types.ModuleType("evennia")
        fake_objects = types.ModuleType("evennia.objects")
        fake_objects_objects = types.ModuleType("evennia.objects.objects")
        DefaultRoom = type("DefaultRoom", (), {})
        DefaultObject = type("DefaultObject", (), {})
        fake_objects_objects.DefaultRoom = DefaultRoom
        fake_objects_objects.DefaultObject = DefaultObject
        fake_objects.objects = fake_objects_objects
        evennia.objects = fake_objects
        evennia.DefaultRoom = DefaultRoom
        evennia.DefaultObject = DefaultObject

        fake_utils = types.ModuleType("evennia.utils")
        fake_utils.__path__ = []  # mark as package for submodule imports
        def _strip_ansi(value: str) -> str:
                if not isinstance(value, str):
                        return value
                out = []
                skip_next = False
                for char in value:
                        if skip_next:
                                skip_next = False
                                continue
                        if char == "|":
                                skip_next = True
                                continue
                        out.append(char)
                return "".join(out)

        fake_utils_ansi = types.ModuleType("evennia.utils.ansi")
        fake_utils_ansi.strip_ansi = _strip_ansi
        fake_utils_ansi.parse_ansi = lambda txt: txt
        fake_utils.ansi = fake_utils_ansi
        evennia.utils = fake_utils

        fake_logger = types.ModuleType("evennia.utils.logger")
        fake_logger.log_info = lambda *args, **kwargs: None
        fake_logger.log_err = lambda *args, **kwargs: None
        fake_utils.logger = fake_logger

        fake_tc_objects = types.ModuleType("typeclasses.objects")
        fake_tc_objects.ObjectParent = type("ObjectParent", (), {})

        sys.modules["evennia"] = evennia
        sys.modules["evennia.objects"] = fake_objects
        sys.modules["evennia.objects.objects"] = fake_objects_objects
        sys.modules["evennia.utils"] = fake_utils
        sys.modules["evennia.utils.ansi"] = fake_utils_ansi
        sys.modules["evennia.utils.logger"] = fake_logger
        sys.modules["typeclasses.objects"] = fake_tc_objects

        typeclasses_pkg = types.ModuleType("typeclasses")
        sys.modules["typeclasses"] = typeclasses_pkg

        fake_battleinstance = types.ModuleType("pokemon.battle.battleinstance")

        class _FakeBattleSession:
                @classmethod
                def restore(cls, *_args, **_kwargs):
                        return None

        fake_battleinstance.BattleSession = _FakeBattleSession
        sys.modules["pokemon.battle.battleinstance"] = fake_battleinstance

        try:
                spec = importlib.util.spec_from_file_location(
                        "typeclasses.rooms",
                        os.path.join(ROOT, "typeclasses", "rooms.py"),
                )
                rooms = importlib.util.module_from_spec(spec)
                typeclasses_pkg.rooms = rooms
                sys.modules["typeclasses.rooms"] = rooms
                assert spec.loader is not None
                spec.loader.exec_module(rooms)
                yield rooms
        finally:
                sys.modules.pop("typeclasses.rooms", None)
                if previous["typeclasses.rooms"] is not None:
                        sys.modules["typeclasses.rooms"] = previous["typeclasses.rooms"]
                if previous["typeclasses"] is not None:
                        sys.modules["typeclasses"] = previous["typeclasses"]
                else:
                        sys.modules.pop("typeclasses", None)

                for name in [
                        "typeclasses.objects",
                        "pokemon.battle.battleinstance",
                        "evennia.utils.logger",
                        "evennia.utils.ansi",
                        "evennia.utils",
                        "evennia.objects.objects",
                        "evennia.objects",
                        "evennia",
                ]:
                        module = previous[name]
                        if module is not None:
                                sys.modules[name] = module
                        else:
                                sys.modules.pop(name, None)


def test_get_weather_handles_get_attribute_shadow():
        with load_rooms_module() as rooms:
                FusionRoom = rooms.FusionRoom
                room = FusionRoom()
                room.db = DummyDB(weather="rain")
                assert room.get_weather() == "rain"
                # Store an attribute named 'get' which could shadow the handler's method
                room.db.get = None
                assert room.get_weather() == "rain"


def test_return_appearance_includes_items_section():
        with load_rooms_module() as rooms:
                FusionRoom = rooms.FusionRoom
                room = FusionRoom()
                room.key = "Test Room"
                room.id = 42
                room.default_description = "A default description."
                room.db = DummyDB(
                        desc="A test room.",
                        weather="clear",
                        is_item_store=False,
                        is_pokemon_center=False,
                )

                def fake_contents_get(content_type=None, **_kwargs):
                        if content_type == "exit":
                                return []
                        if content_type == "character":
                                return []
                        if content_type == "object":
                                potion = types.SimpleNamespace(
                                        key="Potion",
                                        id=101,
                                        db=DummyDB(dark=False),
                                        get_display_name=lambda looker=None, **kwargs: "|gPotion|n",
                                )
                                ether = types.SimpleNamespace(
                                        key="Ether",
                                        id=102,
                                        db=DummyDB(dark=True),
                                        get_display_name=lambda looker=None, **kwargs: "|cEther|n",
                                )
                                return [potion, ether]
                        return []

                room.contents_get = fake_contents_get
                room.filter_visible = lambda objects, *_args, **_kwargs: objects

                looker = types.SimpleNamespace()
                looker.key = "Ash"
                looker.id = 7
                looker.db = DummyDB(ui_mode="fancy", ui_theme="green")
                looker.ndb = DummyDB(cols=78)
                looker.has_account = True
                looker.attributes = DummyDB(npc=False)

                def check_permstring(_perm):
                        return False

                looker.check_permstring = check_permstring

                appearance = room.return_appearance(looker)
                assert ":Items:" in appearance
                assert "Potion" in rooms.strip_ansi(appearance)
                assert "Ether" in rooms.strip_ansi(appearance)


def test_return_appearance_items_in_sr_mode_are_plain_text():
        with load_rooms_module() as rooms:
                FusionRoom = rooms.FusionRoom
                room = FusionRoom()
                room.key = "Test Room"
                room.id = 24
                room.default_description = "A default description."
                room.db = DummyDB(
                        desc="A test room.",
                        weather="clear",
                        is_item_store=False,
                        is_pokemon_center=False,
                )

                def fake_contents_get(content_type=None, **_kwargs):
                        if content_type == "object":
                                return [
                                        types.SimpleNamespace(
                                                key="Potion",
                                                id=201,
                                                db=DummyDB(dark=False),
                                                get_display_name=lambda looker=None, **kwargs: "|gPotion|n",
                                        )
                                ]
                        return []

                room.contents_get = fake_contents_get
                room.filter_visible = lambda objects, *_args, **_kwargs: objects

                looker = types.SimpleNamespace()
                looker.key = "Brock"
                looker.id = 11
                looker.db = DummyDB(ui_mode="sr", ui_theme="green")
                looker.ndb = DummyDB(cols=78)
                looker.has_account = True
                looker.attributes = DummyDB(npc=False)
                looker.check_permstring = lambda _perm: True

                appearance = room.return_appearance(looker)
                assert "Items:" in appearance
                lines = appearance.splitlines()
                item_line = next((line for line in lines if line.strip().startswith("- Potion")), "")
                assert item_line.strip() == "- Potion #201"
                assert "|" not in item_line  # item line should be plain text
