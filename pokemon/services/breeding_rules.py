"""Bounded Generation 9 breeding traits; no persistence or hidden rerolls."""

from types import SimpleNamespace

from pokemon.data.breeding import determine_egg_species
from pokemon.data.generation import NATURES, get_gender
from pokemon.data.learnsets.learnsets import LEARNSETS
from pokemon.dex import MOVEDEX, POKEDEX
from pokemon.names import normalize_name, resolve_dex_entry


class BreedingRuleError(ValueError):
    """Unsupported or invalid parents must fail before any fee or cycle exists."""


class BreedingRules:
    """Support ordinary base species and explicit essential inheritance only."""

    version = 1
    special_families = {"nidoranf", "nidoranm", "nidorina", "nidoqueen", "nidorino", "nidoking",
        "volbeat", "illumise", "indeedee", "rockruff", "manaphy", "phione"}
    power_items = {"powerweight": 0, "powerbracer": 1, "powerbelt": 2,
                   "powerlens": 3, "powerband": 4, "poweranklet": 5}

    @classmethod
    def parent(cls, source):
        """Validate stored genetic identity; never treat battle transforms as parents."""
        entry = resolve_dex_entry(POKEDEX, source.species)
        if entry is None or getattr(source, "is_egg", False):
            raise BreedingRuleError("Use two hatched Pokemon with known saved species.")
        raw = entry.raw
        base = raw.get("baseSpecies") or entry.name
        if (getattr(source, "transformed", False) or raw.get("forme")
                or normalize_name(base) != normalize_name(entry.name)
                or any(raw.get(key) for key in ("battleOnly", "requiredItem", "requiredItems", "requiredAbility"))
                or normalize_name(base) in cls.special_families):
            raise BreedingRuleError("This form or special offspring family is outside the beta breeding scope.")
        if source.gender not in {"M", "F", "N"} or raw.get("gender") and raw["gender"] != source.gender:
            raise BreedingRuleError("Saved gender is invalid for this parent.")
        if raw.get("gender") is None and source.gender == "N":
            ratio = raw.get("genderRatio", {"M": .5, "F": .5})
            if ratio.get("M", 0) or ratio.get("F", 0):
                raise BreedingRuleError("Saved gender is invalid for this parent.")
        if source.nature not in NATURES or len(source.ivs) != 6 or any(type(iv) is not int or not 0 <= iv <= 31 for iv in source.ivs):
            raise BreedingRuleError("Parent has invalid saved nature or genetic IVs; ask staff to inspect it.")
        slots = raw.get("abilities", {})
        matching = [slot for slot, name in slots.items() if normalize_name(name) == normalize_name(source.ability)]
        if len(matching) != 1 or matching[0] not in {"0", "1", "H"}:
            raise BreedingRuleError("Parent has a foreign or ambiguous saved ability slot.")
        return entry, matching[0]

    @classmethod
    def pair(cls, left, right):
        """Reuse audited compatibility/base-species logic after explicit exclusions."""
        if str(left.pk) == str(right.pk):
            raise BreedingRuleError("Choose two different Daycare parents.")
        entries = [cls.parent(source)[0] for source in (left, right)]
        dittos = [entry.name == "Ditto" for entry in entries]
        if all(dittos):
            raise BreedingRuleError("Two Ditto cannot produce an egg.")
        if not any(dittos) and {left.gender, right.gender} != {"M", "F"}:
            raise BreedingRuleError("These parents need opposite genders or one compatible Ditto.")
        try:
            species = determine_egg_species(*(SimpleNamespace(species=entry, gender=source.gender)
                for entry, source in zip(entries, (left, right))))
        except ValueError as error:
            raise BreedingRuleError(str(error)) from error
        child = resolve_dex_entry(POKEDEX, species)
        learnset = LEARNSETS.get(normalize_name(species), {}).get("learnset", {})
        if child is None or not any(code.startswith("9L") for codes in learnset.values() for code in codes):
            raise BreedingRuleError("The offspring needs verified Generation 9 level-up move data before breeding is enabled.")
        inherited_from = (1 if dittos[0] else 0) if any(dittos) else (0 if left.gender == "F" else 1)
        return child, learnset, inherited_from

    @staticmethod
    def move_name(key):
        """Use the existing move catalog's canonical public name."""
        move = resolve_dex_entry(MOVEDEX, key)
        if move is None:
            raise BreedingRuleError("Offspring move data requires staff review.")
        return move.name

    @classmethod
    def plan(cls, left, right, active_moves, *, rng):
        """Choose once before saving the durable cycle; caller persists the whole plan."""
        child, learnset, mother = cls.pair(left, right)
        parents = (left, right)
        items = [normalize_name(source.held_item or "") for source in parents]
        count = 5 if "destinyknot" in items else 3
        inherited = {}
        guaranteed = [(cls.power_items[item], index) for index, item in enumerate(items) if item in cls.power_items]
        if guaranteed:
            stat, parent = rng.choice(guaranteed)
            inherited[stat] = parent
        for stat in rng.sample([index for index in range(6) if index not in inherited], count - len(inherited)):
            inherited[stat] = rng.randrange(2)
        ivs = [parents[inherited[stat]].ivs[stat] if stat in inherited else rng.randrange(32) for stat in range(6)]
        everstones = [source.nature for source, item in zip(parents, items) if item == "everstone"]
        nature = rng.choice(everstones or list(NATURES))
        slots = child.raw.get("abilities", {})
        ordinary = [slot for slot in ("0", "1") if slot in slots]
        if not ordinary:
            raise BreedingRuleError("Offspring has no supported ordinary ability slot.")
        parent_slot = cls.parent(parents[mother])[1]
        roll = rng.random()
        if parent_slot == "H" and "H" in slots and roll < .6:
            ability_slot = "H"
        elif parent_slot in ordinary and roll < .8:
            ability_slot = parent_slot
        elif parent_slot in ordinary and len(ordinary) == 2:
            ability_slot = next(slot for slot in ordinary if slot != parent_slot)
        else:
            ability_slot = rng.choice(ordinary)
        known = [{normalize_name(move) for move in moves} for moves in active_moves]
        defaults, shared, egg = [], [], []
        for key, codes in sorted(learnset.items()):
            if "9L1" in codes:
                defaults.append(key)
            if key in known[0] & known[1] and any(code.startswith("9L") for code in codes):
                shared.append(key)
            if key in known[0] | known[1] and any(code.startswith("9E") for code in codes):
                egg.append(key)
        moves = []
        for key in defaults + shared + egg:
            if key in moves:
                moves.remove(key)
            moves.append(key)
        moves = [cls.move_name(key) for key in moves[-4:]]
        if not moves:
            raise BreedingRuleError("Offspring has no supported hatch moves.")
        return {"rule_version": cls.version, "species": child.name,
            "gender": get_gender(child.raw.get("genderRatio"), child.raw.get("gender"), rng=rng),
            "nature": nature, "ability": slots[ability_slot], "ability_slot": ability_slot,
            "ivs": ivs, "evs": [0] * 6, "moves": moves, "is_shiny": rng.randrange(4096) == 0,
            "genetic_iv_sources": {str(stat): source for stat, source in inherited.items()},
            "ability_parent": mother}
