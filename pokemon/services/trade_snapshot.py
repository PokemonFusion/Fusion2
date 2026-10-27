"""Immutable player-visible asset snapshots for exact trade consent."""

import hashlib
import json


class PokemonTradeSnapshot:
    """Bind genetic, held, move/PP and progression state to the same owned UUID."""

    @staticmethod
    def capture(pokemon_id):
        """Caller holds storage/Pokemon locks; snapshots grant no ownership authority."""
        from pokemon.hyper_training import HyperTraining
        from pokemon.models.core import OwnedPokemon
        from pokemon.models.moves import ActiveMoveslot, MovePPBoost, Moveset, MovesetSlot, PokemonLearnedMove
        from pokemon.services.ownership import fresh_owned

        row = OwnedPokemon.objects.filter(pk=pokemon_id).values().get()
        slots = list(ActiveMoveslot.objects.filter(pokemon_id=pokemon_id).order_by("slot", "pk").values(
            "id", "slot", "move_id", "move__name", "current_pp"))
        bonuses = list(MovePPBoost.objects.filter(pokemon_id=pokemon_id).order_by("move_id").values())
        state = {"pokemon": row, "active_moves": slots, "pp_boosts": bonuses,
                 "learned": list(PokemonLearnedMove.objects.filter(pokemon_id=pokemon_id).order_by("move_id").values()),
                 "movesets": list(Moveset.objects.filter(pokemon_id=pokemon_id).order_by("index").values()),
                 "moveset_slots": list(MovesetSlot.objects.filter(moveset__pokemon_id=pokemon_id)
                                        .order_by("moveset_id", "slot").values())}
        summary = {key: row.get(key) for key in (
            "species", "level", "gender", "is_egg", "held_item", "current_hp", "status",
            "friendship", "nature", "trained_stat_nature", "ability", "ivs", "evs", "tera_type")}
        summary["shiny"] = row["is_shiny"]
        summary["name"] = row.get("nickname") or row["species"]
        summary["level"] = fresh_owned(pokemon_id).computed_level
        summary["hyper_training"] = [label for stat, label in zip(HyperTraining.stats, HyperTraining.labels)
                                     if HyperTraining.prefix + stat in (row.get("flags") or [])]
        summary["moves"] = [{"slot": slot["slot"], "name": slot["move__name"], "pp": slot["current_pp"]}
                            for slot in slots]
        summary["pp_boosts"] = [{"move": str(value["move_id"]), "extra_pp": value["bonus_pp"]} for value in bonuses]
        return {"fingerprint": hashlib.sha256(json.dumps(state, sort_keys=True, default=str).encode()).hexdigest(),
                "summary": summary}
