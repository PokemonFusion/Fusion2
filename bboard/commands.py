from __future__ import annotations

from evennia import Command
from helpers.enhanced_evmenu import EnhancedEvMenu
from evennia.utils.utils import datetime_format

from .bboard import BBoard, create_board, get_board, list_boards


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def get_current_board(caller) -> BBoard | None:
    name = caller.db.current_board
    if name:
        return get_board(name)
    return None


def board_or_error(caller) -> BBoard | None:
    board = get_current_board(caller)
    if not board:
        caller.msg("No board selected. Use +bbset <board> to choose one.")
        return None
    return board


# ---------------------------------------------------------------------------
# Player commands
# ---------------------------------------------------------------------------
class CmdBBList(Command):
    """List boards or posts."""

    key = "+bblist"
    locks = "cmd:all()"

    def func(self):
        if not self.args:
            board = get_current_board(self.caller)
            if not board:
                boards = list_boards()
                if not boards:
                    self.caller.msg("No boards available.")
                    return
                lines = [f"|c{b.key}|n ({b.num_posts()} posts)" for b in boards]
                self.caller.msg("|wAvailable Boards|n:\n" + "\n".join(lines))
                return
            posts = board.db.posts or []
            if not posts:
                self.caller.msg("Board is empty.")
                return
            lines = []
            for i, post in enumerate(posts, 1):
                ts = datetime_format(post["created"])
                prefix = "|y*|n" if not board.has_read(self.caller, i) else " "
                lines.append(
                    f"{prefix}|c{i:3}|n |w{post['subject']}|n by |c{post['author']}|n on {ts}"
                )
            self.caller.msg(f"|wPosts on {board.key}|n:\n" + "\n".join(lines))
        else:
            boards = list_boards()
            if not boards:
                self.caller.msg("No boards available.")
                return
            lines = [f"|c{b.key}|n ({b.num_posts()} posts)" for b in boards]
            self.caller.msg("|wAvailable Boards|n:\n" + "\n".join(lines))


class CmdBBRead(Command):
    """Read a post."""

    key = "+bbread"
    locks = "cmd:all()"

    def parse(self):
        self.index = int(self.args.strip() or 0)

    def func(self):
        board = board_or_error(self.caller)
        if not board:
            return
        if not board.access(self.caller, "read"):
            self.caller.msg("You are not allowed to read this board.")
            return
        post = board.get_post(self.index)
        if not post:
            self.caller.msg("Invalid post number.")
            return
        lines = [
            f"|cPost {self.index}|n - |w{post['subject']}|n",
            f"Author: |c{post['author']}|n   Date: {datetime_format(post['created'])}",
            "-" * 60,
            post["body"],
        ]
        self.caller.msg("\n".join(lines))
        board.mark_read(self.caller, self.index)


class CmdBBPost(Command):
    """Create a new post."""

    key = "+bbpost"
    locks = "cmd:all()"

    def func(self):
        board = board_or_error(self.caller)
        if not board:
            return
        if not board.access(self.caller, "post"):
            self.caller.msg("You cannot post to this board.")
            return
        EnhancedEvMenu(self.caller, "menus.bboard", startnode="post_subject", start_kwargs={"board": board})


class CmdBBDelete(Command):
    """Delete a post."""

    key = "+bbdel"
    locks = "cmd:all()"

    def parse(self):
        self.index = int(self.args.strip() or 0)

    def func(self):
        board = board_or_error(self.caller)
        if not board:
            return
        post = board.get_post(self.index)
        if not post:
            self.caller.msg("Invalid post number.")
            return
        if post["author_dbref"] != self.caller.dbref and not board.access(self.caller, "delete"):
            self.caller.msg("You do not have permission to delete this post.")
            return
        board.delete_post(self.index)
        self.caller.msg("Post deleted.")


class CmdBBSet(Command):
    """Select a board."""

    key = "+bbset"
    locks = "cmd:all()"

    def func(self):
        name = self.args.strip()
        if not name:
            self.caller.msg("Usage: +bbset <board>")
            return
        board = get_board(name)
        if not board:
            self.caller.msg("No such board.")
            return
        self.caller.db.current_board = board.key
        self.caller.msg(f"Board set to {board.key}.")


# ---------------------------------------------------------------------------
# Admin Commands
# ---------------------------------------------------------------------------
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


class CmdBBEdit(Command):
    """Edit a post."""

    key = "+bbedit"
    locks = "cmd:perm(Admin)"

    def parse(self):
        self.index = int(self.args.strip() or 0)

    def func(self):
        board = board_or_error(self.caller)
        if not board:
            return
        post = board.get_post(self.index)
        if not post:
            self.caller.msg("Invalid post number.")
            return
        EnhancedEvMenu(
            self.caller,
            "menus.bboard",
            startnode="edit_body",
            start_kwargs={"board": board, "index": self.index, "post": post},
        )


class CmdBBMove(Command):
    """Move a post to another board."""

    key = "+bbmove"
    locks = "cmd:perm(Admin)"

    def func(self):
        if not self.args:
            self.caller.msg("Usage: +bbmove <#> <board>")
            return
        try:
            num, boardname = self.args.split(None, 1)
            index = int(num)
        except ValueError:
            self.caller.msg("Usage: +bbmove <#> <board>")
            return
        board = board_or_error(self.caller)
        if not board:
            return
        post = board.get_post(index)
        if not post:
            self.caller.msg("Invalid post number.")
            return
        dest = get_board(boardname)
        if not dest:
            self.caller.msg("No such destination board.")
            return
        board.delete_post(index)
        dest.add_post(post)
        self.caller.msg(f"Post moved to {dest.key}.")


class CmdBBPurge(Command):
    """Remove all posts on a board."""

    key = "+bbpurge"
    locks = "cmd:perm(Admin)"

    def func(self):
        name = self.args.strip() or self.caller.db.current_board
        if not name:
            self.caller.msg("Usage: +bbpurge <board>")
            return
        board = get_board(name)
        if not board:
            self.caller.msg("No such board.")
            return
        board.db.posts = []
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
        board = get_board(boardname)
        if not board:
            self.caller.msg("No such board.")
            return
        board.locks.add(lockstring)
        self.caller.msg(f"Locks for {board.key} set to: {lockstring}")

