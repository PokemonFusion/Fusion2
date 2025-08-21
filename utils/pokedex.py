class DexTrackerMixin:
	"""Mixin to track Pokédex progress on a Character."""

	def _get_list(self, attr: str):
		data = getattr(self.db, attr, None)
		if data is None:
			data = []
			setattr(self.db, attr, data)
		return data

	def _add(self, attr: str, name: str):
		lst = self._get_list(attr)
		key = name.lower()
		if key not in lst:
			lst.append(key)
			setattr(self.db, attr, lst)

	@property
	def dex_seen(self):
		return set(self._get_list("dex_seen"))

	@property
	def dex_owned(self):
		return set(self._get_list("dex_owned"))

	@property
	def dex_caught(self):
		return set(self._get_list("dex_caught"))

	def mark_seen(self, name: str) -> None:
		self._add("dex_seen", name)

	def mark_owned(self, name: str) -> None:
		self._add("dex_owned", name)

	def mark_caught(self, name: str) -> None:
		self._add("dex_caught", name)

	def get_dex_symbol(self, name: str) -> str:
		key = name.lower()
		if key in self.dex_caught:
			return "[C]"
		if key in self.dex_owned:
			return "[O]"
		if key in self.dex_seen:
			return "[S]"
		return ""
