from pokemon.dex import POKEDEX
from pokemon.generation import generate_pokemon
from pokemon.models import OwnedPokemon
from commands.command import heal_pokemon


def node_start(caller, raw_input=None, target=None):
    """Ask for Pokemon species."""
    if target.storage.active_pokemon.count() >= 6:
        caller.msg(f"{target.key}'s party is full.")
        return None, None
    if not raw_input:
        return f"Enter Pokemon species to give {target.key}:", [{"key": "_default", "goto": "node_start"}]
    name = raw_input.strip()
    if name.lower() not in POKEDEX and name.title() not in POKEDEX:
        caller.msg("Unknown species. Try again.")
        return "node_start", {}
    caller.ndb.givepoke = {"species": name}
    return "node_level", {}


def node_level(caller, raw_input=None, target=None):
    """Ask for the level and create the Pokemon."""
    if not raw_input:
        return "Enter level:", [{"key": "_default", "goto": "node_level"}]
    try:
        level = int(raw_input.strip())
    except ValueError:
        caller.msg("Level must be a number.")
        return "node_level", {}
    if level < 1:
        level = 1
    species = caller.ndb.givepoke.get("species")
    instance = generate_pokemon(species, level=level)
    pokemon = OwnedPokemon.objects.create(
        trainer=target.trainer,
        species=instance.species.name,
        nickname="",
        gender=instance.gender,
        nature=instance.nature,
        ability=instance.ability,
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
    pokemon.set_level(instance.level)
    heal_pokemon(pokemon)
    target.storage.add_active_pokemon(pokemon)
    caller.msg(
        f"Gave {pokemon.species} (Lv {pokemon.level}) to {target.key}."
    )
    if target != caller:
        target.msg(f"You received {pokemon.species} (Lv {pokemon.level}) from {caller.key}.")
    del caller.ndb.givepoke
    return None, None
