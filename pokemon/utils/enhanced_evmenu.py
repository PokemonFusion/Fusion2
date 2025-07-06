from evennia.utils.evmenu import EvMenu
from evennia.utils.ansi import strip_ansi

class EnhancedEvMenu(EvMenu):
    """
    Extends EvMenu with:
      - built-in abort on q/quit/exit
      - automatic re-display of the same node on invalid choices
      - support for a `_repeat` goto to re-show the current node after exec
      - hooks for custom logging or UI enhancements
    """

    # keys that always abort
    abort_keys = {"q", "quit", "exit"}

    def parse_input(self, raw_string):
        """
        Override the input parser to:
         1) catch abort keys immediately,
         2) catch options with goto == '_repeat' to exec and re-display,
         3) on other invalid input, show our invalid_msg and re-show the node.
        """
        cmd = strip_ansi(raw_string.strip()).lower()

        # 1) Abort handling
        if cmd in self.abort_keys:
            self.msg("|rMenu aborted.|n")
            self.at_abort()
            return self.close_menu()

        # 2) Look for a matching option manually
        match_opt = None
        for opt in getattr(self, 'options', []):
            key = opt.get('key')
            keys = key if isinstance(key, (tuple, list)) else (key,)
            if any(cmd == k.lower() for k in keys if isinstance(k, str)):
                match_opt = opt
                break

        # 3) Handle _repeat goto specially
        if match_opt and match_opt.get('goto') == '_repeat':
            # Execute any 'exec' callback
            exec_fn = match_opt.get('exec')
            if callable(exec_fn):
                exec_fn(self.caller)
            # Re-display the same node text
            self.display_nodetext()
            return

        # 4) Delegate to parent for normal processing
        super().parse_input(raw_string)

        # 5) If nothing changed (and not a help/look), treat as invalid
        if self.nodename and cmd not in ("help", "h", "look", "l"):
            # Check if parent matched any real goto
            # EvMenu moves on valid goto/exec; if still here, invalid
            self.invalid_msg()
            self.display_nodetext()

    def invalid_msg(self):
        """
        Customize the message shown on invalid input.
        Override in subclasses if desired.
        """
        self.msg("Invalid choice, please try again.")

    def at_abort(self):
        """
        Hook that runs when the user aborts.
        You could log this, or clean up state, etc.
        """
        pass
