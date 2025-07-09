from __future__ import annotations
from typing import Dict

from evennia import Command
from pokemon.utils.enhanced_evmenu import EnhancedEvMenu

from pokemon.dex import POKEDEX
from pokemon.generation import generate_pokemon
from pokemon.models import OwnedPokemon, StorageBox
from pokemon.starters import get_starter_names, STARTER_LOOKUP
from commands.command import heal_pokemon

# ────── BUILD UNIVERSAL POKEMON LOOKUP ─────────────────────────────────────────

# Map lowercased raw key → key, and lowercased display name → key
POKEMON_KEY_LOOKUP: Dict[str, str] = {}
for key, mon in POKEDEX.items():
	POKEMON_KEY_LOOKUP[key.lower()] = key
	raw = mon.raw or {}
	display_name = raw.get("name", mon.name)
	POKEMON_KEY_LOOKUP[display_name.lower()] = key

# ────── CONSTANTS ──────────────────────────────────────────────────────────────

TYPES = [
	"Bug",
	"Dark",
	"Dragon",
	"Electric",
	"Fighting",
	"Fire",
	"Flying",
	"Ghost",
	"Grass",
	"Ground",
	"Ice",
	"Normal",
	"Poison",
	"Psychic",
	"Rock",
	"Steel",
	"Water",
]
NATURES = list(generate_pokemon.__globals__["NATURES"].keys())

# Starter‐specific lookup (name/key → key)
STARTER_NAMES = set(STARTER_LOOKUP.keys())

ABORT_INPUTS = {"abort", ".abort", "q", "quit", "exit"}
ABORT_OPTION = {"key": ("q", "quit", "exit"), "desc": "Abort", "goto": "node_abort"}


# ────── HELPERS ────────────────────────────────────────────────────────────────


def _invalid(caller):
	"""Notify caller of invalid input."""
	caller.msg("Invalid entry.\nTry again.")


def format_columns(items, columns=4, indent=2):
	"""Return items formatted into evenly spaced columns."""
	lines = []
	for i in range(0, len(items), columns):
		row = items[i : i + columns]
		lines.append(" " * indent + "\t".join(str(it) for it in row))
	return "\n".join(lines)


def _ensure_storage(char):
	"""Ensure the character has 8 storage boxes."""
	storage = char.storage
	if not storage.boxes.exists():
		for i in range(1, 9):
			StorageBox.objects.create(storage=storage, name=f"Box {i}")
	return storage




def _create_starter(
    char,
    species_key: str,
    ability: str,
    gender: str,
    level: int = 5,
):
    """Instantiate and store a starter Pokémon for the player."""
    try:
        instance = generate_pokemon(species_key, level=level)
    except ValueError:
        char.msg("That species does not exist.")
        return

    chosen_gender = gender or instance.gender


    pokemon = OwnedPokemon.objects.create(
        trainer=char.trainer,
        species=instance.species.name,
        nickname="",
        gender=chosen_gender,
        nature=instance.nature,
        ability=ability or instance.ability,
        ivs=[
            instance.ivs.hp,
            instance.ivs.atk,
            instance.ivs.def_,
            instance.ivs.spa,
            instance.ivs.spd,
            instance.ivs.spe,
        ],
        evs=[0, 0, 0, 0, 0, 0],
    )

    pokemon.set_level(level)

    heal_pokemon(pokemon)

    storage = _ensure_storage(char)
    storage.active_pokemon.add(pokemon)

    return pokemon


# ────── COMMAND CLASS ─────────────────────────────────────────────────────────


class CmdChargen(Command):
	"""Interactive character creation."""

	key = "chargen"
	locks = "cmd:all()"

	def func(self):
		if self.caller.db.validated:
			self.caller.msg("You are already validated and cannot run chargen again.")
			return
		EnhancedEvMenu(
			self.caller,
			__name__,
			startnode="start",
			cmd_on_exit=None,
			on_abort=node_abort,
			invalid_message="Invalid entry.\nTry again.",
			numbered_options=False,
		)


# ────── MENU NODES ─────────────────────────────────────────────────────────────


def start(caller, raw_string):
	text = (
		"Welcome to Pokemon Fusion!\n"
		"A: Play a human trainer with a starter Pokémon.\n"
		"B: Play a Fusion without a starter.\n"
		"______________________________________________________________________________"
	)
	options = (
		{"key": ("A", "a"), "desc": "Human trainer", "goto": ("human_gender", {})},
		{
			"key": ("B", "b"),
			"desc": "Fusion (no starter)",
			"goto": ("fusion_gender", {}),
		},
		ABORT_OPTION,
		{"key": "_default", "goto": "_repeat", "exec": _invalid},
	)
	return text, options


def human_gender(caller, raw_string, **kwargs):
	caller.ndb.chargen = {"type": "human"}
	text = "Choose your gender: (M)ale or (F)emale"
	options = (
		{"key": ("M", "m"), "desc": "Male", "goto": ("human_type", {"gender": "Male"})},
		{
			"key": ("F", "f"),
			"desc": "Female",
			"goto": ("human_type", {"gender": "Female"}),
		},
		ABORT_OPTION,
		{"key": "_default", "goto": "_repeat", "exec": _invalid},
	)
	return text, options


def fusion_gender(caller, raw_string, **kwargs):
	caller.ndb.chargen = {"type": "fusion"}
	text = "Choose your gender: (M)ale or (F)emale"
	options = (
		{
			"key": ("M", "m"),
			"desc": "Male",
			"goto": ("fusion_species", {"gender": "Male"}),
		},
		{
			"key": ("F", "f"),
			"desc": "Female",
			"goto": ("fusion_species", {"gender": "Female"}),
		},
		ABORT_OPTION,
		{"key": "_default", "goto": "_repeat", "exec": _invalid},
	)
	return text, options


def human_type(caller, raw_string, **kwargs):
	# stash gender so we can re-enter with the same kwarg
	gender = kwargs["gender"]
	caller.ndb.chargen["gender"] = gender

	text = "Choose your favored Pokémon type:\n" + format_columns(TYPES) + "\n"

	# build all the real type-choices
	opts = [
		{"key": t.lower(), "desc": t, "goto": ("starter_species", {"type": t})}
		for t in TYPES
	]
	# abort stays the same
	opts.append(ABORT_OPTION)
	# on anything else, show our invalid-entry msg *and* go back into human_type
	opts.append({
		"key": "_default",
		"exec": _invalid,
		"goto": ("human_type", {"gender": gender}),
	})

	return text, tuple(opts)



def fusion_species(caller, raw_string, **kwargs):
	caller.ndb.chargen["gender"] = kwargs.get("gender")
	text = "Enter the species for your fusion:"
	options = (
		{"key": "_default", "goto": "fusion_ability"},
		ABORT_OPTION,
	)
	return text, options


def fusion_ability(caller, raw_string, **kwargs):
	"""Accept either raw key or display name here."""
	entry = raw_string.strip()
	if entry.lower() in ABORT_INPUTS:
		return node_abort(caller)

	# Lookup via our universal mapping
	key = POKEMON_KEY_LOOKUP.get(entry.lower())
	if not key:
		caller.msg("Unknown species.\nTry again.")
		return fusion_species(caller, "")

	mon = POKEDEX[key]
	caller.ndb.chargen.update({
		"species_key": key,
		"species": mon.raw.get("name", mon.name),
	})

	# Gather unique abilities
	raw_abs = mon.raw.get("abilities", {}) or {}
	ab_list = []
	for a in raw_abs.values():
		name = a.name if hasattr(a, "name") else a
		if name not in ab_list:
			ab_list.append(name)

	# Skip to confirm if only one
	if len(ab_list) <= 1:
		caller.ndb.chargen["ability"] = ab_list[0] if ab_list else ""
		return fusion_confirm(caller, "")

	text = "Choose your fusion's ability:\n" + format_columns(ab_list) + "\n"
	options = tuple(
		{"key": ab.lower(), "desc": ab, "goto": ("fusion_confirm", {"ability": ab})}
		for ab in ab_list
	)
	+ (
		ABORT_OPTION,
		{"key": "_default", "goto": "_repeat", "exec": _invalid},
	)
	return text, options


def starter_species(caller, raw_string, **kwargs):
	caller.ndb.chargen["favored_type"] = kwargs.get("type")

	text = (
		"Enter the species for your starter Pokémon\n"
		"(use 'starterlist' or 'pokemonlist' to view valid options):"
	)
	options = [
		{
			"key": ("starterlist", "starters", "pokemonlist"),
			"exec": lambda cb: cb.msg("Starter Pokémon:\n" + ", ".join(get_starter_names())),
			"goto": ("starter_species", {"type": caller.ndb.chargen["favored_type"]}),
		},
		ABORT_OPTION,
		{
			"key": "_default",
			"goto": "starter_ability",
		},
	]
	return text, tuple(options)



def starter_ability(caller, raw_string, **kwargs):
	entry = raw_string.strip().lower()

	if entry in ABORT_INPUTS:
		return node_abort(caller)

	if entry in ("starterlist", "starters", "pokemonlist"):
		caller.msg("Starter Pokémon:\n" + ", ".join(get_starter_names()))
		return starter_species(caller, "", type=caller.ndb.chargen.get("favored_type"))

	key = STARTER_LOOKUP.get(entry)
	if not key:
		caller.msg("Invalid starter species.\nUse 'starterlist' or 'pokemonlist'.")
		return starter_species(caller, "", type=caller.ndb.chargen.get("favored_type"))

	# Valid species
	caller.ndb.chargen["species_key"] = key
	caller.ndb.chargen["species"] = POKEDEX[key].raw.get("name", key)

	mon = POKEDEX[key]
	abilities = mon.raw.get("abilities", {}) or {}

	numeric_keys = sorted(k for k in abilities if k.isdigit())

	lines = ["Choose one of the following abilities:"]
	for k in numeric_keys:
		lines.append(f"  {int(k)+1}: {abilities[k]}")
	if "H" in abilities:
		lines.append(f"  H: {abilities['H']}")
	text = "\n".join(lines)

	opts = []
	for k in numeric_keys:
		opts.append({
			"key": str(int(k)+1),
   			"desc": f"{abilities[k]}",  # This shows the ability name next to the number
			"exec": lambda cb, k=k: cb.ndb.chargen.__setitem__("ability", abilities[k]),
			"goto": "starter_gender",
		})
	if "H" in abilities:
		opts.append({
			"key": "H",
			"desc": f"{abilities['H']}",  # Add description for H as well
			"exec": lambda cb: cb.ndb.chargen.__setitem__("ability", abilities["H"]),
			"goto": "starter_gender",
		})

	opts.append(ABORT_OPTION)
	opts.append({
		"key": "_default",
		"exec": lambda cb: cb.msg("Invalid choice. Please pick 1, 2… or H."),
		"goto": "_repeat",
	})

	return text, tuple(opts)



def starter_gender(caller, raw_string, **kwargs):
	if kwargs.get("ability"):
		caller.ndb.chargen["ability"] = kwargs["ability"]

	key = caller.ndb.chargen.get("species_key")
	data = POKEDEX[key]
	ratio = getattr(data, "gender_ratio", None)
	gender = getattr(data, "gender", None)

	text = "Choose your starter's gender:"
	options: list[dict] = []

	if gender in ("M", "F", "N"):
		desc = {"M": "Male", "F": "Female", "N": "Genderless"}[gender]
		options.append(
			{
				"key": (gender, gender.lower()),
				"desc": desc,
				"goto": ("starter_confirm", {"gender": gender}),
			}
		)
	else:
		m, f = (ratio.M, ratio.F) if ratio else (0.5, 0.5)
		if m > 0:
			options.append(
				{
					"key": ("M", "m"),
					"desc": "Male",
					"goto": ("starter_confirm", {"gender": "M"}),
				}
			)
		if f > 0:
			options.append(
				{
					"key": ("F", "f"),
					"desc": "Female",
					"goto": ("starter_confirm", {"gender": "F"}),
				}
			)
		if m == 0 and f == 0:
			options.append(
				{
					"key": ("N", "n"),
					"desc": "Genderless",
					"goto": ("starter_confirm", {"gender": "N"}),
				}
			)

	options += [
		ABORT_OPTION,
		{"key": "_default", "goto": "_repeat", "exec": _invalid},
	]
	return text, tuple(options)


def starter_confirm(caller, raw_string, **kwargs):
	if kwargs.get("ability"):
		caller.ndb.chargen["ability"] = kwargs["ability"]
	if kwargs.get("gender"):
		caller.ndb.chargen["gender"] = kwargs["gender"]

	species = caller.ndb.chargen["species"]
	low = species.lower()
	if low in ABORT_INPUTS:
		return node_abort(caller)
	if low in ("starterlist", "starters", "pokemonlist"):
		caller.msg("Starter Pokémon:\n" + ", ".join(get_starter_names()))
		return starter_species(caller, "", type=caller.ndb.chargen.get("favored_type"))
	if low not in STARTER_NAMES:
		caller.msg("Invalid starter species.\nUse 'starterlist' or 'pokemonlist'.")
		return starter_species(caller, "", type=caller.ndb.chargen.get("favored_type"))

	text = (
		f"You chose {caller.ndb.chargen['species']} "
		f"({caller.ndb.chargen['gender']}) "
		f"with ability {caller.ndb.chargen['ability']} as your starter.\n"
		"Proceed? (Y/N)"
	)
	options = (
		{"key": ("Y", "y"), "desc": "Yes", "goto": "finish_human"},
		{"key": ("N", "n"), "desc": "No", "goto": "starter_species"},
		ABORT_OPTION,
		{"key": "_default", "goto": "_repeat", "exec": _invalid},
	)
	return text, options


def fusion_confirm(caller, raw_string, **kwargs):
	if kwargs.get("ability"):
		caller.ndb.chargen["ability"] = kwargs["ability"]

	species = caller.ndb.chargen["species"]
	if species.lower() in ABORT_INPUTS:
		return node_abort(caller)

	text = (
		f"You chose to fuse with {species} "
		f"having ability {caller.ndb.chargen['ability']}.\n"
		"Proceed? (Y/N)"
	)
	options = (
		{"key": ("Y", "y"), "desc": "Yes", "goto": "finish_fusion"},
		{"key": ("N", "n"), "desc": "No", "goto": "fusion_species"},
		ABORT_OPTION,
		{"key": "_default", "goto": "_repeat", "exec": _invalid},
	)
	return text, options


def finish_human(caller, raw_string):
	data = caller.ndb.chargen or {}
	key = data.get("species_key")
	if not key:
		caller.msg("Error: No starter selected.")
		return None, None

	pk = _create_starter(
		caller,
		key,
		data.get("ability"),
		data.get("gender"),
	)
	caller.db.gender = data.get("gender")
	caller.db.favored_type = data.get("favored_type")
	caller.msg(f"You received {pk.name} with ability {pk.ability} as your starter!")
	caller.msg("Character generation complete.")
	return None, None


def finish_fusion(caller, raw_string):
	data = caller.ndb.chargen or {}
	caller.db.gender = data.get("gender")
	caller.db.fusion_species = data.get("species")
	caller.db.fusion_ability = data.get("ability")
	caller.msg(
		f"You are now a fusion with {data.get('species')} "
		f"having ability {data.get('ability')}."
	)
	caller.msg("Character generation complete.")
	return None, None


def node_abort(caller, raw_string=None):
	caller.msg("Character generation aborted.")
	return None, None
