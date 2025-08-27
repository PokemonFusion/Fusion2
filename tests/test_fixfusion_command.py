"""Tests for the `@fixfusion` admin command."""

import importlib.util
import os
import sys
import types


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)


def load_module(path, name):
    """Import a module from ``path`` under ``name``."""
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def setup_cmd():
    """Prepare the environment and return command module and fakes."""

    originals = {name: sys.modules.get(name) for name in [
        "evennia",
        "django",
        "django.core",
        "django.core.exceptions",
        "pokemon.models.fusion",
        "pokemon.models.core",
        "pokemon.models.storage",
        "utils.fusion",
    ]}

    # evennia.Command stub
    evennia_mod = types.ModuleType("evennia")
    evennia_mod.Command = type("Command", (), {})
    sys.modules["evennia"] = evennia_mod

    # django ValidationError stub
    django_mod = types.ModuleType("django")
    django_core = types.ModuleType("django.core")
    django_exc = types.ModuleType("django.core.exceptions")

    class ValidationError(Exception):
        """Replacement ValidationError for tests."""

    django_exc.ValidationError = ValidationError
    django_core.exceptions = django_exc
    django_mod.core = django_core
    sys.modules["django"] = django_mod
    sys.modules["django.core"] = django_core
    sys.modules["django.core.exceptions"] = django_exc

    # Fake PokemonFusion model and manager
    class FusionManager:
        def __init__(self):
            self.created = []

        def get_or_create(self, defaults=None, **kwargs):
            trainer = kwargs.get("trainer")
            pokemon = kwargs.get("pokemon")
            for obj in self.created:
                if obj.trainer is trainer and obj.pokemon is pokemon:
                    return obj, False
            obj = FakePokemonFusion(
                result=defaults.get("result"),
                trainer=trainer,
                pokemon=pokemon,
                permanent=defaults.get("permanent", False),
            )
            self.created.append(obj)
            return obj, True

        def filter(self, **kwargs):
            result = kwargs.get("result")
            items = [o for o in self.created if not result or o.result is result]

            class _QS(list):
                def first(self_inner):
                    return self_inner[0] if self_inner else None

            return _QS(items)

    class FakePokemonFusion:
        objects = FusionManager()

        def __init__(self, result, trainer, pokemon, permanent=False):
            self.result = result
            self.trainer = trainer
            self.pokemon = pokemon
            self.permanent = permanent

    fusion_models = types.ModuleType("pokemon.models.fusion")
    fusion_models.PokemonFusion = FakePokemonFusion
    sys.modules["pokemon.models.fusion"] = fusion_models

    # Stub for OwnedPokemon
    class FakeOwnedPokemon:
        objects = types.SimpleNamespace(
            filter=lambda **kwargs: types.SimpleNamespace(first=lambda: None)
        )

    core_models = types.ModuleType("pokemon.models.core")
    core_models.OwnedPokemon = FakeOwnedPokemon
    sys.modules["pokemon.models.core"] = core_models

    # Stub for ActivePokemonSlot
    class SlotManager:
        def __init__(self):
            self.slots = []

        def filter(self, **kwargs):
            storage = kwargs.get("storage")
            pokemon = kwargs.get("pokemon")
            result = [
                s
                for s in self.slots
                if (storage is None or s.storage is storage)
                and (pokemon is None or s.pokemon is pokemon)
            ]

            class _QS(list):
                def first(self_inner):
                    return self_inner[0] if self_inner else None

            return _QS(result)

    class FakeActivePokemonSlot:
        objects = SlotManager()

    storage_models = types.ModuleType("pokemon.models.storage")
    storage_models.ActivePokemonSlot = FakeActivePokemonSlot
    sys.modules["pokemon.models.storage"] = storage_models

    # utils.fusion
    spec = importlib.util.spec_from_file_location(
        "utils.fusion", os.path.join(ROOT, "utils", "fusion.py")
    )
    utils_fusion = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = utils_fusion
    spec.loader.exec_module(utils_fusion)

    cmd_mod = load_module(
        os.path.join(ROOT, "commands", "admin", "cmd_fixfusion.py"),
        "commands.admin.cmd_fixfusion",
    )

    def teardown():
        for name, mod in originals.items():
            if mod is not None:
                sys.modules[name] = mod
            else:
                sys.modules.pop(name, None)

    return cmd_mod, FakePokemonFusion, storage_models.ActivePokemonSlot, teardown, ValidationError


def test_fixfusion_records_fusion_when_already_in_party():
    """`@fixfusion` records a fusion when the mon is already in party."""

    cmd_mod, FakePokemonFusion, _Slot, teardown, _ValidationError = setup_cmd()
    try:
        mon = types.SimpleNamespace(
            species=types.SimpleNamespace(name="Pikachu"),
            name="Pikachu",
            in_party=True,
            party_slot=1,
        )
        storage = types.SimpleNamespace(get_party=lambda: [mon])
        trainer = object()
        target = types.SimpleNamespace(
            key="Ash",
            trainer=trainer,
            storage=storage,
            db=types.SimpleNamespace(fusion_species="Pikachu"),
        )
        caller = types.SimpleNamespace(msgs=[])

        caller.search = lambda name, global_search=True: target if name == "Ash" else None
        caller.msg = lambda text: caller.msgs.append(text)

        cmd = cmd_mod.CmdFixFusion()
        cmd.caller = caller
        cmd.args = "Ash"
        cmd.func()

        assert FakePokemonFusion.objects.created
        fusion = FakePokemonFusion.objects.created[0]
        assert fusion.trainer is trainer and fusion.result is mon
        assert any("Recorded fusion" in m for m in caller.msgs)
        assert any("already in party" in m for m in caller.msgs)
    finally:
        teardown()


def test_fixfusion_adds_mon_to_party_when_missing():
    """If fused Pokémon isn't active, `@fixfusion` adds it to the party."""

    cmd_mod, FakePokemonFusion, ActiveSlot, teardown, ValidationError = setup_cmd()
    try:
        mon = types.SimpleNamespace(
            species=types.SimpleNamespace(name="Pikachu"),
            name="Pikachu",
            in_party=False,
        )

        class Boxes:
            def filter(self, **kwargs):
                class _QS:
                    def first(self_inner):
                        return mon

                return _QS()

        class Storage:
            def __init__(self):
                self.party = []
                self.stored_pokemon = Boxes()

            def get_party(self):
                return self.party

            def add_active_pokemon(self, pokemon):
                if len(self.party) >= 6:
                    raise ValidationError("Party already has six Pokémon.")
                self.party.append(pokemon)
                pokemon.in_party = True
                pokemon.party_slot = len(self.party)
                ActiveSlot.objects.slots.append(
                    types.SimpleNamespace(storage=self, pokemon=pokemon, slot=len(self.party))
                )

        storage = Storage()
        trainer = object()
        target = types.SimpleNamespace(
            key="Ash",
            trainer=trainer,
            storage=storage,
            db=types.SimpleNamespace(fusion_species="Pikachu"),
        )
        caller = types.SimpleNamespace(msgs=[])
        caller.search = lambda name, global_search=True: target if name == "Ash" else None
        caller.msg = lambda text: caller.msgs.append(text)

        cmd = cmd_mod.CmdFixFusion()
        cmd.caller = caller
        cmd.args = "Ash"
        cmd.func()

        assert mon in storage.get_party()
        assert mon.in_party and mon.party_slot == 1
        assert ActiveSlot.objects.slots and ActiveSlot.objects.slots[0].slot == 1
        assert FakePokemonFusion.objects.created and FakePokemonFusion.objects.created[0].pokemon is mon
        assert any("Added" in m for m in caller.msgs)
        assert any("Recorded fusion" in m for m in caller.msgs)
    finally:
        teardown()


def test_fixfusion_errors_when_party_full():
    """The command errors if the party has no free slots."""

    cmd_mod, FakePokemonFusion, ActiveSlot, teardown, ValidationError = setup_cmd()
    try:
        mon = types.SimpleNamespace(
            species=types.SimpleNamespace(name="Pikachu"),
            name="Pikachu",
            in_party=False,
        )

        class Boxes:
            def filter(self, **kwargs):
                class _QS:
                    def first(self_inner):
                        return mon

                return _QS()

        class Storage:
            def __init__(self):
                self.party = [object() for _ in range(6)]
                self.stored_pokemon = Boxes()

            def get_party(self):
                return self.party

            def add_active_pokemon(self, pokemon):
                raise ValidationError("Party already has six Pokémon.")

        storage = Storage()
        trainer = object()
        target = types.SimpleNamespace(
            key="Ash",
            trainer=trainer,
            storage=storage,
            db=types.SimpleNamespace(fusion_species="Pikachu"),
        )
        caller = types.SimpleNamespace(msgs=[])
        caller.search = lambda name, global_search=True: target if name == "Ash" else None
        caller.msg = lambda text: caller.msgs.append(text)

        cmd = cmd_mod.CmdFixFusion()
        cmd.caller = caller
        cmd.args = "Ash"
        cmd.func()

        assert not FakePokemonFusion.objects.created
        assert any("Couldn't add to party" in m for m in caller.msgs)
    finally:
        teardown()

