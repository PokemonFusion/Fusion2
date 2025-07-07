"""Extensions to :class:`evennia.utils.evmenu.EvMenu`."""

from evennia.utils.evmenu import EvMenu, EvMenuError, _HELP_NO_OPTION_MATCH
from evennia.utils.ansi import strip_ansi
from evennia.utils.utils import make_iter


class EnhancedEvMenu(EvMenu):
    """
    Extends EvMenu with:
      - built-in abort on q/quit/exit
      - automatic re-display of the same node on invalid choices
      - support for a `_repeat` goto to re-show the current node after exec
      - hooks for custom logging or UI enhancements
    """

    # keys that always abort
    abort_keys = {"q", "quit", "exit", "abort", ".abort", "cancel"}

    # use a custom border character
    node_border_char = "~"

    def __init__(
        self,
        *args,
        on_abort=None,
        invalid_message=None,
        auto_repeat_invalid=True,
        **kwargs,
    ):
        self.on_abort = on_abort
        self.invalid_message = invalid_message or _HELP_NO_OPTION_MATCH
        self.auto_repeat_invalid = auto_repeat_invalid
        super().__init__(*args, **kwargs)

    def parse_input(self, raw_string):
        """
        Override the input parser to:
         1) catch abort keys immediately,
         2) catch options with goto == '_repeat' to exec and re-display,
         3) on other invalid input, show our invalid_msg and re-show the node.
        """
        cmd = strip_ansi(raw_string.strip())
        low = cmd.lower()

        # 1) Abort handling
        if low in self.abort_keys:
            self.msg("|rMenu aborted.|n")
            self.at_abort()
            return self.close_menu()

        # 2) help <topic> support
        if low.startswith("help ") and isinstance(self.helptext, dict):
            topic = low.split(" ", 1)[1]
            if topic in self.helptext:
                return self.display_tooltip(topic)
            self.msg(f"|rNo help for '{topic}'.|n")
            return

        # 3) Look for a matching option manually using raw option definitions
        match_opt = None
        options = self.test_options or []
        options = options if isinstance(options, (list, tuple)) else [options]
        for opt in options:
            keys = make_iter(opt.get("key"))
            if any(low == str(k).lower() for k in keys):
                match_opt = opt
                break

        # 4) Run exec callback and handle `_repeat` goto before normal processing
        if match_opt:
            exec_fn = match_opt.get("exec")
            if callable(exec_fn):
                exec_fn(self.caller)
            if match_opt.get("goto") == "_repeat":
                self.display_nodetext()
                return

        # 5) Delegate to parent for normal processing
        try:
            super().parse_input(raw_string)
        except EvMenuError:
            pass

        # 6) If nothing changed (and not a help/look), treat as invalid
        if (
            self.nodename
            and low not in ("help", "h", "look", "l")
            and low not in self.options
        ):
            self.invalid_msg()
            if self.auto_repeat_invalid:
                self.display_nodetext()

    def invalid_msg(self):
        """
        Customize the message shown on invalid input.
        Override in subclasses if desired.
        """
        self.msg(self.invalid_message)

    def at_abort(self):
        """
        Hook that runs when the user aborts.
        You could log this, or clean up state, etc.
        """
        if callable(self.on_abort):
            self.on_abort(self.caller)

    @staticmethod
    def generate_options(
        items,
        key_func=lambda x: str(x),
        desc_func=lambda x: str(x),
        goto_node=None,
        goto_kwargs_func=lambda x: {},
    ):
        """Return a list of option dictionaries from ``items``."""
        opts = []
        for item in items:
            key = key_func(item)
            opts.append(
                {
                    "key": (key,),
                    "desc": desc_func(item),
                    "goto": (goto_node, {**goto_kwargs_func(item)}),
                }
            )
        return opts

    def nodetext_formatter(self, nodetext):
        text = super().nodetext_formatter(nodetext)
        return f"|w== Menu ==|n\n{text}\n"

    def options_formatter(self, optionlist):
        lines = []
        for idx, (key, desc) in enumerate(optionlist, 1):
            lines.append(f"{idx}. {key}: {desc}")
        return "\n".join(lines)
