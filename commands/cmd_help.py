from __future__ import annotations

from collections import defaultdict
from itertools import chain

from evennia.commands.default.help import (
    CmdHelp as DefaultCmdHelp,
    DEFAULT_HELP_CATEGORY,
)
from evennia.utils.utils import format_grid, pad


class CmdHelp(DefaultCmdHelp):
    """Help command supporting hierarchical categories."""

    def collect_topics(self, caller, mode="list"):
        cmd, db, file = super().collect_topics(caller, mode=mode)
        for entry in chain(cmd.values(), db.values(), file.values()):
            cat = getattr(entry, "help_category", DEFAULT_HELP_CATEGORY)
            entry.category_path = [p.strip() for p in cat.split("/") if p.strip()]
        return cmd, db, file

    # internal helper
    def _add_to_tree(self, tree, path, topics):
        if not path:
            tree.setdefault("_topics", []).extend(topics)
            return
        head, *rest = path
        node = tree.setdefault(head, {})
        self._add_to_tree(node, rest, topics)

    def format_help_index(
        self, cmd_help_dict=None, db_help_dict=None, title_lone_category=False, click_topics=True
    ):
        cmd_tree: dict[str, dict] = {}
        db_tree: dict[str, dict] = {}
        for cat, topics in (cmd_help_dict or {}).items():
            self._add_to_tree(cmd_tree, [p.strip() for p in cat.split("/") if p.strip()], topics)
        for cat, topics in (db_help_dict or {}).items():
            self._add_to_tree(db_tree, [p.strip() for p in cat.split("/") if p.strip()], topics)

        width = self.client_width()

        def render(tree, indent=0):
            lines = []
            for cat in sorted(k for k in tree.keys() if k != "_topics"):
                node = tree[cat]
                cat_str = f"-- {cat.title()} "
                header = (
                    self.index_category_clr
                    + " " * (indent * 2)
                    + cat_str
                    + "-" * max(0, width - len(cat_str) - indent * 2)
                    + self.index_topic_clr
                )
                lines.append(header)
                topics = sorted(set(node.get("_topics", [])))
                if topics:
                    if click_topics:
                        topics = [f"|lchelp {t}|lt{t}|le" for t in topics]
                    gridrows = format_grid(
                        topics,
                        width=width - indent * 2,
                        sep="  ",
                        line_prefix=self.index_topic_clr,
                    )
                    lines.extend(" " * (indent * 2) + row for row in gridrows)
                lines.extend(render(node, indent + 1))
            return lines

        cmd_lines = render(cmd_tree)
        db_lines = render(db_tree)

        parts = []
        if cmd_lines:
            parts.append(
                self.index_type_separator_clr
                + pad("Commands", width=width, fillchar="-")
                + self.index_topic_clr
            )
            parts.extend(cmd_lines)
        if db_lines:
            parts.append(
                self.index_type_separator_clr
                + pad("Game & World", width=width, fillchar="-")
                + self.index_topic_clr
            )
            parts.extend(db_lines)
        return "\n".join(parts)
