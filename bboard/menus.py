from __future__ import annotations

from evennia.utils.evmenu import EvMenu
from evennia.utils.eveditor import EvEditor


def post_subject(caller, raw_string, **kwargs):
    """Collect subject and launch editor for body."""
    board = kwargs["board"]
    subject = raw_string.strip()
    if not subject:
        return "Enter post subject:", {"goto": "post_subject"}

    def _save(caller, buffer):
        board.post(subject, buffer.strip(), caller)
        caller.msg("|gPost saved.|n")

    def _quit(caller):
        caller.msg("|rPost aborted.|n")

    EvEditor(caller, loadfunc=None, savefunc=_save, quitfunc=_quit, key=subject)
    return None


def edit_body(caller, raw_string, **kwargs):
    """Open editor to edit a post body."""
    board = kwargs["board"]
    index = kwargs["index"]
    post = kwargs["post"]

    def _load(caller):
        return post["body"]

    def _save(caller, buffer):
        board.edit_post(index, buffer.strip())
        caller.msg("|gPost updated.|n")

    def _quit(caller):
        caller.msg("|rEdit aborted.|n")

    EvEditor(caller, loadfunc=_load, savefunc=_save, quitfunc=_quit, key=post["subject"])
    return None
