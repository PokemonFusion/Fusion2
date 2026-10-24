"""Private read-only Player Hub over canonical character ownership and custody."""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from utils.character_reads import canonical_roster, owned_characters


def build_player_hub_entries(account, characters=None) -> list[dict]:
	"""Intersect requested characters with fresh saved account authority."""
	owned = owned_characters(account)
	allowed = {character.pk for character in owned}
	characters = owned if characters is None else [character for character in characters if character.pk in allowed]
	entries = []
	for character in characters:
		snapshot = canonical_roster(character)
		trainer, pokemon = snapshot['trainer'], snapshot['pokemon']
		entries.append({**snapshot, 'character': character, 'character_id': character.pk,
			'inventory': list(trainer.list_inventory()) if trainer else [],
			'badges': list(trainer.badges.order_by('region', 'name')) if trainer else [],
			'seen_count': trainer.seen_pokemon.count() if trainer else 0,
			'caught_count': len({mon.species for mon in pokemon if mon.species}),
			'total_pokemon': len(pokemon)})
	return entries


class MySheetView(LoginRequiredMixin, TemplateView):
	"""Display only the logged-in account's existing data without grants/repairs."""

	template_name = 'website/character_sheet.html'
	page_title = 'Player Hub'

	def get_context_data(self, **kwargs):
		"""Build fresh current-owner data on every request."""
		context = super().get_context_data(**kwargs)
		context['characters'] = build_player_hub_entries(self.request.user)
		context['page_title'] = self.page_title
		return context
