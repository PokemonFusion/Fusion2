"""Reviewed transient Z definitions; learned moves and the shared dex stay ordinary."""

from copy import copy, deepcopy
from dataclasses import dataclass

from pokemon.names import normalize_name, resolve_dex_entry


@dataclass(frozen=True)
class ZProfile:
    """One explicitly accepted crystal/source pair and its intrinsic effect."""

    crystal: str
    source: str
    name: str
    power: int
    move_type: str
    category: str
    target: str = "normal"
    kind: str = "generic"
    native: tuple = ()
    contact: bool = False
    sound: bool = False
    bypass_substitute: bool = False
    critical_stage: int = 0
    ignore_ability: bool = False
    intrinsic: str = ""
    bonus: tuple = ()

    def descriptor(self, source, pokemon=None):
        """Build a private runtime move after the ordinary source prevention pass."""
        from pokemon.battle.engine import BattleMove
        from pokemon.dex import MOVEDEX

        if self.kind == "status":
            raw = deepcopy(resolve_dex_entry(MOVEDEX, self.source).raw)
            raw.pop("zMove", None)
            # The ordinary fallback treats an absent protect flag as true.
            # Reviewed status copies use the source metadata's actual flag.
            raw["flags"] = deepcopy(raw.get("flags", {}))
            raw["flags"].setdefault("protect", 0)
            raw["name"] = "Z-" + self.source
            raw["isZ"] = normalize_name(self.crystal)
            if self.intrinsic == "curse" and pokemon is not None:
                raw["target"] = "normal" if "Ghost" in pokemon.types else "self"
                if "Ghost" not in pokemon.types:
                    raw.pop("volatileStatus", None)
            name = raw["name"]
        else:
            flags = {}
            if self.contact:
                flags["contact"] = 1
            if self.sound:
                flags["sound"] = 1
            if self.bypass_substitute:
                flags["bypasssub"] = 1
            raw = {
                "name": self.name,
                "basePower": self.power,
                "type": self.move_type,
                "category": self.category,
                "priority": 0,
                "accuracy": True,
                "target": self.target,
                "flags": flags,
                "isZ": normalize_name(self.crystal),
                "critRatio": self.critical_stage,
            }
            if self.ignore_ability:
                raw["ignoreAbility"] = True
            if self.intrinsic == "paralysis":
                raw["secondary"] = {"chance": 100, "status": "par"}
            if self.category == "Status" and self.bonus:
                raw["boosts"] = dict(self.bonus)
            if self.intrinsic == "soulblaze":
                # Truthy no-op secondary exposes the reviewed Sheer Force
                # interaction without copying Clanging Scales' Defense drop.
                raw["secondary"] = {"chance": 100}
            if self.intrinsic == "guardian":
                raw["zGuardian"] = True
            if self.intrinsic == "ultra" and pokemon is not None:
                from .ultra_profile import UltraProfile

                raw["category"] = UltraProfile.category(pokemon)
            name = self.name
        if self.kind == "status":
            # The ordinary engine has already bound the base callbacks.
            move = copy(source)
            move.name, move.raw, move.flags = name, raw, deepcopy(raw.get("flags", {}))
        else:
            move = BattleMove(
                name,
                key=normalize_name(name),
                power=self.power,
                type=self.move_type,
                priority=0,
                accuracy=True,
                pp=source.pp,
                raw=raw,
            )
        move.isZ = True
        move._pp_move_name = self.source
        move._z_paid = True
        move._z_profile = self
        return move


class ZProfiles:
    """Metadata alone cannot release any crystal or source move."""

    accepted = {
        ("normaliumz", "tackle"): ZProfile(
            "Normalium Z", "Tackle", "Breakneck Blitz", 100, "Normal", "Physical"
        ),
    }

    @classmethod
    def get(cls, crystal, source):
        """Resolve only a specifically qualified pair, never every zMove field."""
        from .z_generic_pairs import GENERIC_PAIRS
        from .z_status_pairs import STATUS_PAIRS
        from .z_signature_pairs import SIGNATURE_PAIRS

        key = normalize_name(crystal), normalize_name(source)
        if key == ("ultranecroziumz", "photongeyser"):
            from .ultra_profile import UltraProfile

            return UltraProfile.checked().z_profile()
        return cls.accepted.get(key) or next(
            (
                profile
                for profile in (*GENERIC_PAIRS, *STATUS_PAIRS, *SIGNATURE_PAIRS)
                if (normalize_name(profile.crystal), normalize_name(profile.source)) == key
            ),
            None,
        )
