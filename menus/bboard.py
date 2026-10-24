from __future__ import annotations

"""Menu nodes for bulletin board interactions."""

from evennia.utils.eveditor import EvEditor
from bboard.transactions import BoardError


def post_subject(caller, raw_string, **kwargs):
	"""Collect subject and launch editor for body."""
	board = kwargs["board"]
	subject = raw_string.strip()
	if not subject:
		return "Enter post subject:", {"goto": "post_subject"}

	def _save(caller, buffer):
		try:
			board.post(subject, buffer.strip(), caller)
		except BoardError as error:
			caller.msg(str(error))
			return False
		caller.msg("|gPost saved.|n")
		return True

	def _quit(caller):
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
