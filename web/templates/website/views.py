from django.shortcuts import render

from pokemon.models.core import OwnedPokemon


def character_sheet(request):
	# Assuming `request.user` is linked to Evennia's Account/Character
	character = request.user
	trainer = getattr(character, "trainer", None)

	mons = []
	if trainer:
		qs = (
			OwnedPokemon.objects.filter(trainer=trainer)
			.prefetch_related("active_slots")  # for party slot lookup
			.order_by("species")
		)
		mons = list(qs)

	context = {
		"characters": [
			{
				"character": character,
				"trainer": trainer,
				"pokemon": mons,
			}
		]
	}
	return render(request, "website/character_sheet.html", context)
