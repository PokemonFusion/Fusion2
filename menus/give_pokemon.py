from utils.dex_suggestions import (
	is_known_species,
	is_species_not_found_error,
	species_not_found_message,
)


def node_start(caller, raw_input=None, **kwargs):
	"""Ask for Pokemon species."""
	target = kwargs.get("target")
	if not target:
		caller.msg("No target specified.")
		return None, None
	storage = target.storage
	if hasattr(storage, "active_pokemon_count"):
		active_count = storage.active_pokemon_count()
	else:
		active = getattr(storage, "active_pokemon", None)
		if hasattr(active, "count"):
			active_count = active.count()
		elif hasattr(active, "all"):
			active_count = len(list(active.all()))
		else:
			active_count = len(list(active or []))
	if active_count >= 6:
		caller.msg(f"{target.key}'s party is full.")
		return None, None
	menu = getattr(caller.ndb, "_evmenu", None)
	if menu:
		menu.footer_prompt = "Name"
	if not raw_input:
		return (
			f"Enter Pokemon species to give {target.key}:",
			[
				{
					"key": "_default",
					"desc": "Enter species name",
					"goto": ("node_start", {"target": target}),
				}
			],
		)
	name = raw_input.strip()
	if not is_known_species(name):
		caller.msg(f"{species_not_found_message(name)} Try again.")
		return node_start(caller, target=target)

	caller.ndb.givepoke = {"species": name}
	return node_level(caller, target=target)


def node_level(caller, raw_input=None, **kwargs):
	"""Ask for the level and create the Pokemon."""
	target = kwargs.get("target")
	if not target:
		caller.msg("No target specified.")
		return None, None
	menu = getattr(caller.ndb, "_evmenu", None)
	if menu:
		menu.footer_prompt = "Number"
	if not raw_input:
		return (
			"Enter level:",
			[
				{
					"key": "_default",
					"desc": "Enter level number",
					"goto": ("node_level", {"target": target}),
				}
			],
		)
	try:
		level = int(raw_input.strip())
	except ValueError:
		caller.msg("Level must be a number.")
		return node_level(caller, target=target)
	if level < 1:
		level = 1
	species = caller.ndb.givepoke.get("species")
	try:
		from utils.pokemon_utils import grant_generated_pokemon

		pokemon = grant_generated_pokemon(target, species, level, caller=caller)
	except Exception as err:
		if is_species_not_found_error(err):
			caller.msg(species_not_found_message(species))
			return node_start(caller, target=target)
		from pokemon.data.generation import generate_pokemon
		from pokemon.helpers.pokemon_helpers import create_owned_pokemon

		try:
			instance = generate_pokemon(species, level=level)
		except ValueError as gen_err:
			if is_species_not_found_error(gen_err):
				caller.msg(species_not_found_message(species))
			else:
				caller.msg(str(gen_err))
			return node_start(caller, target=target)
		pokemon = create_owned_pokemon(
			instance.species.name,
			target.trainer,
			instance.level,
			gender=instance.gender,
			nature=instance.nature,
			ability=instance.ability,
			ivs=[
				instance.ivs.hp,
				instance.ivs.attack,
				instance.ivs.defense,
				instance.ivs.special_attack,
				instance.ivs.special_defense,
				instance.ivs.speed,
			],
			evs=[0, 0, 0, 0, 0, 0],
		)
		target.storage.add_active_pokemon(pokemon)
		caller.msg(f"Gave {pokemon.species} (Lv {pokemon.computed_level}) to {target.key}.")
		if target != caller:
			target.msg(f"You received {pokemon.species} (Lv {pokemon.computed_level}) from {caller.key}.")
	del caller.ndb.givepoke
	return None, None
