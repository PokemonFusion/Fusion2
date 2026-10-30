"""One reviewed Ultra descriptor; it grants no ownership or activation permission."""

from dataclasses import asdict, dataclass
import hashlib
import json

from pokemon.names import resolve_dex_entry


@dataclass(frozen=True)
class UltraProfile:
    """Keep the existing sixteen Z signatures independent from the native Ultra proof."""

    version: int = 1
    crystal: str = "Ultranecrozium Z"
    source: str = "Photon Geyser"
    native: tuple = ("Necrozma-Dusk-Mane", "Necrozma-Dawn-Wings")
    target: str = "Necrozma-Ultra"
    native_ability: str = "Prism Armor"
    ability: str = "Neuroforce"
    signature: str = "Light That Burns the Sky"
    power: int = 200
    types: tuple = ("Psychic", "Dragon")

    @classmethod
    def checked(cls):
        """Refuse catalog drift rather than infer another form or crystal route."""
        from pokemon.dex import ITEMDEX, MOVEDEX, POKEDEX

        profile = cls()
        item = resolve_dex_entry(ITEMDEX, profile.crystal)
        form = resolve_dex_entry(POKEDEX, profile.target)
        move = resolve_dex_entry(MOVEDEX, profile.signature)
        item_data = getattr(item, "raw", {}) or {}
        form_data = getattr(form, "raw", {}) or {}
        move_data = getattr(move, "raw", {}) or {}
        if (
            item_data.get("zMove") != profile.signature
            or item_data.get("zMoveFrom") != profile.source
            or item_data.get("itemUser") != [profile.target]
            or form_data.get("baseSpecies") != "Necrozma"
            or form_data.get("forme") != "Ultra"
            or set(form_data.get("battleOnly", ())) != set(profile.native)
            or form_data.get("requiredItem") != profile.crystal
            or tuple(form_data.get("types", ())) != profile.types
            or form_data.get("abilities", {}).get("0") != profile.ability
            or not form_data.get("baseStats")
            or move_data.get("basePower") != profile.power
            or move_data.get("type") != "Psychic"
            or move_data.get("target") != "normal"
            or move_data.get("accuracy") is not True
            or move_data.get("ignoreAbility") is not True
        ):
            raise ValueError(
                "The reviewed Ultra descriptor disagrees with the catalog; recovery is required."
            )
        return profile

    @property
    def fingerprint(self):
        """Bind the exact immutable selected policy, independently of mutable PP."""
        return hashlib.sha256(json.dumps(asdict(self), sort_keys=True).encode()).hexdigest()

    @staticmethod
    def source_is_learnable(level):
        """Reuse legitimate base-species cross-generation access; no new level72 gate."""
        from pokemon.data.generation import get_valid_moves
        from pokemon.names import normalize_name

        return (
            type(level) is int
            and 1 <= level <= 100
            and any(
                normalize_name(move) == "photongeyser"
                for move in get_valid_moves("Necrozma", level)
            )
        )

    @staticmethod
    def category(pokemon):
        """Match the reference's stored stats/stages, skipping modifier events.

        PF2's generic getStat currently suppresses stages when unmodified=True.
        Read its unboosted/unmodified stored value and apply the ordinary raw
        stage explicitly here; do not change unrelated getStat consumers.
        """

        def staged(stat):
            """No ModifyBoost, held Attack modifier or ability modifier participates."""
            value = pokemon.getStat(stat, True, True)
            stage = (getattr(pokemon, "boosts", None) or {}).get(stat, 0)
            if type(value) is not int or value <= 0 or type(stage) is not int:
                raise ValueError("Invalid Ultra category stats require battle recovery.")
            stage = max(-6, min(6, stage))
            return value * (2 + stage) // 2 if stage >= 0 else value * 2 // (2 - stage)

        return "Physical" if staged("atk") > staged("spa") else "Special"

    def z_profile(self):
        """Return one private descriptor; the normal registry remains guarded separately."""
        from .z_profiles import ZProfile

        return ZProfile(
            self.crystal,
            self.source,
            self.signature,
            self.power,
            "Psychic",
            "Special",
            kind="ultra",
            native=(self.target,),
            ignore_ability=True,
            intrinsic="ultra",
        )
