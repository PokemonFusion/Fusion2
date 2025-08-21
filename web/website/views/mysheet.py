from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from pokemon.models.core import OwnedPokemon


class MySheetView(LoginRequiredMixin, TemplateView):
	"""Display characters and their Pokémon for the logged in account."""

	template_name = "website/character_sheet.html"
	page_title = "My Character Sheet"

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		account = self.request.user
		char_entries = []
		try:
			characters = account.characters
		except Exception:
			characters = []
		for char in characters:
			trainer = getattr(char, "trainer", None)
			mons = []
			if trainer:
				mons = list(OwnedPokemon.objects.filter(trainer=trainer))
			char_entries.append(
				{
					"character": char,
					"trainer": trainer,
					"pokemon": mons,
				}
			)
		context["characters"] = char_entries
		context["page_title"] = self.page_title
		return context
