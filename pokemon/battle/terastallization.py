"""Battle-scoped Tera declarations, typing and deterministic NPC eligibility."""

from __future__ import annotations

TERA_TYPES = (
    "Normal", "Fire", "Water", "Electric", "Grass", "Ice", "Fighting",
    "Poison", "Ground", "Flying", "Psychic", "Bug", "Rock", "Ghost",
    "Dragon", "Dark", "Steel", "Fairy", "Stellar",
)


class Terastallization:
    """Keep each side's single use separate from its Pokemon's saved Tera type."""

    @staticmethod
    def side(battle, participant):
        """Identify shared sides independently of their active slot count."""
        return getattr(participant, "team", None) or ("A" if battle.participants.index(participant) == 0 else "B")

    @staticmethod
    def identifier(pokemon):
        """Use the same stable roster identity as battle checkpoint alignment."""
        from .logic import _participant_identifier

        return _participant_identifier(pokemon)

    @staticmethod
    def type_for(pokemon):
        """Blank legacy configurations default to the first ordinary type."""
        configured = str(getattr(pokemon, "tera_type", "") or "").strip()
        types = getattr(pokemon, "tera_original_types", None) or getattr(pokemon, "types", [])
        value = configured or (types[0] if types else "")
        return next((typ for typ in TERA_TYPES if typ.lower() == str(value).lower()), None)

    @classmethod
    def validate(cls, battle, participant, pokemon, *, pending=False):
        """Reject unavailable battlers, incompatible mechanics and consumed sides."""
        if battle.battle_over or getattr(battle.type, "name", "") not in {"WILD", "TRAINER", "PVP"}:
            raise ValueError("Terastallization is unavailable in this battle.")
        if participant not in battle.participants or not any(mon is pokemon for mon in participant.active):
            raise ValueError("Choose an active Pokemon to Terastallize.")
        if getattr(pokemon, "hp", 0) <= 0 or getattr(pokemon, "is_fainted", False):
            raise ValueError("A fainted Pokemon cannot Terastallize.")
        if getattr(pokemon, "terastallized", None):
            raise ValueError("That Pokemon is already Terastallized.")
        side = cls.side(battle, participant)
        if side in getattr(battle, "tera_used", set()):
            raise ValueError("Your side has already used Terastallization this battle.")
        if not pending and side in getattr(battle, "tera_pending", {}):
            raise ValueError("Your side already has Terastallization reserved. Cancel it first.")
        species = str(getattr(pokemon, "species", getattr(pokemon, "name", ""))).lower()
        lookup = getattr(pokemon, "_lookup_species_entry", None)
        entry = lookup(species) if lookup else None
        species_data = entry if isinstance(entry, dict) else getattr(entry, "raw", {}) or {}
        forme = str(species_data.get("forme", "")).lower().split("-")[0]
        named_forme = species.split("-")[1:2]
        item = getattr(pokemon, "item", None)
        raw = getattr(item, "raw", {}) or {}
        if (species.startswith(("ogerpon", "terapagos"))
                or species_data.get("isMega") or species_data.get("isPrimal")
                or forme in {"mega", "primal"} or named_forme in (["mega"], ["primal"])
                or getattr(pokemon, "mega_evolved", False) or getattr(pokemon, "pending_mega", False)
                or raw.get("megaStone") or getattr(pokemon, "transformed", False)
                or "dynamax" in getattr(pokemon, "volatiles", {})):
            raise ValueError("Terastallization does not support that form or transformation yet.")
        tera_type = cls.type_for(pokemon)
        if tera_type is None:
            raise ValueError("That Pokemon has an unsupported Tera type.")
        return tera_type

    @classmethod
    def reserve(cls, battle, participant, pokemon):
        """Reserve one slot without using its action or consuming the side's use."""
        tera_type = cls.validate(battle, participant, pokemon)
        if not hasattr(battle, "tera_pending"):
            battle.tera_pending = {}
        battle.tera_pending[cls.side(battle, participant)] = {
            "pokemon": cls.identifier(pokemon), "type": tera_type,
            "slot": str(cls.slot(participant, pokemon)),
        }
        return tera_type

    @staticmethod
    def slot(participant, pokemon):
        """Distinguish otherwise identical ephemeral battlers within one side."""
        from .active_slots import slot_for

        return slot_for(participant, pokemon)

    @classmethod
    def activate(cls, battle, participant, pokemon, tera_type):
        """Commit an eligible locked declaration before moves are ordered."""
        try:
            if cls.validate(battle, participant, pokemon, pending=True) != tera_type:
                return False
        except ValueError:
            return False
        pokemon.tera_original_types = list(pokemon.types)
        pokemon.types = list(pokemon.types) if tera_type == "Stellar" else [tera_type]
        pokemon.terastallized = tera_type
        pokemon.stellar_boosted_types = []
        if not hasattr(battle, "tera_used"):
            battle.tera_used = set()
        side = cls.side(battle, participant)
        battle.tera_used.add(side)
        getattr(battle, "tera_pending", {}).pop(side, None)
        battle.log_action(f"{pokemon.name} Terastallized into the {tera_type} type!")
        return True

    @classmethod
    def lock(cls, battle, actions=None):
        """Only a living, still-active actor with a move may consume a reservation."""
        from .engine import ActionType

        if actions is None:
            actions = []
            for participant in battle.participants:
                queued = getattr(participant, "pending_action", None)
                actions.extend(queued if isinstance(queued, list) else [queued] if queued else [])
        for side, declaration in list(getattr(battle, "tera_pending", {}).items()):
            for action in actions:
                pokemon = action.pokemon
                if (action.action_type is ActionType.MOVE and pokemon is not None
                        and cls.side(battle, action.actor) == side
                        and str(cls.slot(action.actor, pokemon)) == declaration.get("slot")
                        and cls.identifier(pokemon) == declaration.get("pokemon")):
                    cls.activate(battle, action.actor, pokemon, declaration.get("type"))
                    break
            battle.tera_pending.pop(side, None)

    @classmethod
    def propose_ai(cls, battle, participant, action, profile):
        """Opt-in NPCs reserve Tera on a visible, damaging, nonimmune matching move."""
        from .damage import type_effectiveness

        if getattr(profile, "tera_policy", "none") != "matching_attack" or action.move is None:
            return False
        pokemon, move = action.pokemon, action.move
        try:
            tera_type = cls.validate(battle, participant, pokemon)
        except ValueError:
            return False
        raw = getattr(move, "raw", {}) or {}
        move_type = str(getattr(move, "type", ""))
        if (str(raw.get("category", "")).lower() == "status" or not getattr(move, "power", 0)
                or action.target_pokemon is None or type_effectiveness(action.target_pokemon, move) == 0):
            return False
        if tera_type != "Stellar" and move_type.lower() != tera_type.lower() and str(move.key).lower() != "terablast":
            return False
        cls.reserve(battle, participant, pokemon)
        return True

    @staticmethod
    def cleanup(battle):
        """Revert battle typing without writing to any owned Pokemon record."""
        for participant in battle.participants:
            for pokemon in participant.pokemons:
                if not hasattr(pokemon, "tera_original_types"):
                    continue
                if getattr(pokemon, "terastallized", None):
                    pokemon.terastallized = None
                    pokemon.types = list(pokemon.tera_original_types)
                pokemon.tera_original_types = []
                pokemon.stellar_boosted_types = []
        battle.tera_pending = {}


def tera_power_floor(attacker, move, power):
    """Apply Gen 9's 60-power floor, excluding priority, multi-hit and variable BP."""
    raw = getattr(move, "raw", {}) or {}
    tera = getattr(attacker, "terastallized", None)
    types = getattr(attacker, "types", [])
    matches = str(getattr(move, "type", "")).lower() in {str(typ).lower() for typ in types}
    key = str(getattr(move, "key", getattr(move, "name", ""))).replace(" ", "").lower()
    if (key != "struggle" and tera and matches and 0 < power < 60 and raw.get("priority", 0) <= 0
            and not raw.get("multihit") and not (raw.get("basePower", power) in (0, 150)
                                               and raw.get("basePowerCallback"))):
        return 60
    return power


def tera_blast_parameters(pokemon):
    """Return Tera Blast's type, category and power without mutating battle state."""
    tera = getattr(pokemon, "terastallized", None)
    if not tera:
        return "Normal", "Special", 80
    get_stat = getattr(pokemon, "getStat", None)
    boosts = getattr(pokemon, "boosts", {})

    def staged(short, full):
        """Compare staged offensive stats before ability/item modifiers."""
        value = get_stat(short, True, True) if callable(get_stat) else getattr(pokemon, short, 0)
        stage = max(-6, min(6, boosts.get(full, boosts.get(short, 0))))
        return value * (2 + stage) / 2 if stage >= 0 else value * 2 / (2 - stage)

    category = "Physical" if staged("atk", "attack") > staged("spa", "special_attack") else "Special"
    return tera, category, 100 if tera == "Stellar" else 80


def apply_stellar_cost(pokemon, move, result):
    """Pay Tera Blast's stat cost once per successful use, including substitutes."""
    if (str(move.key).lower() == "terablast" and getattr(pokemon, "terastallized", None) == "Stellar"
            and any(value > 0 for value in result.debug.get("damage", []))
            and not move._stellar_boosts.get("_drop")):
        from pokemon.utils.boosts import apply_boost

        apply_boost(pokemon, {"atk": -1, "spa": -1}, source=pokemon, effect=move)
        move._stellar_boosts["_drop"] = True
