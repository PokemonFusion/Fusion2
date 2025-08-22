from django.urls import path

from . import views

urlpatterns = [
	path("character-sheet/", views.character_sheet, name="character_sheet"),
]
