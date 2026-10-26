"""Fresh native ownership checks for reusable player battle mechanics."""

from contextlib import contextmanager

from pokemon.names import normalize_name


class BattleOwnershipChanged(ValueError):
    """Fresh persistent identity changed; abort the complete turn for recovery."""


class OwnedBattleActor:
    """Never infer a native holder from its nickname or copied appearance."""

    @staticmethod
    def item_key(pokemon):
        """Read actual held ownership independently of held-effect suppression."""
        item = getattr(pokemon, "item", None)
        raw = getattr(item, "raw", {}) or {}
        return normalize_name(raw.get("name") or getattr(item, "name", item) or "")

    @staticmethod
    def controller(participant):
        """Resolve only a real ordinary human controller, including test transports."""
        from pokemon.services.battle_rewards import BattleRewards

        player = getattr(participant, "player", None)
        if getattr(participant, "is_ai", True) or not BattleRewards.supports(player):
            raise ValueError("Only the current ordinary player can declare this mechanic.")
        return BattleRewards.character(player)

    @classmethod
    @contextmanager
    def locked(cls, battle, participant, pokemon, *, active=True):
        """Lock character, storage, trainer, owned row and canonical placement."""
        from django.db import transaction
        from evennia.objects.models import ObjectDB
        from pokemon.models.core import OwnedPokemon
        from pokemon.models.storage import PokemonPlacement, UserStorage
        from pokemon.models.trainer import Trainer
        from pokemon.models.ownership import PokemonReservation
        from pokemon.services.battle_rewards import BattleRewards
        from pokemon.services.pokemon_refs import parse_pokemon_ref

        if (
            participant not in battle.participants
            or (battle.battle_over and active)
            or getattr(battle.type, "name", "") not in {"WILD", "TRAINER", "PVP"}
            or (len(battle.participants) != 2 and not (
                getattr(battle, 'multi', False) and len(battle.participants) == 4
                and all(getattr(part, 'max_active', 1) == 1 for part in battle.participants)
                and all(sum(part.team == team for part in battle.participants) == 2 for team in ('A', 'B'))
                and len({getattr(part, 'controller_id', None) for part in battle.participants}) == 4))
            or any(getattr(part, "max_active", 1) not in {1, 2} for part in battle.participants)
            or not getattr(battle, "mechanic_battle_id", None)
        ):
            raise ValueError("That battle does not support this player mechanic.")
        if active and (
            not any(mon is pokemon for mon in participant.active)
            or pokemon.hp <= 0
            or getattr(pokemon, "is_fainted", False)
        ):
            raise ValueError("Choose your conscious current active Pokemon.")
        character = cls.controller(participant)
        kind, identifier = parse_pokemon_ref(getattr(pokemon, "model_id", None))
        if kind != "owned" or not identifier:
            raise ValueError("This mechanic requires a native owned Pokemon.")
        with transaction.atomic():
            character = ObjectDB.objects.select_for_update().get(pk=character.pk)
            if getattr(battle, "mechanic_session_id", None) is not None and str(
                BattleRewards.stored_attribute(character, "battle_id")
            ) != str(battle.mechanic_session_id):
                raise BattleOwnershipChanged("That controller is no longer in this battle session.")
            storage = (
                UserStorage.objects.select_for_update()
                .filter(user_id=character.pk)
                .values("pk")
                .first()
            )
            trainer = (
                Trainer.objects.select_for_update()
                .filter(user_id=character.pk)
                .values("pk")
                .first()
            )
            row = OwnedPokemon.objects.select_for_update().filter(pk=identifier).values().first()
            placement = (
                PokemonPlacement.objects.select_for_update()
                .filter(pokemon_id=identifier)
                .values()
                .first()
            )
            if (
                not storage
                or not trainer
                or not row
                or row["trainer_id"] != trainer["pk"]
                or row["is_egg"]
                or not placement
                or placement["storage_id"] != storage["pk"]
                or placement["location_type"] not in {"party", "fusion"}
                or PokemonReservation.objects.filter(pokemon_id=identifier).exists()
            ):
                raise BattleOwnershipChanged(
                    "That Pokemon is no longer your eligible party or current Fusion."
                )
            if placement["location_type"] == "fusion" and str(
                BattleRewards.stored_attribute(character, "fusion_id", default="")
            ) != str(identifier):
                raise BattleOwnershipChanged("That Fusion reservation is not currently active.")
            origin = getattr(pokemon, "native_origin", None)
            if (
                not isinstance(origin, dict)
                or origin.get("ref") != str(pokemon.model_id)
                or normalize_name(origin.get("species", "")) != normalize_name(row["species"])
            ):
                raise BattleOwnershipChanged(
                    "Native battle provenance changed; choose again after recovery."
                )
            from .necrozma import NativeNecrozmaBattle

            NativeNecrozmaBattle.validate_actor(battle, participant, pokemon, row=row)
            yield row

    @staticmethod
    def incompatible(battle, participant, pokemon, *, mechanic):
        """Separate team budgets cannot stack active or pending mechanics on one actor."""
        from .terastallization import Terastallization

        side = Terastallization.side(battle, participant)
        if (getattr(pokemon, "native_origin", None) or {}).get("necrozma") and mechanic != "z":
            return True
        identifier = Terastallization.identifier(pokemon)
        for name in ("tera", "mega", "z"):
            if name == mechanic:
                continue
            pending = getattr(battle, name + "_pending", {}).get(side, {})
            if pending.get("pokemon") == identifier:
                return True
        return bool(
            getattr(pokemon, "terastallized", None)
            or getattr(pokemon, "mega_evolved", False)
            or getattr(pokemon, "z_activated", False)
            or getattr(pokemon, "transformed", False)
            or "dynamax" in getattr(pokemon, "volatiles", {})
        )
