from __future__ import annotations

from collections import defaultdict
from itertools import chain

from evennia.commands.default.help import (
    DEFAULT_HELP_CATEGORY,
)
from evennia.commands.default.help import (
    CmdHelp as DefaultCmdHelp,
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

    def parse(self):
        """Store the full query path for later use."""
        if self.args:
            self.query_parts = [
                part.strip().lower() for part in self.args.split(self.subtopic_separator_char)
            ]
            self.topic = self.query_parts[0]
            self.subtopics = self.query_parts[1:]
        else:
            self.query_parts = []
            self.topic = ""
            self.subtopics = []

    def func(self):
        """Simplified help command supporting nested categories."""
        caller = self.caller
        query_parts = getattr(self, "query_parts", [])

        if not query_parts:
            cmd_help, db_help, file_help = self.collect_topics(caller, mode="list")
            file_db = {**file_help, **db_help}
            cmd_cat = defaultdict(list)
            db_cat = defaultdict(list)
            for key, cmd in cmd_help.items():
                cmd_cat[cmd.help_category].append(key)
            for key, entry in file_db.items():
                db_cat[entry.help_category].append(key)
            output = self.format_help_index(cmd_cat, db_cat, click_topics=self.clickable_topics)
            self.msg_help(output)
            return

        cmd_help, db_help, file_help = self.collect_topics(caller, mode="query")
        file_db = {**file_help, **db_help}
        all_topics = {**file_db, **cmd_help}
        category_map = {topic.help_category.lower(): topic.help_category for topic in all_topics.values()}
        categories = set(category_map.keys())

        candidate_topic, remaining = None, []
        for i in range(len(query_parts), 0, -1):
            candidate = "/".join(query_parts[:i])
            if (
                candidate in all_topics
                or candidate in categories
                or any(cat.startswith(candidate + "/") for cat in categories)
            ):
                candidate_topic = candidate
                remaining = query_parts[i:]
                break

        if candidate_topic is None:
            self.msg_help(f"No help entry found for '{'/'.join(query_parts)}'")
            return

        if candidate_topic in all_topics:
            entry = all_topics[candidate_topic]
            text = getattr(entry, "entrytext", "")
            self.msg_help(self.format_help_entry(topic=candidate_topic, help_text=text))
            return

        # it's a category
        category_name = category_map.get(candidate_topic, candidate_topic)
        prefix = candidate_topic + "/"
        subcats = [category_map[c] for c in categories if c.startswith(prefix)]
        cmds_in_cat = [key for key, cmd in cmd_help.items() if cmd.help_category.lower() == candidate_topic]
        topics_in_cat = [key for key, t in file_db.items() if t.help_category.lower() == candidate_topic]

        if subcats:
            cat_dict = {subcat: [] for subcat in subcats}
            if cmds_in_cat or topics_in_cat:
                cat_dict[category_name] = cmds_in_cat + topics_in_cat
            output = self.format_help_index(
                cat_dict,
                {},
                title_lone_category=True,
                click_topics=self.clickable_topics,
            )
        else:
            output = self.format_help_index(
                {category_name: cmds_in_cat},
                {category_name: topics_in_cat},
                title_lone_category=True,
                click_topics=self.clickable_topics,
            )

        self.msg_help(output)

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
