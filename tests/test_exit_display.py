import importlib.util
import os
import sys
import types

from utils.exit_display import format_exit_name

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def load_exits_module():
	module_names = [
		"evennia",
		"evennia.objects",
		"evennia.objects.objects",
		"typeclasses",
		"typeclasses.objects",
		"typeclasses.exits",
	]
	previous = {name: sys.modules.get(name) for name in module_names}

	fake_evennia = types.ModuleType("evennia")
	fake_objects = types.ModuleType("evennia.objects")
	fake_objects_objects = types.ModuleType("evennia.objects.objects")

	class FakeDefaultExit:
		default_description = "This is an exit."

		def get_display_desc(self, looker, **kwargs):
			return getattr(getattr(self, "db", None), "desc", None) or self.default_description

		def get_display_header(self, looker, **kwargs):
			return ""

		def get_display_footer(self, looker, **kwargs):
			return ""

		def get_display_exits(self, looker, **kwargs):
			return ""

		def get_display_characters(self, looker, **kwargs):
			return ""

		def get_display_things(self, looker, **kwargs):
			return ""

		def format_appearance(self, appearance, looker, **kwargs):
			return "\n".join(line for line in appearance.splitlines() if line.strip()).strip()

		def return_appearance(self, looker, **kwargs):
			if not looker:
				return ""
			return self.format_appearance(
				self.appearance_template.format(
					name=self.get_display_name(looker, **kwargs),
					extra_name_info=self.get_extra_display_name_info(looker, **kwargs),
					desc=self.get_display_desc(looker, **kwargs),
					header=self.get_display_header(looker, **kwargs),
					footer=self.get_display_footer(looker, **kwargs),
					exits=self.get_display_exits(looker, **kwargs),
					characters=self.get_display_characters(looker, **kwargs),
					things=self.get_display_things(looker, **kwargs),
				),
				looker,
				**kwargs,
			)

	fake_objects_objects.DefaultExit = FakeDefaultExit
	fake_objects.objects = fake_objects_objects
	fake_evennia.objects = fake_objects
	sys.modules["evennia"] = fake_evennia
	sys.modules["evennia.objects"] = fake_objects
	sys.modules["evennia.objects.objects"] = fake_objects_objects

	typeclasses_pkg = types.ModuleType("typeclasses")
	typeclasses_pkg.__path__ = [os.path.join(ROOT, "typeclasses")]
	sys.modules["typeclasses"] = typeclasses_pkg

	fake_typeclass_objects = types.ModuleType("typeclasses.objects")
	fake_typeclass_objects.ObjectParent = type("ObjectParent", (), {})
	sys.modules["typeclasses.objects"] = fake_typeclass_objects

	path = os.path.join(ROOT, "typeclasses", "exits.py")
	spec = importlib.util.spec_from_file_location("typeclasses.exits", path)
	mod = importlib.util.module_from_spec(spec)
	sys.modules[spec.name] = mod
	assert spec.loader is not None
	spec.loader.exec_module(mod)

	def restore():
		for name in reversed(module_names):
			module = previous[name]
			if module is not None:
				sys.modules[name] = module
			else:
				sys.modules.pop(name, None)

	return mod, restore


def test_direct_exit_look_uses_room_exit_name_coloring():
	exits, restore = load_exits_module()
	try:
		exit_obj = exits.Exit()
		exit_obj.key = "(O)ut"
		exit_obj.id = 302
		exit_obj.db = types.SimpleNamespace(desc="A door out.", dark=False)
		exit_obj.access = lambda *_args, **_kwargs: True
		looker = types.SimpleNamespace(check_permstring=lambda _perm: False)

		appearance = exit_obj.return_appearance(looker)

		assert format_exit_name("(O)ut") == "|c(|wO|c)ut|n"
		assert appearance.startswith("|c(|wO|c)ut|n\nA door out.")
	finally:
		restore()


def test_builder_exit_look_keeps_metadata_after_colored_name():
	exits, restore = load_exits_module()
	try:
		exit_obj = exits.Exit()
		exit_obj.key = "(S)ecret"
		exit_obj.id = 303
		exit_obj.db = types.SimpleNamespace(desc=None, dark=True)
		exit_obj.access = lambda *_args, **_kwargs: False
		looker = types.SimpleNamespace(check_permstring=lambda _perm: True)

		appearance = exit_obj.return_appearance(looker)

		assert appearance.startswith("|c(|wS|c)ecret|n |y(#303)|n [|rLocked|n |mDark|n]")
		assert "This is an exit." in appearance
	finally:
		restore()
