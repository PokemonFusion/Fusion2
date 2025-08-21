"""Utilities for battle messaging."""


class MessagingMixin:
	"""Mixin providing basic battle messaging helpers.

	Classes inheriting this mixin are expected to define ``captainA`` and
	optionally ``captainB`` attributes referencing the battling trainers. They
	may also provide ``trainers`` and ``observers`` collections. Messages are
	relayed verbatim without any automatic prefixing.
	"""

	def msg(self, text: str) -> None:
		"""Send ``text`` to all trainers and observers."""
		trainers = getattr(self, "trainers", None)
		if not trainers:
			trainers = [t for t in (getattr(self, "captainA", None), getattr(self, "captainB", None)) if t]
		message = text
		for obj in trainers + list(getattr(self, "observers", set())):
			if hasattr(obj, "msg"):
				obj.msg(message)

	def _msg_to(self, obj, text: str) -> None:
		"""Send ``text`` to ``obj``."""
		if hasattr(obj, "msg"):
			obj.msg(text)
