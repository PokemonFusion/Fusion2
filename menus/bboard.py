from __future__ import annotations

"""Menu nodes for bulletin board interactions."""

from evennia.utils.eveditor import EvEditor
from bboard.transactions import BoardError


def post_subject(caller, raw_string, **kwargs):
	"""Collect subject and launch editor for body."""
	board = kwargs["board"]
	subject = raw_string.strip()
	if not subject:
		return "Enter post subject:", {"key": "_default", "goto": ("post_subject", {"board": board})}

	saved = False

	def _save(caller, buffer):
		nonlocal saved
		if saved:
			caller.msg("This post is already saved. Reopen it with +bbedit to make further changes.")
			return False
		try:
			board.post(subject, buffer.strip(), caller)
		except BoardError as error:
			caller.msg(str(error))
			return False
		saved = True
		caller.msg("|gPost saved.|n")
		return True

	def _quit(caller):
		if not saved:
			caller.msg("|rPost aborted.|n")

	EvEditor(caller, loadfunc=None, savefunc=_save, quitfunc=_quit, key=subject)
	return None


def edit_body(caller, raw_string, **kwargs):
	"""Open editor to edit a post body."""
	board = kwargs["board"]
	index = kwargs["index"]
	post = kwargs["post"]
	expected_id = post.get("id")

	def _load(caller):
		return post["body"]

	def _save(caller, buffer):
		try:
			if not board.edit_post(index, buffer.strip(), actor=caller, expected_id=expected_id):
				raise BoardError("This post was removed. Reopen the board list.")
		except BoardError as error:
			caller.msg(str(error))
			return False
		caller.msg("|gPost updated.|n")
		return True

	def _quit(caller):
		caller.msg("|rEdit aborted.|n")

	EvEditor(caller, loadfunc=_load, savefunc=_save, quitfunc=_quit, key=post["subject"])
	return None
