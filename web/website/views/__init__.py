from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from pokemon.models.core import OwnedPokemon


@login_required
def character_sheet(request):
	"""Display the logged-in user's character sheet.

	The view gathers all Pokémon owned by the trainer linked to the logged-in
	user, prefetching the active slots for efficient lookup. The data is passed
	to the character sheet template as a list with a single entry containing the
	character, its trainer and the related Pokémon.
	"""
	trainer = getattr(request.user, "trainer", None)
	mons = []
	if trainer:
		mons = list(OwnedPokemon.objects.filter(trainer=trainer).prefetch_related("active_slots"))

	context = {
		"characters": [
			{
				"character": request.user,
				"trainer": trainer,
				"pokemon": mons,
			}
		]
	}
	return render(request, "website/character_sheet.html", context)
