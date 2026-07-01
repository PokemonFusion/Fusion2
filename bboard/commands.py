from __future__ import annotations

from typing import Iterable

from evennia import Command
from evennia.utils.utils import datetime_format

from utils.enhanced_evmenu import EnhancedEvMenu

from .bboard import BBoard, create_board, get_board, list_boards, seed_default_boards


def _board_sort_key(board: BBoard) -> tuple[int, str]:
	sort_order = getattr(getattr(board, "db", None), "sort_order", None)
	try:
		sort_order = int(sort_order)
	except (TypeError, ValueError):
		sort_order = 999999
	return sort_order, str(getattr(board, "key", "")).lower()


def _all_boards() -> list[BBoard]:
	return sorted(list(list_boards()), key=_board_sort_key)


def _can_access(board: BBoard, caller, access_type: str) -> bool:
	access = getattr(board, "access", None)
	if not callable(access):
		return True
	try:
		return bool(access(caller, access_type))
	except TypeError:
		return bool(access(caller, access_type, default=False))


def _visible_boards(caller) -> list[BBoard]:
	return [board for board in _all_boards() if _can_access(board, caller, "read")]


def _staff_reveals_anonymous(caller) -> bool:
	check = getattr(caller, "check_permstring", None)
	if callable(check):
		return bool(check("Admin") or check("Builder") or check("Helper"))
	permissions = getattr(caller, "permissions", None)
	all_perms = getattr(permissions, "all", None)
	if callable(all_perms):
		return any(perm in {"Admin", "Builder", "Helper"} for perm in all_perms())
	return False


def _author_name(board: BBoard, post: dict, caller) -> str:
	anon = getattr(getattr(board, "db", None), "anonymous_name", None)
	if anon and not _staff_reveals_anonymous(caller):
		return str(anon)
	return str(post.get("author") or "Unknown")


def _board_posts(board: BBoard) -> list[dict]:
	posts = getattr(board, "posts", None)
	if callable(posts):
		return posts()
	return list(getattr(getattr(board, "db", None), "posts", None) or [])


def _num_posts(board: BBoard) -> int:
	num_posts = getattr(board, "num_posts", None)
	if callable(num_posts):
		return int(num_posts())
	return len(_board_posts(board))


def get_current_board(caller) -> BBoard | None:
	name = getattr(getattr(caller, "db", None), "current_board", None)
	if name:
		return get_board(name)
	return None


def _set_current_board(caller, board: BBoard) -> None:
	setattr(caller.db, "current_board", board.key)


def _find_board_by_name(name: str) -> list[BBoard]:
	needle = name.strip().lower()
	boards = _all_boards()
	exact = [board for board in boards if board.key.lower() == needle]
	if exact:
		return exact
	return [board for board in boards if board.key.lower().startswith(needle)]


def resolve_board(caller, raw: str, *, allow_current: bool = False) -> BBoard | None:
	name = (raw or "").strip()
	if not name and allow_current:
		board = get_current_board(caller)
		if board and _can_access(board, caller, "read"):
			return board
	if not name:
		caller.msg("Usage: +bbread <board> or +bbread <board>/<post>")
		return None

	if name.isdigit():
		index = int(name)
		boards = _visible_boards(caller)
		if 1 <= index <= len(boards):
			return boards[index - 1]
		caller.msg("That board does not exist.")
		return None

	matches = _find_board_by_name(name)
	visible = [board for board in matches if _can_access(board, caller, "read")]
	if not visible:
		caller.msg("That board does not exist.")
		return None
	if len(visible) > 1:
		caller.msg("Multiple boards match: " + ", ".join(board.key for board in visible[:8]))
		return None
	return visible[0]


def _board_number(caller, board: BBoard) -> int | None:
	for index, visible in enumerate(_visible_boards(caller), 1):
		if visible == board or getattr(visible, "key", None) == getattr(board, "key", None):
			return index
	return None


def _parse_unread_filter(raw: str) -> tuple[str, bool]:
	text = raw or ""
	unread = "#unread" in text.lower()
	while "#unread" in text.lower():
		start = text.lower().find("#unread")
		text = f"{text[:start]}{text[start + len('#unread'):]}"
	return " ".join(text.split()), unread


def _parse_positive_int(caller, raw: str, usage: str) -> int | None:
	try:
		value = int(str(raw).strip())
	except (TypeError, ValueError):
		caller.msg(usage)
		return None
	if value < 1:
		caller.msg(usage)
		return None
	return value


def _format_date(value) -> str:
	if not value:
		return "-"
	return datetime_format(value)


def _latest_post_date(board: BBoard) -> str:
	posts = _board_posts(board)
	if not posts:
		return "-"
	return _format_date(posts[-1].get("created"))


def display_board_overview(caller) -> None:
	boards = _visible_boards(caller)
	if not boards:
		caller.msg("No boards available.")
		return

	lines = [
		"|wMessage Board|n",
		"|g" + "-" * 78 + "|n",
		"|w # | Name                                | Last Post        | Unread/Posts |n",
		"|g" + "-" * 78 + "|n",
	]
	for index, board in enumerate(boards, 1):
		postable = _can_access(board, caller, "post")
		color = "|c" if postable else "|y"
		unread = board.unread_count(caller) if hasattr(board, "unread_count") else 0
		total = _num_posts(board)
		lines.append(
			f"{color}{index:2}|n |w{board.key[:35]:35}|n "
			f"{_latest_post_date(board)[:16]:16} "
			f"|c{unread:5}|n/|c{total:<5}|n"
		)
	lines.extend(
		[
			"|g" + "-" * 78 + "|n",
			"|y# = read only|n    |c# = postable|n",
		]
	)
	caller.msg("\n".join(lines))


def display_post_list(caller, board: BBoard, *, unread_only: bool = False) -> None:
	if not _can_access(board, caller, "read"):
		caller.msg("You are not allowed to read this board.")
		return

	board_num = _board_number(caller, board)
	posts = _board_posts(board)
	if not posts:
		caller.msg(f"{board.key} is empty.")
		return

	lines = [
		f"|w{board_num}. {board.key}|n" if board_num else f"|w{board.key}|n",
		"|g" + "-" * 78 + "|n",
		"|w # | Title                           | Name             | When       |n",
		"|g" + "-" * 78 + "|n",
	]
	visible_rows = 0
	for index, post in enumerate(posts, 1):
		has_read = board.has_read(caller, index)
		if unread_only and has_read:
			continue
		visible_rows += 1
		marker = "U" if not has_read else " "
		lines.append(
			f"|c{index:3}{marker}|n |w{str(post.get('subject', '(No subject)'))[:31]:31}|n "
			f"|w{_author_name(board, post, caller)[:16]:16}|n "
			f"{_format_date(post.get('created'))[:11]}"
		)
	if not visible_rows:
		caller.msg(f"No unread posts on {board.key}.")
		return
	lines.append("|g" + "-" * 78 + "|n")
	caller.msg("\n".join(lines))


def read_post(caller, board: BBoard, post_index: int) -> bool:
	if not _can_access(board, caller, "read"):
		caller.msg("You are not allowed to read this board.")
		return False
	post = board.get_post(post_index)
	if not post:
		caller.msg("That post does not exist.")
		return False
	board_num = _board_number(caller, board) or "?"
	lines = [
		f"|cMessage:|n |w{board_num}/{post_index}|n",
		f"|cTitle:|n |w{post.get('subject', '(No subject)')}|n",
		f"|cPoster:|n |w{_author_name(board, post, caller)}|n",
		f"|cTime:|n |w{_format_date(post.get('created'))}|n",
		"|g" + "-" * 78 + "|n",
		str(post.get("body") or ""),
		"|g" + "-" * 78 + "|n",
	]
	board.mark_read(caller, post_index)
	caller.msg("\n".join(lines))
	return True


def _resolve_board_post(caller, raw: str, *, allow_current: bool = False) -> tuple[BBoard, int] | None:
	text = (raw or "").strip()
	if "/" in text:
		board_raw, post_raw = [part.strip() for part in text.split("/", 1)]
		board = resolve_board(caller, board_raw)
		if not board:
			return None
		post_index = _parse_positive_int(caller, post_raw, "Usage: +bbread <board>/<post>")
		if post_index is None:
			return None
		return board, post_index

	if allow_current:
		board = get_current_board(caller)
		if board and text:
			post_index = _parse_positive_int(caller, text, "Usage: +bbremove <board>/<post>")
			if post_index is None:
				return None
			return board, post_index

	caller.msg("Usage: +bbread <board>/<post>")
	return None


def _join_names(boards: Iterable[BBoard]) -> str:
	return ", ".join(str(board.key) for board in boards)


class CmdBBHelp(Command):
	"""Show bulletin board help."""

	key = "+bbhelp"
	aliases = ["+bboard"]
	locks = "cmd:all()"

	def func(self):
		self.caller.msg(
			"\n".join(
				[
					"|yMessage Board|n",
					"|g-------------|n",
					"|y+bbhelp|n                       - This screen.",
					"|y+bbread|n                       - Check the board.",
					"|y+bbread #|n                     - Check a section.",
					"|y+bbread #/#|n                   - Check a post.",
					"|y+bbread # #unread|n             - Check unread posts in a section.",
					"|y+bbpost #|n                     - Post in a section.",
					"|y+bbremove #/#|n                 - Remove a post.",
					"|y+bbcatchup all or #|n           - Mark posts as read.",
					"|y+bbnext [#]|n                   - Read the next unread message.",
					"|y+bbseed|n                       - Staff: create the default board set.",
				]
			)
		)


class CmdBBList(Command):
	"""List boards or posts."""

	key = "+bblist"
	locks = "cmd:all()"

	def func(self):
		raw, unread_only = _parse_unread_filter(self.args)
		if not raw:
			display_board_overview(self.caller)
			return
		board = resolve_board(self.caller, raw)
		if board:
			display_post_list(self.caller, board, unread_only=unread_only)


class CmdBBRead(Command):
	"""Read boards and posts."""

	key = "+bbread"
	locks = "cmd:all()"

	def func(self):
		raw, unread_only = _parse_unread_filter(self.args)
		if not raw:
			display_board_overview(self.caller)
			return

		if "/" in raw:
			ref = _resolve_board_post(self.caller, raw)
			if ref:
				board, post_index = ref
				read_post(self.caller, board, post_index)
			return

		board = resolve_board(self.caller, raw)
		if board:
			display_post_list(self.caller, board, unread_only=unread_only)
			return

		current = get_current_board(self.caller)
		if current and raw.isdigit():
			read_post(self.caller, current, int(raw))


class CmdBBPost(Command):
	"""Create a new post."""

	key = "+bbpost"
	locks = "cmd:all()"

	def func(self):
		board = resolve_board(self.caller, self.args, allow_current=True)
		if not board:
			return
		if not _can_access(board, self.caller, "post"):
			self.caller.msg("You cannot post to this board.")
			return
		_set_current_board(self.caller, board)
		EnhancedEvMenu(self.caller, "menus.bboard", startnode="post_subject", start_kwargs={"board": board})


class CmdBBDelete(Command):
	"""Delete a post."""

	key = "+bbdel"
	aliases = ["+bbremove"]
	locks = "cmd:all()"

	def func(self):
		ref = _resolve_board_post(self.caller, self.args, allow_current=True)
		if not ref:
			return
		board, index = ref
		post = board.get_post(index)
		if not post:
			self.caller.msg("That post does not exist.")
			return
		if post.get("author_dbref") != getattr(self.caller, "dbref", None) and not _can_access(board, self.caller, "delete"):
			self.caller.msg("You do not have permission to delete this post.")
			return
		board.delete_post(index)
		self.caller.msg("Post deleted.")


class CmdBBCatchup(Command):
	"""Mark board posts read."""

	key = "+bbcatchup"
	locks = "cmd:all()"

	def func(self):
		raw = (self.args or "").strip()
		if not raw:
			self.caller.msg("Usage: +bbcatchup all or +bbcatchup <board> [<board> ...]")
			return

		if raw.lower() == "all":
			boards = _visible_boards(self.caller)
			for board in boards:
				board.mark_all_read(self.caller)
			self.caller.msg("All boards now marked as read.")
			return

		resolved = []
		for token in raw.replace(",", " ").split():
			board = resolve_board(self.caller, token)
			if not board:
				return
			board.mark_all_read(self.caller)
			resolved.append(board)
		self.caller.msg(f"Boards {_join_names(resolved)} are now marked as read.")


class CmdBBNext(Command):
	"""Read the next unread board post."""

	key = "+bbnext"
	locks = "cmd:all()"

	def func(self):
		raw = (self.args or "").strip()
		if raw:
			board = resolve_board(self.caller, raw)
			if not board:
				return
			next_index = board.first_unread_index(self.caller)
			if next_index:
				read_post(self.caller, board, next_index)
				return
			self.caller.msg(f"There are no unread messages on {board.key}.")
			return

		for board in _visible_boards(self.caller):
			next_index = board.first_unread_index(self.caller)
			if next_index:
				read_post(self.caller, board, next_index)
				return
		self.caller.msg("There are no more unread messages.")


class CmdBBSet(Command):
	"""Select a board for PF2-style shorthand commands."""

	key = "+bbset"
	locks = "cmd:all()"

	def func(self):
		board = resolve_board(self.caller, self.args)
		if not board:
			return
		_set_current_board(self.caller, board)
		self.caller.msg(f"Board set to {board.key}.")


class CmdBBNew(Command):
	"""Create a new board."""

	key = "+bbnew"
	locks = "cmd:perm(Admin)"

	def func(self):
		name = self.args.strip()
		if not name:
			self.caller.msg("Usage: +bbnew <board>")
			return
		if get_board(name):
			self.caller.msg("Board already exists.")
			return
		create_board(name)
		self.caller.msg(f"Board '{name}' created.")


class CmdBBSeed(Command):
	"""Create the default PF1-style board set."""

	key = "+bbseed"
	locks = "cmd:perm(Admin)"

	def func(self):
		result = seed_default_boards()
		created = result["created"]
		existing = result["existing"]
		if created:
			self.caller.msg(
				f"Created {len(created)} default boards. Existing boards left in place: {len(existing)}."
			)
		else:
			self.caller.msg(f"Default boards already exist ({len(existing)} found).")


class CmdBBEdit(Command):
	"""Edit a post."""

	key = "+bbedit"
	locks = "cmd:perm(Admin)"

	def func(self):
		ref = _resolve_board_post(self.caller, self.args, allow_current=True)
		if not ref:
			return
		board, index = ref
		post = board.get_post(index)
		if not post:
			self.caller.msg("That post does not exist.")
			return
		EnhancedEvMenu(
			self.caller,
			"menus.bboard",
			startnode="edit_body",
			start_kwargs={"board": board, "index": index, "post": post},
		)


class CmdBBMove(Command):
	"""Move a post to another board."""

	key = "+bbmove"
	locks = "cmd:perm(Admin)"

	def func(self):
		if "=" in self.args:
			left, dest_name = [part.strip() for part in self.args.split("=", 1)]
		else:
			parts = self.args.split(None, 1)
			if len(parts) != 2:
				self.caller.msg("Usage: +bbmove <board>/<post> = <board>")
				return
			left, dest_name = parts
		ref = _resolve_board_post(self.caller, left, allow_current=True)
		if not ref:
			return
		board, index = ref
		post = board.get_post(index)
		if not post:
			self.caller.msg("That post does not exist.")
			return
		dest = resolve_board(self.caller, dest_name)
		if not dest:
			return
		board.delete_post(index)
		dest.add_post(post)
		self.caller.msg(f"Post moved to {dest.key}.")


class CmdBBPurge(Command):
	"""Remove all posts on a board."""

	key = "+bbpurge"
	locks = "cmd:perm(Admin)"

	def func(self):
		board = resolve_board(self.caller, self.args, allow_current=True)
		if not board:
			return
		board.db.posts = []
		board.db.read_tracking = {}
		self.caller.msg(f"Purged posts on {board.key}.")


class CmdBBLock(Command):
	"""Set board locks."""

	key = "+bblock"
	locks = "cmd:perm(Admin)"

	def func(self):
		if "=" not in self.args:
			self.caller.msg("Usage: +bblock <board> = <lockstring>")
			return
		boardname, lockstring = [part.strip() for part in self.args.split("=", 1)]
		board = resolve_board(self.caller, boardname)
		if not board:
			return
		board.locks.add(lockstring)
		self.caller.msg(f"Locks for {board.key} set to: {lockstring}")
