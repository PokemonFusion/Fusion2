"""Extensions to :class:`evennia.utils.evmenu.EvMenu`."""

from typing import Any, Callable, Dict, List, Tuple, Union

from evennia.utils.evmenu import EvMenu
from evennia.utils.ansi import strip_ansi


NodeReturn = Tuple[str, Union[None, Dict[str, Any], List[Dict[str, Any]]]]


def _ensure_default_option(node_ret: NodeReturn) -> NodeReturn:
    """Ensure free-form nodes always capture input with ``_default``."""

    if not isinstance(node_ret, tuple) or len(node_ret) != 2:
        return node_ret
    text, options = node_ret
    if isinstance(options, dict):
        if "goto" in options and "key" not in options:
            wrapped = {"key": "_default", **options}
            return text, [wrapped]
        return text, [options]
    return node_ret


def free_input_node(func: Callable[..., NodeReturn]) -> Callable[..., NodeReturn]:
    """Decorator adding a ``_default`` option when absent."""

    def wrapper(caller, raw_input=None, **kwargs):
        ret = func(caller, raw_input, **kwargs)
        return _ensure_default_option(ret)

    wrapper.__name__ = getattr(func, "__name__", "free_input_node")
    return wrapper


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
        invalid_message="|rIncorrect input, try again.|n",
        auto_repeat_invalid=True,
        brief_invalid=True,
        numbered_options=True,
        menu_title="Pokémon Menu",
        use_pokemon_style=True,
        show_footer=True,
        footer_prompt="Number",
        start_kwargs=None,
        **menu_kwargs,
    ):
        self.on_abort = on_abort
        self.invalid_message = invalid_message
        self.auto_repeat_invalid = auto_repeat_invalid
        self.brief_invalid = brief_invalid
        self.numbered_options = numbered_options
        self.menu_title = menu_title
        self.use_pokemon_style = use_pokemon_style
        self.show_footer = show_footer
        self.footer_prompt = footer_prompt

        startnode_input = menu_kwargs.pop("startnode_input", "")
        if start_kwargs:
            if isinstance(startnode_input, (tuple, list)) and len(startnode_input) > 1:
                raw, extra = startnode_input[:2]
                if not isinstance(extra, dict):
                    extra = {}
                extra.update(start_kwargs)
                startnode_input = (raw, extra)
            else:
                startnode_input = (startnode_input, start_kwargs)

        super().__init__(*args, startnode_input=startnode_input, **menu_kwargs)

    def parse_input(self, raw_string):
        """Minimal input parsing that only handles the ``_repeat`` sentinel."""

        low = strip_ansi((raw_string or "").strip()).lower()

        if getattr(self, "options", None) and low in self.options:
            goto_node, _ = self.options[low]
            if goto_node == "_repeat":
                self.goto(None, "")
                return

        if (
            (not getattr(self, "options", None) or low not in self.options)
            and getattr(self, "default", None)
        ):
            goto_node, _ = self.default
            if goto_node == "_repeat":
                self.goto(None, "")
                return

        return super().parse_input(raw_string)

    def invalid_msg(self):
        """
        Customize the message shown on invalid input.
        Override in subclasses if desired.
        """
        self.msg(self.invalid_message)

    def _show_footer_hint(self):
        """Show a compact footer hint without repainting the whole node."""
        if not self.show_footer:
            return
        prompt = self.footer_prompt
        if self.use_pokemon_style:
            tail = []
            if self.auto_quit:
                tail.append("|w'q' to quit|n")
            if self.auto_help:
                tail.append("'h' for help")
            extra = f" | {' | '.join(tail)}" if tail else ""
            self.msg(f"|y==|n [Enter {prompt}]{extra}")
        else:
            tail = []
            if self.auto_quit:
                tail.append("'q' to quit")
            if self.auto_help:
                tail.append("'h' for help")
            extra = ("; " + " · ".join(tail)) if tail else ""
            self.msg(f"[Type {prompt.lower()} or command{extra}]")

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
                tail = []
                if self.auto_quit:
                    tail.append("|w'q' to quit|n")
                if self.auto_help:
                    tail.append("'h' for help")
                hints = (" | " + " | ".join(tail)) if tail else ""
                result += f"\n\n|y== |g[Enter {prompt}]|n{hints}|y ==|n"
            else:
                tail = []
                if self.auto_quit:
                    tail.append("'q' to quit")
                if self.auto_help:
                    tail.append("'h' for help")
                hints = ("; " + " · ".join(tail)) if tail else ""
                result += f"\n\n[Type {prompt.lower()} or command{hints}]."
        return result
