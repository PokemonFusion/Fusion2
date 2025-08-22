"""Enumerations used by Pokémon models."""

from django.db import models

__all__ = ["Gender", "Nature"]


class Gender(models.TextChoices):
	"""Allowed Pokémon genders."""

	MALE = "M", "Male"
	FEMALE = "F", "Female"
	NONE = "N", "None"


class Nature(models.TextChoices):
	"""Available Pokémon natures."""

	HARDY = "Hardy", "Hardy"
	LONELY = "Lonely", "Lonely"
	BRAVE = "Brave", "Brave"
	ADAMANT = "Adamant", "Adamant"
	NAUGHTY = "Naughty", "Naughty"
	BOLD = "Bold", "Bold"
	DOCILE = "Docile", "Docile"
	RELAXED = "Relaxed", "Relaxed"
	IMPISH = "Impish", "Impish"
	LAX = "Lax", "Lax"
	TIMID = "Timid", "Timid"
	HASTY = "Hasty", "Hasty"
	SERIOUS = "Serious", "Serious"
	JOLLY = "Jolly", "Jolly"
	NAIVE = "Naive", "Naive"
	MODEST = "Modest", "Modest"
	MILD = "Mild", "Mild"
	QUIET = "Quiet", "Quiet"
	BASHFUL = "Bashful", "Bashful"
	RASH = "Rash", "Rash"
	CALM = "Calm", "Calm"
	GENTLE = "Gentle", "Gentle"
	SASSY = "Sassy", "Sassy"
	CAREFUL = "Careful", "Careful"
	QUIRKY = "Quirky", "Quirky"
