from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .mysheet import build_player_hub_entries


@login_required
def character_sheet(request):
	"""Display the legacy character sheet route with Player Hub data."""

	context = {
		"characters": build_player_hub_entries(request.user),
		"page_title": "Player Hub",
	}
	return render(request, "website/character_sheet.html", context)
