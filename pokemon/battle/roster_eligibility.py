"""Separate owned egg custody from combat roster membership and recovery."""


class BattleRosterRecoveryRequired(ValueError):
    """Retain an incompatible saved roster for explicit staff recovery."""


class BattleRosterEligibility:
    """Exclude eggs at setup and refuse legacy rosters without rewriting custody."""

    @staticmethod
    def models(party):
        """Keep fainted non-eggs and Fusion order; read persistent egg flags fresh."""
        from pokemon.helpers.party_helpers import pokemon_is_battle_member

        party = [mon for mon in party if mon is not None]
        persistent = [mon for mon in party if getattr(mon, "_meta", None)]
        flags = {}
        if persistent:
            from pokemon.models.core import OwnedPokemon

            flags = dict(OwnedPokemon.objects.filter(pk__in=[mon.pk for mon in persistent])
                         .values_list("pk", "is_egg"))
        members = []
        for mon in party:
            eligible = (not flags.get(mon.pk, True) if getattr(mon, "_meta", None)
                        else pokemon_is_battle_member(mon))
            if eligible:
                members.append(mon)
        return members

    @staticmethod
    def egg_refs(battle):
        """Read current owned egg flags for persistent player rosters, including reserves."""
        from pokemon.services.battle_rewards import BattleRewards
        from pokemon.services.pokemon_refs import parse_pokemon_ref

        identifiers = set()
        for participant in getattr(battle, "participants", []):
            if not BattleRewards.supports(getattr(participant, "player", None)):
                continue
            for pokemon in participant.pokemons:
                kind, identifier = parse_pokemon_ref(getattr(pokemon, "model_id", None))
                if kind == "owned" and identifier:
                    identifiers.add(identifier)
        if not identifiers:
            return []
        from django.db import connection
        from pokemon.models.core import OwnedPokemon

        rows = OwnedPokemon.objects.filter(pk__in=identifiers).order_by("pk")
        if connection.in_atomic_block:
            rows = rows.select_for_update()
        return ["owned:" + str(pk) for pk, is_egg in rows.values_list("pk", "is_egg") if is_egg]

    @classmethod
    def quarantine(cls, session):
        """Retain data/declarations intact; save a separate durable recovery marker."""
        storage = getattr(session, "storage", None)
        getter = getattr(storage, "get", None)
        marker = getter("roster_recovery") if callable(getter) else None
        eggs = cls.egg_refs(getattr(session, "battle", None))
        if not marker and eggs:
            marker = {"reason": "unhatched-egg-in-battle-roster", "egg_refs": eggs}
            storage.set("roster_recovery", marker)
        return marker

    @classmethod
    def require(cls, session):
        """Reject input, turns and end writes before PP, HP, rewards or custody change."""
        if cls.quarantine(session):
            raise BattleRosterRecoveryRequired(
                f"Battle #{session.battle_id} contains an egg in its saved roster and is paused. "
                "Ask staff to recover this battle; its checkpoint and Pokemon are retained."
            )
