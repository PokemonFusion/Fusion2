"""Extensions to :class:`evennia.utils.evmenu.EvMenu`."""

from typing import Any, Callable, Dict, List, Tuple, Union

from evennia.utils.ansi import strip_ansi  # for width calc of ANSI-colored lines
from evennia.utils.evmenu import EvMenu

# Generic invalid-input feedback shared across menus
INVALID_INPUT_MSG = "|rInvalid input.|n Try again. Type |wh|n for help."

# Example usage::
#
#     from utils.enhanced_evmenu import EnhancedEvMenu
#
#     menu = EnhancedEvMenu(
#         caller, menudata, startnode="node_start",
#         on_abort=None,                     # callback when the user aborts
#         invalid_message=INVALID_INPUT_MSG,
#         auto_repeat_invalid=True,          # redisplay node after invalid choice
#         brief_invalid=True,                # show brief invalid message
#         numbered_options=True,             # prefix options with numbers
#         menu_title="Pokémon Menu",         # title text
#         use_pokemon_style=True,            # enable Pokémon-style formatting
#         show_border=True,                  # draw border around node text
#         show_title=True,                   # show title in border/top line
#         show_options=True,                 # render option list
#         show_footer=True,                  # render footer prompt and hints
#         footer_prompt="Number",            # prompt text inside footer
#         border_color="|y",                 # border color (pipe-ANSI)
#         title_text_color="|w",             # title text color
#         option_number_color="|c",          # option number color
#         option_desc_color="|w",            # option description color
#         prompt_color="|g",                 # color of [Enter Number]
#         hint_color="|w",                   # color of 'q'/'h' hints
#         start_kwargs=None,                 # kwargs forwarded to start node
#         **menu_kwargs,                     # additional EvMenu kwargs
#     )


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
      - optional Pokémon-style borders, title, options and footer
      - per-menu color customization
    """

    # keys that always abort
    abort_keys = {"q", "quit", "exit", "abort", ".abort", "cancel"}

    # use a custom border character
    node_border_char = "~"

    def __init__(
        self,
        *args,
        on_abort=None,
        invalid_message=INVALID_INPUT_MSG,
        auto_repeat_invalid=True,
        brief_invalid=True,
        numbered_options=True,
        menu_title="Pokémon Menu",
        use_pokemon_style=True,
        show_border=True,
        show_title=True,
        show_options=True,
        show_footer=True,
        footer_prompt="Number",
        border_color="|y",
        title_text_color="|w",
        option_number_color="|c",
        option_desc_color="|w",
        prompt_color="|g",
        hint_color="|w",
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
        self.show_border = bool(show_border)
        self.show_title = bool(show_title)
        self.show_options = bool(show_options)
        self.show_footer = bool(show_footer)
        self.footer_prompt = footer_prompt
        self.border_color = border_color
        self.title_text_color = title_text_color
        self.option_number_color = option_number_color
        self.option_desc_color = option_desc_color
        self.prompt_color = prompt_color
        self.hint_color = hint_color

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

        if (not getattr(self, "options", None) or low not in self.options) and getattr(self, "default", None):
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
        if not getattr(self, "show_footer", True):
            return
        prompt = self.footer_prompt
        if self.use_pokemon_style:
            tail = []
            if self.auto_quit:
                tail.append(f"{self.hint_color}'q' to quit|n")
            if self.auto_help:
                tail.append(f"{self.hint_color}'h' for help|n")
            extra = f" | {' | '.join(tail)}" if tail else ""
            bc, pc = self.border_color, self.prompt_color
            self.msg(f"{bc}==|n {pc}[Enter {prompt}]|n{extra}")
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
        """
        Format the node text. In Pokémon style, draw a single, width-aware box
        with a centered title and proper side walls. Otherwise, use the base formatter.
        """
        text = super().nodetext_formatter(nodetext)
        if not strip_ansi(text or "").strip():
            return ""
        if not self.use_pokemon_style:
            return text

        if not self.show_border:
            if self.show_title and self.menu_title:
                bc, tc = self.border_color, self.title_text_color
                title = f"{bc}==[ {tc}{self.menu_title}{bc} ]==|n"
                return f"{title}\n{text}"
            return text

        def vlen(s: str) -> int:
            return len(strip_ansi(s or ""))

        def pad_visible(s: str, width: int) -> str:
            pad = max(0, width - vlen(s))
            return s + " " * pad

        lines = (text or "").splitlines() or [""]
        inner_w = max(1, max(vlen(ln) for ln in lines))
        title_seg = ""
        if self.show_title and self.menu_title:
            title_seg = f"[ {self.title_text_color}{self.menu_title}{self.border_color} ]"
        title_w = vlen(title_seg) if title_seg else 0
        inner_w = max(inner_w, title_w)

        left_fill = (inner_w - title_w) // 2 if title_seg else 0
        right_fill = (inner_w - title_w - left_fill) if title_seg else 0
        bc = self.border_color
        top = f"{bc}╔{'═' * left_fill}{title_seg}{'═' * right_fill}╗|n" if title_seg else f"{bc}╔{'═' * inner_w}╗|n"
        middle = [f"{bc}║|n{pad_visible(ln, inner_w)}{bc}║|n" for ln in lines]
        bottom = f"{bc}╚{'═' * inner_w}╝|n"
        return "\n".join([top] + middle + [bottom])

    def options_formatter(self, optionlist):
        """
        When numbered_options is True, show a single number column and the description.
        Avoid duplicating the selection key (which is usually the same number).
        """
        if not self.numbered_options:
            return super().options_formatter(optionlist)

        # Non Pokémon style: compact "1. Desc" lines
        if not self.use_pokemon_style:
            return "\n".join(f"{idx}. {desc}" if desc else f"{idx}." for idx, (_key, desc) in enumerate(optionlist, 1))

        # Pokémon style: colored number + description
        lines = []
        for idx, (_key, desc) in enumerate(optionlist, 1):
            prefix = f"{self.option_number_color}{idx}.|n"
            lines.append(f"{prefix} {self.option_desc_color}{desc}|n" if desc else prefix)
        return "\n".join(lines)

    def node_formatter(self, nodetext, optionstext):
        """
        Compose the final node display.
        We deliberately do NOT call super().node_formatter to avoid the extra
        outer gray border; we render only our Pokémon box + options + footer.
        """
        # If both are empty, we are effectively done — print nothing.
        if not nodetext and not optionstext:
            return ""

        parts = [nodetext] if nodetext else []
        if optionstext and self.show_options:
            parts.append(optionstext)
        result = "\n\n".join(p for p in parts if p)
        # Append footer only when we are awaiting input (i.e., when there ARE options).
        # This hides the footer for terminal/confirmation nodes that return (text, None).
        awaiting_input = bool(optionstext)
        if result and awaiting_input and getattr(self, "show_footer", True):
            prompt = self.footer_prompt
            if self.use_pokemon_style:
                tail = []
                if self.auto_quit:
                    tail.append(f"{self.hint_color}'q' to quit|n")
                if self.auto_help:
                    tail.append(f"{self.hint_color}'h' for help|n")
                hints = (" | " + " | ".join(tail)) if tail else ""
                result += (
                    f"\n\n{self.border_color}== {self.prompt_color}[Enter {prompt}]|n{hints}{self.border_color} ==|n"
                )
            else:
                tail = []
                if self.auto_quit:
                    tail.append("'q' to quit")
                if self.auto_help:
                    tail.append("'h' for help")
                hints = ("; " + " · ".join(tail)) if tail else ""
                result += f"\n\n[Type {prompt.lower()} or command{hints}]."
        return result
