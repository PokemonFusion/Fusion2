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
        numbered_options=True,
        menu_title="Pokémon Menu",
        use_pokemon_style=True,
        show_footer=True,
        footer_prompt="Number",
        kwargs=None,
        **evkwargs,
    ):
        self.on_abort = on_abort
        self.invalid_message = invalid_message or _HELP_NO_OPTION_MATCH
        self.auto_repeat_invalid = auto_repeat_invalid
        self.numbered_options = numbered_options
        self.menu_title = menu_title
        self.use_pokemon_style = use_pokemon_style
        self.show_footer = show_footer
        self.footer_prompt = footer_prompt

        startnode_input = evkwargs.pop("startnode_input", "")
        if kwargs:
            if isinstance(startnode_input, (tuple, list)) and len(startnode_input) > 1:
                raw, extra = startnode_input[:2]
                if not isinstance(extra, dict):
                    extra = {}
                extra.update(kwargs)
                startnode_input = (raw, extra)
            else:
                startnode_input = (startnode_input, kwargs)

        super().__init__(*args, startnode_input=startnode_input, **evkwargs)

    def parse_input(self, raw_string):
        """Custom input parsing supporting the ``_repeat`` target."""
        cmd = strip_ansi(raw_string.strip())
        low = cmd.lower()

        if not low:
            if self.auto_repeat_invalid:
                # re-run the current node with a blank entry so any
                # raw-string dependent logic resets cleanly
                self.goto(None, "")
            return

        # abort keys always end the menu
        if low in self.abort_keys:
            self.msg("|rMenu aborted.|n")
            self.at_abort()
            return self.close_menu()

        # allow per-node help by "help <topic>"
        if low.startswith("help ") and isinstance(self.helptext, dict):
            topic = low.split(" ", 1)[1]
            if topic in self.helptext:
                return self.display_tooltip(topic)
            self.msg(f"|rNo help for '{topic}'.|n")
            return

        # collect option definitions for later reference. If not provided
        # explicitly (used only in tests), fall back to the menu's current
        # options so normal input works.
        option_defs = getattr(self, "test_options", None)
        if option_defs is None:
            option_defs = [
                {"key": key, "goto": goto}
                for key, goto in (self.options or {}).items()
            ]
            if self.default:
                option_defs.append({"key": "_default", "goto": self.default})
        else:
            option_defs = (
                option_defs if isinstance(option_defs, (list, tuple)) else [option_defs]
            )

        match_opt = None
        default_opt = None
        for opt in option_defs:
            keys = make_iter(opt.get("key"))
            if "_default" in keys and default_opt is None:
                default_opt = opt
            if any(low == str(k).lower() for k in keys):
                match_opt = opt
                break

        def _run_exec(opt):
            exec_fn = opt.get("exec")
            if callable(exec_fn):
                exec_fn(self.caller)

        # explicit match
        if match_opt:
            _run_exec(match_opt)
            if match_opt.get("goto") == "_repeat":
                # re-run same node without carrying over old input
                self.goto(None, "")
                return
            try:
                super().parse_input(raw_string)
            except EvMenuError:
                pass
            return

        # built-in commands
        if self.auto_look and low in ("look", "l"):
            self.display_nodetext()
            return
        if self.auto_help and isinstance(self.helptext, dict) and low in self.helptext:
            self.display_tooltip(low)
            return
        if self.auto_help and low in ("help", "h"):
            self.display_helptext()
            return
        if self.auto_quit and low in ("quit", "q", "exit"):
            self.close_menu()
            return
        if self.debug_mode and low.startswith("menudebug"):
            self.print_debug_info(low[9:].strip())
            return

        # default option
        if default_opt:
            _run_exec(default_opt)
            goto = default_opt.get("goto")
            if goto == "_repeat":
                # repeat current node with cleared input
                if self.auto_repeat_invalid:
                    self.goto(None, "")
                else:
                    self.goto(None, "")
                return
            try:
                super().parse_input(raw_string)
            except EvMenuError:
                pass
            return

        # completely invalid
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
        if not self.use_pokemon_style:
            return text
        return (
            f"|y╔═══════════[ |w{self.menu_title}|n|y ]═══════════╗|n\n"
            f"{text}\n"
            f"|y╚══════════════════════════════════════╝|n"
        )

    def options_formatter(self, optionlist):
        if not self.numbered_options:
            return super().options_formatter(optionlist)

        if not self.use_pokemon_style:
            return "\n".join(
                f"{idx}. {key}: {desc}" if desc else f"{idx}. {key}"
                for idx, (key, desc) in enumerate(optionlist, 1)
            )

        lines = []
        for idx, (key, desc) in enumerate(optionlist, 1):
            prefix = f"|c{idx}.|n |g{key}|n"
            lines.append(f"{prefix}: |w{desc}|n" if desc else prefix)
        return "\n".join(lines)

    def node_formatter(self, nodetext, optionstext):
        result = super().node_formatter(nodetext, optionstext)
        if self.show_footer:
            prompt = self.footer_prompt
            if self.use_pokemon_style:
                result += (
                    f"\n\n|y== |g[Enter {prompt}] |w| 'q' to quit | 'h' for help|y ==|n"
                )
            else:
                result += f"\n\n[Type {prompt.lower()} or command. 'q' to quit.]"
        return result
