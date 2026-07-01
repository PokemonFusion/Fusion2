from __future__ import annotations

import datetime
from typing import Any, Dict, List, Optional

from evennia import DefaultScript, ScriptDB


STAFF_LOCK = "perm(Admin) or perm(Helper)"
DEFAULT_BOARD_DEFINITIONS = [
	("Staff", f"read:{STAFF_LOCK};post:{STAFF_LOCK};delete:{STAFF_LOCK};edit:{STAFF_LOCK}"),
	("Announcements", f"read:all();post:{STAFF_LOCK};delete:{STAFF_LOCK};edit:{STAFF_LOCK}"),
	("Events", f"read:all();post:{STAFF_LOCK};delete:{STAFF_LOCK};edit:{STAFF_LOCK}"),
	("Public - OOC", None),
	("Suggestions - OOC", None),
	("Theme Questions - OOC", None),
	("Removed Characters", f"read:all();post:{STAFF_LOCK};delete:{STAFF_LOCK};edit:{STAFF_LOCK}"),
	("Not Quite Pokemon - OOC", f"read:all();post:{STAFF_LOCK};delete:{STAFF_LOCK};edit:{STAFF_LOCK}"),
	("Journals - IC", None),
	("Errors & Bugs - OOC", None),
	("Errors & Bugs - Fixed", f"read:all();post:{STAFF_LOCK};delete:{STAFF_LOCK};edit:{STAFF_LOCK}"),
	("News - IC", f"read:all();post:{STAFF_LOCK};delete:{STAFF_LOCK};edit:{STAFF_LOCK}"),
	("Change Log - OOC", f"read:all();post:{STAFF_LOCK};delete:{STAFF_LOCK};edit:{STAFF_LOCK}"),
	("Scene announcements", None),
	("Pokemon Friend Codes - OOC", None),
]


class BBoard(DefaultScript):
	"""Simple bulletin board stored as a persistent Script.

	Posts are kept in ``self.db.posts`` as a list of dictionaries with keys
	``subject``, ``body``, ``author`` (Character name), ``author_dbref``,
	``created`` and optional ``edited`` timestamps.
	"""

	def at_script_creation(self):
		self.persistent = True
		if not self.db.posts:
			self.db.posts = []
		if not self.db.read_tracking:
			# {char_dbref: {"post_ids": [...]}}
			# Legacy int values are migrated lazily when a player checks a board.
			self.db.read_tracking = {}
		if not self.locks.get():
			# default locks: anyone can read/post, only Admins delete/edit
			self.locks.add("read:all();post:all();delete:perm(Admin);edit:perm(Admin)")

	# ---------------------------------------------------------------------
	# Post handling
	# ---------------------------------------------------------------------
	def num_posts(self) -> int:
		return len(self.db.posts or [])

	def posts(self) -> List[Dict[str, Any]]:
		"""Return posts with stable ids populated for legacy rows."""
		posts = list(self.db.posts or [])
		changed = False
		for index, post in enumerate(posts, 1):
			if not post.get("id"):
				post["id"] = self._post_id(post, index)
				changed = True
		if changed:
			self.db.posts = posts
		return posts

	def _post_id(self, post: Dict[str, Any], index: int | None = None) -> str:
		"""Return a stable post identifier, deriving one for pre-id posts."""
		if post.get("id"):
			return str(post["id"])
		created = post.get("created")
		if hasattr(created, "isoformat"):
			return str(created.isoformat())
		if created:
			return str(created)
		return f"legacy-{index or 0}"

	def post(self, subject: str, body: str, author) -> int:
		"""Create a new post by the given Character ``author``."""
		posts = self.posts()
		created = datetime.datetime.utcnow()
		posts.append(
			{
				"id": f"{int(created.timestamp() * 1000000)}-{len(posts) + 1}",
				"subject": subject,
				"body": body,
				"author": author.key,
				"author_dbref": author.dbref,
				"created": created,
				"edited": None,
			}
		)
		self.db.posts = posts
		index = len(posts)
		self.mark_read(author, index)
		self.notify_new_post(author, index, posts[-1])
		return index

	def add_post(self, post: Dict[str, Any]):
		"""Add an existing post dict without modification."""
		posts = self.posts()
		if not post.get("id"):
			post["id"] = self._post_id(post, len(posts) + 1)
		posts.append(post)
		self.db.posts = posts
		return len(posts)

	def get_post(self, index: int) -> Optional[Dict[str, Any]]:
		posts = self.posts()
		if 1 <= index <= len(posts):
			return posts[index - 1]
		return None

	def edit_post(self, index: int, body: str) -> bool:
		post = self.get_post(index)
		if not post:
			return False
		post["body"] = body
		post["edited"] = datetime.datetime.utcnow()
		posts = self.posts()
		posts[index - 1] = post
		self.db.posts = posts
		return True

	def delete_post(self, index: int) -> bool:
		posts = self.posts()
		if 1 <= index <= len(posts):
			posts.pop(index - 1)
			self.db.posts = posts
			return True
		return False

	# ------------------------------------------------------------------
	# Read tracking
	# ------------------------------------------------------------------
	def _reader_key(self, reader) -> str:
		return str(
			getattr(reader, "dbref", None)
			or getattr(reader, "id", None)
			or getattr(reader, "pk", None)
			or getattr(reader, "key", None)
			or id(reader)
		)

	def _read_post_ids(self, reader) -> tuple[str, set[str], dict]:
		"""Return read post ids, migrating old last-index records lazily."""
		reads = dict(self.db.read_tracking or {})
		key = self._reader_key(reader)
		raw = reads.get(key)
		legacy_key = getattr(reader, "dbref", None)
		if raw is None and legacy_key in reads:
			raw = reads.pop(legacy_key)
		if isinstance(raw, dict):
			ids = {str(post_id) for post_id in raw.get("post_ids", [])}
		elif isinstance(raw, int):
			ids = {
				self._post_id(post, index)
				for index, post in enumerate(self.posts()[: max(raw, 0)], 1)
			}
			reads[key] = {"post_ids": sorted(ids)}
			self.db.read_tracking = reads
		elif isinstance(raw, (list, set, tuple)):
			ids = {str(post_id) for post_id in raw}
		else:
			ids = set()
		return key, ids, reads

	def _save_read_post_ids(self, reader, ids: set[str]):
		reads = dict(self.db.read_tracking or {})
		key = self._reader_key(reader)
		reads[key] = {"post_ids": sorted(ids)}
		self.db.read_tracking = reads

	def mark_read(self, reader, index: int):
		"""Mark one post read for ``reader``."""
		post = self.get_post(index)
		if not post:
			return
		_, ids, _ = self._read_post_ids(reader)
		ids.add(self._post_id(post, index))
		self._save_read_post_ids(reader, ids)

	def mark_all_read(self, reader):
		"""Mark all current posts read for ``reader``."""
		ids = {self._post_id(post, index) for index, post in enumerate(self.posts(), 1)}
		self._save_read_post_ids(reader, ids)

	def has_read(self, reader, index: int) -> bool:
		post = self.get_post(index)
		if not post:
			return False
		_, ids, _ = self._read_post_ids(reader)
		return self._post_id(post, index) in ids

	def unread_count(self, reader) -> int:
		"""Return how many posts ``reader`` (Character) hasn't read yet."""
		return sum(1 for index, _post in enumerate(self.posts(), 1) if not self.has_read(reader, index))

	def first_unread_index(self, reader) -> int | None:
		"""Return the 1-based index of the first unread post for ``reader``."""
		for index, _post in enumerate(self.posts(), 1):
			if not self.has_read(reader, index):
				return index
		return None

	def notify_new_post(self, author, index: int, post: Dict[str, Any]) -> None:
		"""Notify online characters who can read this board."""
		try:
			from evennia import SESSION_HANDLER
		except Exception:
			return

		get_sessions = getattr(SESSION_HANDLER, "get_sessions", None)
		if not callable(get_sessions):
			return
		author_dbref = getattr(author, "dbref", None)
		for session in get_sessions():
			get_puppet = getattr(session, "get_puppet", None)
			receiver = get_puppet() if callable(get_puppet) else None
			if not receiver or getattr(receiver, "dbref", None) == author_dbref:
				continue
			try:
				if not self.access(receiver, "read"):
					continue
			except Exception:
				continue
			receiver.msg(
				f"|gThere is a new message at |w{self.key}|g "
				f"(|r#{index}|g) by |w{post.get('author', getattr(author, 'key', 'Someone'))}|g: "
				f"|c{post.get('subject', '(No subject)')}|n"
			)


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------


def get_board(name: str) -> Optional[BBoard]:
	boards = ScriptDB.objects.typeclass_search(BBoard, key=name)
	return boards[0] if boards else None


def list_boards() -> List[BBoard]:
	return ScriptDB.objects.typeclass_search(BBoard)


def create_board(name: str, lockstring: str | None = None) -> BBoard:
	board = get_board(name)
	if board:
		return board
	board = ScriptDB.create(typeclass=BBoard, key=name)
	if lockstring:
		board.locks.add(lockstring)
	return board


def seed_default_boards() -> dict[str, list[BBoard]]:
	"""Create the PF1-style default board sections if missing."""
	created: list[BBoard] = []
	existing: list[BBoard] = []
	for sort_order, (name, lockstring) in enumerate(DEFAULT_BOARD_DEFINITIONS, 1):
		board = get_board(name)
		if board:
			existing.append(board)
		else:
			board = create_board(name, lockstring=lockstring)
			created.append(board)
		board.db.sort_order = sort_order
	return {"created": created, "existing": existing}
