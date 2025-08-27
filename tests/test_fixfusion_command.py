import importlib.util
import os
import sys
import types

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_fixfusion_records_fusion():
    """The @fixfusion command records a missing fusion entry."""
    orig_evennia = sys.modules.get("evennia")
    orig_models_fusion = sys.modules.get("pokemon.models.fusion")
    orig_utils_fusion = sys.modules.get("utils.fusion")
    try:
        evennia_mod = types.ModuleType("evennia")
        evennia_mod.Command = type("Command", (), {})
        sys.modules["evennia"] = evennia_mod

        class FakeManager:
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
            objects = FakeManager()

            def __init__(self, result, trainer, pokemon, permanent=False):
                self.result = result
                self.trainer = trainer
                self.pokemon = pokemon
                self.permanent = permanent

        fusion_models = types.ModuleType("pokemon.models.fusion")
        fusion_models.PokemonFusion = FakePokemonFusion
        sys.modules["pokemon.models.fusion"] = fusion_models

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

        mon = types.SimpleNamespace(species="Pikachu", in_party=True)
        storage = types.SimpleNamespace(get_party=lambda: [mon])
        trainer = object()
        target = types.SimpleNamespace(
            key="Ash",
            trainer=trainer,
            storage=storage,
            db=types.SimpleNamespace(fusion_species="Pikachu"),
        )
        caller = types.SimpleNamespace(msgs=[])

        def search(name, global_search=True):
            return target if name == "Ash" else None

        caller.search = search
        caller.msg = lambda text: caller.msgs.append(text)

        cmd = cmd_mod.CmdFixFusion()
        cmd.caller = caller
        cmd.args = "Ash"
        cmd.func()

        assert FakePokemonFusion.objects.created
        fusion = FakePokemonFusion.objects.created[0]
        assert fusion.trainer is trainer and fusion.result is mon
        assert caller.msgs and "Recorded fusion" in caller.msgs[-1]
    finally:
        if orig_evennia is not None:
            sys.modules["evennia"] = orig_evennia
        else:
            sys.modules.pop("evennia", None)
        if orig_models_fusion is not None:
            sys.modules["pokemon.models.fusion"] = orig_models_fusion
        else:
            sys.modules.pop("pokemon.models.fusion", None)
        if orig_utils_fusion is not None:
            sys.modules["utils.fusion"] = orig_utils_fusion
        else:
            sys.modules.pop("utils.fusion", None)
