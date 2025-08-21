from __future__ import annotations

import datetime
from typing import Any, Dict, List, Optional

from evennia import DefaultScript, ScriptDB


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
            # {char_dbref: last_read_index}
            # Using Character dbrefs keeps read status per-character.
            self.db.read_tracking = {}
        if not self.locks.get():
            # default locks: anyone can read/post, only Admins delete/edit
            self.locks.add(
                "read:all();post:all();delete:perm(Admin);edit:perm(Admin)"
            )

    # ---------------------------------------------------------------------
    # Post handling
    # ---------------------------------------------------------------------
    def num_posts(self) -> int:
        return len(self.db.posts or [])

    def post(self, subject: str, body: str, author) -> int:
        """Create a new post by the given Character ``author``."""
        posts = list(self.db.posts or [])
        posts.append(
            {
                "subject": subject,
                "body": body,
                "author": author.key,
                "author_dbref": author.dbref,
                "created": datetime.datetime.utcnow(),
                "edited": None,
            }
        )
        self.db.posts = posts
        return len(posts)

    def add_post(self, post: Dict[str, Any]):
        """Add an existing post dict without modification."""
        posts = list(self.db.posts or [])
        posts.append(post)
        self.db.posts = posts
        return len(posts)

    def get_post(self, index: int) -> Optional[Dict[str, Any]]:
        posts = list(self.db.posts or [])
        if 1 <= index <= len(posts):
            return posts[index - 1]
        return None

    def edit_post(self, index: int, body: str) -> bool:
        post = self.get_post(index)
        if not post:
            return False
        post["body"] = body
        post["edited"] = datetime.datetime.utcnow()
        posts = list(self.db.posts or [])
        posts[index - 1] = post
        self.db.posts = posts
        return True

    def delete_post(self, index: int) -> bool:
        posts = list(self.db.posts or [])
        if 1 <= index <= len(posts):
            posts.pop(index - 1)
            self.db.posts = posts
            return True
        return False

    # ------------------------------------------------------------------
    # Read tracking
    # ------------------------------------------------------------------
    def mark_read(self, reader, index: int):
        """Mark that ``reader`` (Character) has read up to ``index``."""
        reads = dict(self.db.read_tracking or {})
        prev = reads.get(reader.dbref, 0)
        if index > prev:
            reads[reader.dbref] = index
            self.db.read_tracking = reads

    def has_read(self, reader, index: int) -> bool:
        reads = self.db.read_tracking or {}
        return reads.get(reader.dbref, 0) >= index

    def unread_count(self, reader) -> int:
        """Return how many posts ``reader`` (Character) hasn't read yet."""
        reads = self.db.read_tracking or {}
        last = reads.get(reader.dbref, 0)
        return max(0, self.num_posts() - last)


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
