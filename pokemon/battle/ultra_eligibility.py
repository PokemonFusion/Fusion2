"""Fresh native pair and legitimate Photon preparation for the reviewed Ultra route."""

from dataclasses import dataclass

from pokemon.names import normalize_name
from .effect_context import EffectContext
from .necrozma import NativeNecrozmaBattle
from .owned_battle_actor import OwnedBattleActor
from .ultra_profile import UltraProfile
from .z_moves import ZMoves


@dataclass(frozen=True)
class UltraPreparation:
    """Structural source identity plus current PP for an honest terms preview."""

    profile: str
    native: str
    pair: dict
    photon_slot: int
    photon_id: int
    current_pp: int
    capacity: int


class UltraEligibility:
    """A crystal grants no form: require current native lifecycle and active source."""

    @classmethod
    def binding(cls, battle, participant, pokemon):
        """Lock real controller/storage/owned placement before reading any preparation."""
        with OwnedBattleActor.locked(battle, participant, pokemon) as row:
            return cls.validate(battle, participant, pokemon, row)

    @staticmethod
    def validate(battle, participant, pokemon, row):
        """Activation permits Photon0, never a missing/dormant/displaced source slot."""
        profile = UltraProfile.checked()
        pair = NativeNecrozmaBattle.validate_actor(battle, participant, pokemon, row=row)
        if (
            not pair
            or row["species"] not in profile.native
            or row["species"] != pair["target_species"]
            or str(pokemon.species) != row["species"]
            or getattr(pokemon, "_pf2_active_fusion", False)
            or getattr(pokemon, "transformed", False)
            or getattr(pokemon, "mega_evolved", False)
            or getattr(pokemon, "terastallized", None)
            or getattr(pokemon, "z_activated", False)
            or "dynamax" in (getattr(pokemon, "volatiles", None) or {})
        ):
            raise ValueError(
                "Ultra Burst requires your current genuine Dusk Mane or Dawn Wings pair."
            )
        if normalize_name(row["held_item"]) != normalize_name(
            profile.crystal
        ) or OwnedBattleActor.item_key(pokemon) != normalize_name(profile.crystal):
            raise ValueError("Equip the real Ultranecrozium Z on that native host first.")
        if (
            normalize_name(row["ability"]) != normalize_name(profile.native_ability)
            or EffectContext.key(EffectContext.ability(pokemon)) != "prismarmor"
            or getattr(pokemon, "native_ability_provenance", None) != "native"
        ):
            raise ValueError(
                "Ultra Burst needs active native Prism Armor, without a copied, replaced or suppressed ability."
            )
        from pokemon.models.stats import level_for_exp

        if (
            type(row["level"]) is not int
            or type(row["total_exp"]) is not int
            or row["total_exp"] < 0
            or level_for_exp(row["total_exp"]) != row["level"]
            or not profile.source_is_learnable(row["level"])
        ):
            raise ValueError("This host lacks legitimate current native Photon Geyser preparation.")
        source, pp, maximum, _ = ZMoves.source(pokemon, row, profile.source, require_pp=False)
        if source.slot == pair["move_slot"] or row["active_moveset_id"] != pair["moveset_id"]:
            raise ValueError(
                "Keep Photon Geyser active in a different slot before combining; separate and prepare it normally."
            )
        from .terastallization import Terastallization

        side = Terastallization.side(battle, participant)
        for mechanic in ("mega", "tera", "z"):
            request = getattr(battle, mechanic + "_pending", {}).get(side, {})
            if request.get("pokemon") == Terastallization.identifier(pokemon):
                raise ValueError(
                    "Cancel that actor's incompatible pending mechanic before Ultra Burst."
                )
        return UltraPreparation(
            profile.fingerprint,
            row["species"],
            NativeNecrozmaBattle.proof(pair),
            source.slot,
            source.move_id,
            pp,
            maximum,
        )
