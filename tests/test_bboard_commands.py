import importlib.util
import os
import sys
import types
from datetime import datetime


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)


def load_bboard_commands():
	originals = {
		name: sys.modules.get(name)
		for name in (
			"evennia",
			"evennia.utils",
			"evennia.utils.utils",
			"utils.enhanced_evmenu",
			"bboard.bboard",
			"bboard.commands",
		)
	}

	class FakeScriptDB:
		objects = types.SimpleNamespace(typeclass_search=lambda *_args, **_kwargs: [])

	class FakeDefaultScript:
		pass

	class FakeSessionHandler:
		def get_sessions(self):
			return []

	fake_evennia = types.ModuleType("evennia")
	fake_evennia.Command = type("Command", (), {})
	fake_evennia.DefaultScript = FakeDefaultScript
	fake_evennia.ScriptDB = FakeScriptDB
	fake_evennia.SESSION_HANDLER = FakeSessionHandler()
	sys.modules["evennia"] = fake_evennia

	fake_utils = types.ModuleType("evennia.utils")
	fake_utils_utils = types.ModuleType("evennia.utils.utils")
	fake_utils_utils.datetime_format = lambda value: value.strftime("%Y-%m-%d") if hasattr(value, "strftime") else str(value)
	fake_utils.utils = fake_utils_utils
	sys.modules["evennia.utils"] = fake_utils
	sys.modules["evennia.utils.utils"] = fake_utils_utils

	fake_enhanced = types.ModuleType("utils.enhanced_evmenu")
	fake_enhanced.calls = []

	def fake_menu(caller, menu, startnode=None, start_kwargs=None):
		fake_enhanced.calls.append((caller, menu, startnode, start_kwargs))

	fake_enhanced.EnhancedEvMenu = fake_menu
	sys.modules["utils.enhanced_evmenu"] = fake_enhanced

	sys.modules.pop("bboard.bboard", None)
	path = os.path.join(ROOT, "bboard", "commands.py")
	spec = importlib.util.spec_from_file_location("bboard.commands", path)
	mod = importlib.util.module_from_spec(spec)
	sys.modules[spec.name] = mod
	spec.loader.exec_module(mod)

	def restore():
		sys.modules.pop("bboard.commands", None)
		sys.modules.pop("bboard.bboard", None)
		for name, original in originals.items():
			if original is not None:
				sys.modules[name] = original
			else:
				sys.modules.pop(name, None)

	return mod, fake_enhanced, restore


class FakeDB:
	pass


class FakeCaller:
	def __init__(self, key="Ash", dbref="#1", perms=()):
		self.key = key
		self.dbref = dbref
		self.db = FakeDB()
		self.messages = []
		self._perms = set(perms)

	def msg(self, message):
		self.messages.append(message)

	def check_permstring(self, perm):
		return perm in self._perms


class FakeLocks:
	def add(self, lockstring):
		self.lockstring = lockstring


class FakeBoard:
	def __init__(self, key, posts=(), *, read=True, post=True, delete=False, sort_order=None):
		self.key = key
		self.db = FakeDB()
		self.db.posts = list(posts)
		self.db.read_tracking = {}
		self.db.sort_order = sort_order
		self.locks = FakeLocks()
		self._access = {"read": read, "post": post, "delete": delete, "edit": delete}
		self.deleted = []

	def access(self, _caller, access_type, **_kwargs):
		return self._access.get(access_type, False)

	def posts(self):
		return list(self.db.posts)

	def num_posts(self):
		return len(self.db.posts)

	def get_post(self, index):
		if 1 <= index <= len(self.db.posts):
			return self.db.posts[index - 1]
		return None

	def _read_ids(self, caller):
		return self.db.read_tracking.setdefault(caller.dbref, set())

	def has_read(self, caller, index):
		post = self.get_post(index)
		return bool(post and post["id"] in self._read_ids(caller))

	def mark_read(self, caller, index):
		post = self.get_post(index)
		if post:
			self._read_ids(caller).add(post["id"])

	def mark_all_read(self, caller):
		self._read_ids(caller).update(post["id"] for post in self.db.posts)

	def unread_count(self, caller):
		return sum(1 for index, _post in enumerate(self.db.posts, 1) if not self.has_read(caller, index))

	def first_unread_index(self, caller):
		for index, _post in enumerate(self.db.posts, 1):
			if not self.has_read(caller, index):
				return index
		return None

	def delete_post(self, index):
		if 1 <= index <= len(self.db.posts):
			self.deleted.append(self.db.posts.pop(index - 1))
			return True
		return False

	def add_post(self, post):
		self.db.posts.append(post)


def post(ident, subject, author="Misty", body="Body"):
	return {
		"id": ident,
		"subject": subject,
		"author": author,
		"author_dbref": "#2",
		"body": body,
		"created": datetime(2026, 1, int(ident[-1])),
	}


def install_boards(mod, boards):
	mod.list_boards = lambda: list(boards)
	mod.get_board = lambda name: next((board for board in boards if board.key == name), None)


def call(cmd_cls, caller, args=""):
	cmd = cmd_cls()
	cmd.caller = caller
	cmd.args = args
	cmd.func()
	return caller.messages[-1]


def test_bbread_without_args_shows_pf1_style_board_overview():
	mod, _menu, restore = load_bboard_commands()
	caller = FakeCaller()
	announcements = FakeBoard("Announcements", [post("p1", "Welcome"), post("p2", "Rules")], sort_order=1)
	staff = FakeBoard("Staff", [post("p3", "Hidden")], read=False, sort_order=2)
	announcements.mark_read(caller, 1)
	install_boards(mod, [staff, announcements])

	try:
		output = call(mod.CmdBBRead, caller)
	finally:
		restore()

	assert "Message Board" in output
	assert "Announcements" in output
	assert "Staff" not in output
	assert "1" in output
	assert "/|c2" in output


def test_bbread_board_post_reads_and_marks_specific_post():
	mod, _menu, restore = load_bboard_commands()
	caller = FakeCaller()
	board = FakeBoard("Announcements", [post("p1", "Welcome"), post("p2", "Rules", body="Read this.")], sort_order=1)
	install_boards(mod, [board])

	try:
		output = call(mod.CmdBBRead, caller, "1/2")
	finally:
		restore()

	assert "Message:" in output
	assert "1/2" in output
	assert "Rules" in output
	assert "Read this." in output
	assert board.has_read(caller, 2)


def test_bbnext_reads_first_unread_visible_post():
	mod, _menu, restore = load_bboard_commands()
	caller = FakeCaller()
	first = FakeBoard("Announcements", [post("p1", "Welcome")], sort_order=1)
	second = FakeBoard("Public", [post("p2", "Hello")], sort_order=2)
	first.mark_all_read(caller)
	install_boards(mod, [second, first])

	try:
		output = call(mod.CmdBBNext, caller)
	finally:
		restore()

	assert "Public" not in output
	assert "Hello" in output
	assert second.has_read(caller, 1)


def test_bbnext_with_board_number_reads_next_unread_from_that_board_only():
	mod, _menu, restore = load_bboard_commands()
	caller = FakeCaller()
	first = FakeBoard("Announcements", [post("p1", "Welcome")], sort_order=1)
	second = FakeBoard("Public", [post("p2", "Hello")], sort_order=2)
	install_boards(mod, [second, first])

	try:
		output = call(mod.CmdBBNext, caller, "2")
	finally:
		restore()

	assert "Hello" in output
	assert second.has_read(caller, 1)
	assert not first.has_read(caller, 1)


def test_bbnext_with_board_number_reports_when_board_has_no_unread_posts():
	mod, _menu, restore = load_bboard_commands()
	caller = FakeCaller()
	board = FakeBoard("Announcements", [post("p1", "Welcome")], sort_order=1)
	board.mark_all_read(caller)
	install_boards(mod, [board])

	try:
		output = call(mod.CmdBBNext, caller, "1")
	finally:
		restore()

	assert output == "There are no unread messages on Announcements."


def test_bbcatchup_all_marks_visible_posts_read():
	mod, _menu, restore = load_bboard_commands()
	caller = FakeCaller()
	first = FakeBoard("Announcements", [post("p1", "Welcome")], sort_order=1)
	second = FakeBoard("Staff", [post("p2", "Hidden")], read=False, sort_order=2)
	install_boards(mod, [first, second])

	try:
		output = call(mod.CmdBBCatchup, caller, "all")
	finally:
		restore()

	assert output == "All boards now marked as read."
	assert first.unread_count(caller) == 0
	assert second.unread_count(caller) == 1


def test_bbpost_accepts_pf1_board_number_and_opens_editor_menu():
	mod, menu, restore = load_bboard_commands()
	caller = FakeCaller()
	board = FakeBoard("Announcements", [], sort_order=1)
	install_boards(mod, [board])

	try:
		cmd = mod.CmdBBPost()
		cmd.caller = caller
		cmd.args = "1"
		cmd.func()
	finally:
		restore()

	assert menu.calls
	_call_caller, menu_name, startnode, kwargs = menu.calls[-1]
	assert menu_name == "menus.bboard"
	assert startnode == "post_subject"
	assert kwargs == {"board": board}
	assert caller.db.current_board == "Announcements"


def test_bbremove_alias_accepts_pf1_board_post_reference():
	mod, _menu, restore = load_bboard_commands()
	caller = FakeCaller(dbref="#2")
	board = FakeBoard("Announcements", [post("p1", "Welcome")], sort_order=1)
	install_boards(mod, [board])

	try:
		output = call(mod.CmdBBDelete, caller, "1/1")
	finally:
		restore()

	assert output == "Post deleted."
	assert board.num_posts() == 0


def test_bbseed_reports_created_default_boards(monkeypatch):
	mod, _menu, restore = load_bboard_commands()
	caller = FakeCaller(perms=("Admin",))
	created = [FakeBoard("Announcements"), FakeBoard("Public - OOC")]
	existing = [FakeBoard("Staff")]
	monkeypatch.setattr(mod, "seed_default_boards", lambda: {"created": created, "existing": existing})

	try:
		output = call(mod.CmdBBSeed, caller)
	finally:
		restore()

	assert output == "Created 2 default boards. Existing boards left in place: 1."


def test_bboard_migrates_legacy_index_reads_to_stable_post_ids():
	_mod, _menu, restore = load_bboard_commands()
	bboard_mod = sys.modules["bboard.bboard"]
	caller = FakeCaller()
	board = bboard_mod.BBoard()
	board.key = "Announcements"
	board.db = FakeDB()
	board.db.posts = [post("p1", "Welcome"), post("p2", "Rules")]
	board.db.read_tracking = {caller.dbref: 1}
	board.locks = FakeLocks()

	try:
		assert board.has_read(caller, 1)
		assert not board.has_read(caller, 2)
		board.delete_post(1)
		assert not board.has_read(caller, 1)
	finally:
		restore()
