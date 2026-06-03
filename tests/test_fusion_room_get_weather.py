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
                assert "---- Items" in rooms.strip_ansi(appearance)
                assert "Potion" in rooms.strip_ansi(appearance)
                assert "Ether" in rooms.strip_ansi(appearance)


def test_return_appearance_uses_classic_modern_layout_and_hotkeys():
        with load_rooms_module() as rooms:
                FusionRoom = rooms.FusionRoom
                room = FusionRoom()
                room.key = "Temporary Pokemon Center"
                room.id = 42
                room.default_description = "A default description."
                room.db = DummyDB(
                        desc="This room is a temporary pokemon center, no thrills, just a room to be a pokemon center.",
                        weather="clear",
                        is_item_store=False,
                        is_item_shop=False,
                        is_pokemon_center=True,
                )

                exits = [
                        types.SimpleNamespace(
                                key="(H)unting (G)round",
                                id=301,
                                db=DummyDB(priority=1, dark=False),
                                access=lambda *_args, **_kwargs: True,
                        ),
                        types.SimpleNamespace(
                                key="(O)ut",
                                id=302,
                                db=DummyDB(priority=2, dark=False),
                                access=lambda *_args, **_kwargs: True,
                        ),
                        types.SimpleNamespace(
                                key="(S)ecret",
                                id=303,
                                db=DummyDB(priority=3, dark=True),
                                access=lambda *_args, **_kwargs: True,
                        ),
                ]
                items = [
                        types.SimpleNamespace(
                                key="Ball-O-Matic",
                                id=401,
                                db=DummyDB(dark=False),
                                get_display_name=lambda looker=None, **kwargs: "|gBall-O-Matic|n",
                        )
                ]

                def fake_contents_get(content_type=None, **_kwargs):
                        if content_type == "exit":
                                return exits
                        if content_type == "character":
                                return []
                        if content_type == "object":
                                return items
                        return []

                room.contents_get = fake_contents_get
                room.filter_visible = lambda objects, *_args, **_kwargs: objects

                looker = types.SimpleNamespace()
                looker.key = "Yang"
                looker.id = 7
                looker.db = DummyDB(ui_mode="fancy", ui_theme="green")
                looker.ndb = DummyDB(cols=80)
                looker.has_account = True
                looker.attributes = DummyDB(npc=False)
                looker.check_permstring = lambda _perm: False

                appearance = room.return_appearance(looker)
                plain = rooms.strip_ansi(appearance)

                assert plain.startswith("Temporary Pokemon Center\n\nThis room is")
                assert "---- Exits " in plain
                assert "---- Items " in plain
                assert "---- Players " in plain
                assert "Ball-O-Matic" in plain
                assert "Yang" in plain
                assert "(H)unting (G)round" in plain
                assert "(O)ut" in plain
                assert "(S)ecret" not in plain
                assert "#42" not in plain
                assert "#301" not in plain
                assert ":Exits:" not in plain
                assert "|c(|wH|c)unting |c(|wG|c)round|n" in appearance
                assert "|c(|wO|c)ut|n" in appearance
                assert "There is a Pokemon center here. Use +pokestore to access your Pokemon storage." in plain
                assert all(len(line) <= 78 for line in plain.splitlines())


def test_return_appearance_hides_inactive_player_puppets_from_npcs():
        with load_rooms_module() as rooms:
                FusionRoom = rooms.FusionRoom
                room = FusionRoom()
                room.key = "Route House"
                room.id = 52
                room.default_description = "A default description."
                room.db = DummyDB(
                        desc="A small route house.",
                        weather="clear",
                        is_item_store=False,
                        is_item_shop=False,
                        is_pokemon_center=False,
                )

                active_player = types.SimpleNamespace(
                        key="Ash",
                        id=10,
                        has_account=True,
                        attributes=DummyDB(npc=False),
                        db=DummyDB(dark=False),
                )
                inactive_player = types.SimpleNamespace(
                        key="Misty",
                        id=11,
                        has_account=False,
                        attributes=DummyDB(npc=False),
                        db=DummyDB(dark=False),
                )
                store_owner = types.SimpleNamespace(
                        key="Shopkeeper",
                        id=12,
                        has_account=False,
                        attributes=DummyDB(npc=True),
                        db=DummyDB(dark=False),
                )

                def fake_contents_get(content_type=None, **_kwargs):
                        if content_type == "exit":
                                return []
                        if content_type == "character":
                                return [active_player, inactive_player, store_owner]
                        if content_type == "object":
                                return []
                        return []

                room.contents_get = fake_contents_get
                room.filter_visible = lambda objects, *_args, **_kwargs: objects

                looker = active_player
                looker.ndb = DummyDB(cols=80)
                looker.db.ui_mode = "fancy"
                looker.db.ui_theme = "green"
                looker.check_permstring = lambda _perm: False

                appearance = room.return_appearance(looker)
                plain = rooms.strip_ansi(appearance)

                assert "---- Players " in plain
                assert "Ash" in plain
                assert "---- NPCs " in plain
                assert "Shopkeeper" in plain
                assert "Misty" not in plain


def test_return_appearance_hides_npc_section_when_only_inactive_puppets_are_present():
        with load_rooms_module() as rooms:
                FusionRoom = rooms.FusionRoom
                room = FusionRoom()
                room.key = "Quiet Room"
                room.id = 53
                room.default_description = "A default description."
                room.db = DummyDB(
                        desc="A quiet room.",
                        weather="clear",
                        is_item_store=False,
                        is_item_shop=False,
                        is_pokemon_center=False,
                )

                inactive_player = types.SimpleNamespace(
                        key="Misty",
                        id=11,
                        has_account=False,
                        attributes=DummyDB(npc=False),
                        db=DummyDB(dark=False),
                )

                def fake_contents_get(content_type=None, **_kwargs):
                        if content_type == "exit":
                                return []
                        if content_type == "character":
                                return [inactive_player]
                        if content_type == "object":
                                return []
                        return []

                room.contents_get = fake_contents_get
                room.filter_visible = lambda objects, *_args, **_kwargs: objects

                looker = types.SimpleNamespace()
                looker.key = "Brock"
                looker.id = 12
                looker.db = DummyDB(ui_mode="fancy", ui_theme="green", dark=False)
                looker.ndb = DummyDB(cols=80)
                looker.has_account = True
                looker.attributes = DummyDB(npc=False)
                looker.check_permstring = lambda _perm: False

                appearance = room.return_appearance(looker)
                plain = rooms.strip_ansi(appearance)

                assert "Misty" not in plain
                assert "---- NPCs " not in plain
                assert "---- Players " in plain
                assert "Brock" in plain


def test_return_appearance_preserves_builder_metadata_in_classic_layout():
        with load_rooms_module() as rooms:
                FusionRoom = rooms.FusionRoom
                room = FusionRoom()
                room.key = "Temporary Pokemon Center"
                room.id = 42
                room.default_description = "A default description."
                room.db = DummyDB(
                        desc="A staff-visible test room.",
                        weather="clear",
                        is_item_store=False,
                        is_item_shop=True,
                        is_pokemon_center=False,
                )

                exits = [
                        types.SimpleNamespace(
                                key="(O)ut",
                                id=302,
                                db=DummyDB(priority=None, dark=False),
                                access=lambda *_args, **_kwargs: True,
                        ),
                        types.SimpleNamespace(
                                key="(S)ecret",
                                id=303,
                                db=DummyDB(priority=None, dark=True),
                                access=lambda *_args, **_kwargs: True,
                        ),
                ]
                items = [
                        types.SimpleNamespace(
                                key="Ball-O-Matic",
                                id=401,
                                db=DummyDB(dark=True),
                                get_display_name=lambda looker=None, **kwargs: "|gBall-O-Matic|n",
                        )
                ]

                def fake_contents_get(content_type=None, **_kwargs):
                        if content_type == "exit":
                                return exits
                        if content_type == "character":
                                return []
                        if content_type == "object":
                                return items
                        return []

                room.contents_get = fake_contents_get
                room.filter_visible = lambda objects, *_args, **_kwargs: objects

                looker = types.SimpleNamespace()
                looker.key = "Builder"
                looker.id = 7
                looker.db = DummyDB(ui_mode="fancy", ui_theme="green")
                looker.ndb = DummyDB(cols=80)
                looker.has_account = True
                looker.attributes = DummyDB(npc=False)
                looker.check_permstring = lambda _perm: True

                appearance = room.return_appearance(looker)
                plain = rooms.strip_ansi(appearance)

                assert "Temporary Pokemon Center (#42)" in plain
                assert "(O)ut (#302)" in plain
                assert "(S)ecret (#303) [Dark]" in plain
                assert "Ball-O-Matic (#401) (Dark)" in plain
                assert "There is a store here. Use +store/list to see its contents." in plain


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
