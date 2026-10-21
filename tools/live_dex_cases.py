"""Catalog-driven local battle cases with explicitly bounded proof claims.

All loaded species/forms, unique moves and abilities receive a real logged-in
battle probe. Simple metadata outcomes have independent assertions. Conditional
or probabilistic behavior remains visibly unverified until a targeted case
proves it; a completed turn is never called full semantic coverage.
"""

from dataclasses import asdict, dataclass, field, replace

from live_battle_pilot_cases import Mon, Scenario, turn


def key(value):
    """Normalize dex names without treating compatibility aliases as entries."""
    return "".join(char for char in str(value).casefold() if char.isalnum())


@dataclass(frozen=True)
class DexCase(Scenario):
    """A catalog subject, concrete fixture and the exact asserted outcomes."""

    kind: str = ""
    subject: str = ""
    raw: dict = field(default_factory=dict)
    assertions: tuple[dict, ...] = ()
    limitations: tuple[str, ...] = ()
    pp_actor: str = "A"
    seed_each_turn: bool = False
    pp_source: str = "owned"
    entry_ability: str = ""


def unique_entries(entries):
    """Return one entry for each raw display name, sorted deterministically."""
    result = {}
    for alias, entry in entries.items():
        name = entry.raw.get("name", entry.name or alias)
        result.setdefault(key(name), (name, entry))
    return sorted(result.values(), key=lambda pair: key(pair[0]))


def native_ability(species):
    """Choose the species' ordinary first ability from the actual local dex."""
    return str(next(iter(species.raw.get("abilities", {}).values()), "No Ability"))


def species_cases(dex):
    """Check every loaded form's owned data, battle entry and normal action."""
    entries = {key(name): species for name, species in unique_entries(dex.POKEDEX)}
    entry_forms = {"Castform-Rainy": "Castform", "Castform-Snowy": "Castform",
                   "Castform-Sunny": "Castform", "Cherrim-Sunshine": "Cherrim",
                   "Minior": "Minior-Meteor", "Terapagos": "Terapagos-Terastal",
                   "Wishiwashi": "Wishiwashi-School"}
    for name, species in unique_entries(dex.POKEDEX):
        ability = native_ability(species)
        entry_form = entry_forms.get(name, name)
        entry_types = list(entries[key(entry_form)].raw["types"])
        assertions = [{"type": "species_identity", "entry_form": entry_form, "entry_types": entry_types}]
        if entry_form != name:
            assertions.append({"type": "native_stats", "value": entry_form, "initial": True})
        if name == "Terapagos":
            assertions.append({"type": "ability", "value": "Tera Shell", "initial": True})
        yield DexCase(
            "pokemon-" + key(name), "Species/form battle probe: " + name,
            (Mon(name, ("Tackle",), ability),),
            (Mon("Chansey", ("Splash",), "No Ability", level=100),),
            (turn("+attack Tackle"),), "dex", kind="pokemon", subject=name,
            raw=species.raw,
            expected="The stored identity is preserved; the declared native entry form/types and normal PP use are observed.",
            assertions=tuple(assertions),
            limitations=("Staff supplied Tackle; this does not prove natural learnsets, evolution or form activation requirements.",
                         "Native ability/form changes can legitimately alter identity, typing or action availability."),
        )


# These outcomes need additional coverage even after the prepared probe executes.
NEGATIVE_PRECONDITIONS = {
    "celebrate": "Celebration has no direct combat outcome.",
    "happyhour": "Prize money is not awarded during this PvP turn.",
    "holdhands": "Holding hands has no direct combat outcome.",
    "quash": "The target may already have acted; queue manipulation needs a dedicated order test.",
    "splash": "Splash deliberately has no combat effect.",
    "teleport": "A switching/escape outcome depends on battle rules and available reserves.",
}


def move_cases(dex):
    """Generate real command probes, with positive preconditions where practical."""
    for name, move in unique_entries(dex.MOVEDEX):
        raw, move_key = move.raw, key(name)
        category = str(raw.get("category", "Status"))
        a = Mon("Mew", (name,), "No Ability")
        b = Mon("Chansey", ("Splash",), "No Ability", level=70, gender="F")
        if raw.get("type") == "Ghost":
            b = replace(b, species="Wailord")
        if raw.get("ohko"):
            b = replace(b, level=50)
        before_turns, assertions, limitations = [], [], []
        b_command = "+attack Splash"
        if raw.get("heal") or raw.get("drain"):
            a = replace(a, hp_fraction=.35)
        if raw.get("heal") and raw.get("target") not in {"self", "allySide", "allyTeam"}:
            b = replace(b, hp_fraction=.35)
        if move_key in {"aurawheel"}:
            a = replace(a, species="Morpeko")
        if move_key == "darkvoid":
            a = replace(a, species="Darkrai")
        if move_key in {"burnup", "doubleshock"}:
            a = replace(a, species="Charizard" if move_key == "burnup" else "Pikachu")
        if move_key in {"hyperspacefury"}:
            a = replace(a, species="Hoopa-Unbound")
        if move_key in {"aurawheel", "ragingbull", "ivycudgel"}:
            limitations.append("Species-dependent move variants need additional form-specific outcomes.")
        if move_key in {"dreameater", "nightmare"}:
            b = replace(b, status="slp")
        if move_key in {"sleeptalk", "snore"}:
            a = replace(a, status="slp", moves=(name, "Tackle"))
        if move_key in {"spitup", "swallow"}:
            a = replace(a, moves=(name, "Stockpile"), hp_fraction=.35)
            before_turns.append(turn("+attack Stockpile"))
        if move_key == "steelroller":
            a = replace(a, moves=(name, "Electric Terrain"))
            before_turns.append(turn("+attack Electric Terrain"))
        if move_key in {"poltergeist", "knockoff", "thief", "covet", "corrosivegas"}:
            b = replace(b, item="Lagging Tail")
        if move_key in {"fling", "recycle", "naturalgift", "stuffcheeks"}:
            a = replace(a, item="Oran Berry", hp_fraction=.8)
        if move_key == "fling":
            a = replace(a, item="Iron Ball")
            limitations.append("This fixture tests an item with explicit Fling power; Berry defaults and thrown-item effects remain unverified.")
        if move_key in {"trick", "switcheroo"}:
            a, b = replace(a, item="Lagging Tail"), replace(b, item="Leftovers")
        if move_key == "bestow":
            a = replace(a, item="Lagging Tail")
        if move_key in {"entrainment", "roleplay", "skillswap"}:
            a, b = replace(a, ability="Blaze"), replace(b, ability="Overgrow")
        if move_key in {"counter", "metalburst", "bide", "comeuppance", "shelltrap"}:
            b = replace(b, moves=("Tackle",))
            b_command = "+attack Tackle"
            if move_key in {"metalburst", "comeuppance"}:
                b = replace(b, species="Jolteon")
        if move_key == "mirrorcoat":
            b = replace(b, moves=("Water Gun",))
            b_command = "+attack Water Gun"
        if move_key == "iondeluge":
            a = replace(a, species="Gengar", level=100, moves=(name, "Splash"))
            b = replace(b, species="Mew", level=50, moves=("Tackle",))
            b_command = "+attack Tackle"
        if move_key == "plasmafists":
            a = replace(a, species="Garchomp", level=100, moves=(name, "Splash"))
            b = replace(b, species="Registeel", level=100, moves=("Tackle",))
            b_command = "+attack Tackle"
        if move_key == "perishsong":
            a = replace(a, moves=(name, "Splash"))
        if move_key in {"suckerpunch", "upperhand"}:
            b = replace(b, moves=("Quick Attack",))
            b_command = "+attack Quick Attack"
        if move_key in {"quickguard", "matblock", "craftyshield", "wideguard"}:
            incoming = {"quickguard": "Quick Attack", "matblock": "Tackle",
                        "craftyshield": "Growl", "wideguard": "Surf"}[move_key]
            b = replace(b, moves=(incoming,))
            b_command = "+attack " + incoming
        if move_key == "substitute":
            b = replace(b, moves=("Tackle",))
            b_command = "+attack Tackle"
        if move_key in {"disable", "encore", "spite", "instruct", "mimic", "sketch", "torment", "mirrormove"}:
            a = replace(a, moves=(name, "Splash"))
            b = replace(b, moves=("Tackle",))
            before_turns.append(turn("+attack Splash", "+attack Tackle"))
            b_command = "+attack Tackle"
        if move_key == "lastresort":
            a = replace(a, moves=(name, "Splash"))
            before_turns.append(turn("+attack Splash"))
        if move_key == "auroraveil":
            a = replace(a, moves=(name, "Snowscape"))
            before_turns.append(turn("+attack Snowscape"))
        if move_key == "conversion":
            a = replace(a, moves=("Tackle", name))
        if move_key in {"conversion2", "copycat"}:
            a = replace(a, moves=(name, "Splash"))
            b = replace(b, moves=("Tackle",))
            before_turns.append(turn("+attack Splash", "+attack Tackle"))
            b_command = "+attack Tackle"
        if move_key == "doodle":
            b = replace(b, ability="Overgrow")
        if move_key in {"rest", "aquaring", "ingrain", "wish"}:
            a = replace(a, hp_fraction=.35)
        if move_key in {"moonlight", "morningsun", "shoreup", "synthesis"}:
            a = replace(a, hp_fraction=.35)
        if move_key == "psychoshift":
            a = replace(a, status="psn")
        if move_key == "rototiller":
            b = replace(b, species="Bulbasaur")
        if move_key in {"floralhealing", "healpulse"}:
            b = replace(b, hp_fraction=.35)
        if move_key in {"junglehealing", "lunarblessing"}:
            a = replace(a, hp_fraction=.35, status="psn")
        if move_key == "flowershield":
            b = replace(b, species="Bulbasaur")
        if move_key in {"gearup", "magneticflux"}:
            a = replace(a, ability="Plus")
        if move_key in {"guardswap", "heartswap", "powerswap", "psychup", "haze", "topsyturvy", "courtchange"}:
            setup_move = "Amnesia" if move_key == "guardswap" else "Reflect" if move_key == "courtchange" else "Swords Dance"
            a = replace(a, moves=(name, "Splash"))
            b = replace(b, moves=("Splash", setup_move))
            before_turns.append(turn("+attack Splash", "+attack " + setup_move))
        if move_key in {"belch", "recycle"}:
            # Let an actual held berry be consumed naturally on battle entry.
            # Recycle must finish above half HP to retain the restored berry.
            a = replace(a, item="Oran Berry", hp_fraction=.49 if move_key == "recycle" else .35)
        if move_key == "teatime":
            a = replace(a, item="Oran Berry", hp_fraction=.8)
        if move_key in {"attract", "captivate"}:
            a = replace(a, species="Eevee", gender="M")
        if move_key in {"snatch", "magiccoat", "mefirst"}:
            response = {"snatch": "Swords Dance", "magiccoat": "Growl", "mefirst": "Tackle"}[move_key]
            b = replace(b, moves=(response,))
            b_command = "+attack " + response
        if move_key == "synchronoise":
            b = replace(b, species="Slowpoke")
        if move_key == "venomdrench":
            b = replace(b, status="psn")
        if move_key in {"purify", "sparklingaria", "refresh", "aromatherapy", "healbell"}:
            a = replace(a, status="psn")
            b = replace(b, status="brn")
        if move_key == "smellingsalts":
            b = replace(b, status="par")
        if move_key in {"wakeupslap"}:
            b = replace(b, status="slp")
        target = raw.get("target", "normal")
        mode = "double" if target in {"adjacentAlly", "allies"} or move_key in {"afteryou", "allyswitch", "followme", "ragepowder", "wideguard"} else "single"
        a_team, b_team = (a,), (b,)
        if mode == "double":
            ally = Mon("Slowpoke", ("Splash",), "No Ability", hp_fraction=.35)
            a_team, b_team = (a, ally), (b, replace(b, species="Blissey", moves=("Splash",)))
            target_token = "A1" if target in {"self", "allies"} else "A2"
            test_turn = (("a", "+attack A1 " + name + " " + target_token), ("a", "+attack A2 Splash"),
                         ("b", "+attack B1 " + b_command.removeprefix("+attack ")), ("b", "+attack B2 Splash"))
            limitations.append("Only the declared ally targeting outcome is covered; other doubles interactions need targeted checks.")
        else:
            test_turn = turn("+attack " + name, b_command)
        if move_key in {"assist", "batonpass", "shedtail", "chillyreception", "teleport"} or raw.get("selfSwitch"):
            a_team += (Mon("Eevee", ("Tackle",), "No Ability"),)
        if move_key in {"healingwish", "lunardance"}:
            a_team = a_team[:1] + (Mon("Eevee", ("Splash",), "No Ability", hp_fraction=.35, status="psn"),)
        if move_key == "revivalblessing":
            a_team = a_team[:1] + (Mon("Eevee", ("Splash",), "No Ability", hp_fraction=0),)
        if raw.get("forceSwitch"):
            b_team += (Mon("Blissey", ("Splash",), "No Ability", level=70),)
        turns = list(before_turns) + [test_turn]
        if move_key in {"healingwish", "lunardance"}:
            turns = [turn("+switch 2"), turn("+attack Splash"), turn("+switch 1"), test_turn]
        if move_key == "iondeluge":
            turns.append(turn("+attack Splash", "+attack Tackle"))
        if move_key == "plasmafists":
            turns.append(turn("+attack Splash", "+attack Tackle"))
        if move_key == "perishsong":
            turns.extend([turn("+attack Splash")] * 3)
        if raw.get("flags", {}).get("charge") or move_key == "bide":
            turns.append(test_turn)
            if move_key == "bide":
                turns.append(test_turn)
        if move_key in {"futuresight", "doomdesire", "wish", "yawn"}:
            a_team = (replace(a_team[0], moves=a_team[0].moves + ("Splash",)),) + a_team[1:]
            turns.append(turn("+attack Splash"))
            if move_key in {"futuresight", "doomdesire"}:
                turns.append(turn("+attack Splash"))
        if move_key == "mimic":
            turns.append(turn("+attack Tackle", b_command))
        if move_key == "transform":
            turns.append(turn("+attack Splash"))
        if move_key in {"quickguard", "wideguard", "craftyshield"}:
            a_team = (replace(a_team[0], moves=a_team[0].moves + ("Splash",)),) + a_team[1:]
            if mode == "double":
                turns.append((("a", "+attack A1 Splash"), ("a", "+attack A2 Splash"),
                              ("b", "+attack B1 " + b_command.removeprefix("+attack ")), ("b", "+attack B2 Splash")))
            else:
                turns.append(turn("+attack Splash", b_command))
        # Assertions are intentionally limited to direct, observable outcomes.
        actor = "A" if target in {"self", "allies", "allySide", "allyTeam", "adjacentAlly"} else "B"
        actor_index = 1 if target == "adjacentAlly" else 0
        if category != "Status" and (raw.get("basePower", 0) or raw.get("damage") or raw.get("damageCallback")):
            assertions.append({"type": "damage", "side": "B"})
        if move_key in {"counter", "mirrorcoat", "metalburst", "comeuppance"}:
            assertions.append({"type": "retaliation", "multiplier": 2 if move_key in {"counter", "mirrorcoat"} else 1.5})
        if raw.get("boosts"):
            assertions.append({"type": "boosts", "side": actor, "index": actor_index, "values": raw["boosts"]})
        if raw.get("status"):
            assertions.append({"type": "status", "side": actor, "value": raw["status"]})
        if raw.get("heal"):
            assertions.append({"type": "heal", "side": actor, "index": actor_index})
        if raw.get("drain"):
            assertions.append({"type": "heal", "side": "A"})
        if raw.get("recoil"):
            assertions.append({"type": "damage", "side": "A"})
        if raw.get("weather"):
            assertions.append({"type": "weather", "value": raw["weather"]})
        if raw.get("terrain"):
            assertions.append({"type": "terrain", "value": raw["terrain"]})
        if raw.get("sideCondition") and move_key not in {"craftyshield", "matblock", "quickguard", "wideguard"}:
            assertions.append({"type": "side_condition", "side": actor, "value": raw["sideCondition"]})
        if raw.get("pseudoWeather") and move_key not in {"iondeluge", "plasmafists"}:
            assertions.append({"type": "pseudo_weather", "value": raw["pseudoWeather"]})
        if move_key == "plasmafists":
            assertions.extend(({"type": "immune", "side": "A", "after_turn": 1},
                               {"type": "damage", "side": "A"},
                               {"type": "executed_move", "side": "B", "value": "Tackle", "move_type": "Electric", "after_turn": 1},
                               {"type": "executed_move", "side": "B", "value": "Tackle", "move_type": "Normal", "after_turn": 2},
                               {"type": "pseudo_weather", "value": "iondeluge", "present": False, "after_turn": 1},
                               {"type": "pp_cost", "side": "A", "move": name, "value": 1},
                               {"type": "pp_cost", "side": "B", "move": "Tackle", "value": 2}))
        changed_types = {"conversion": ("A", ["Normal"]), "camouflage": ("A", ["Normal"]),
                         "magicpowder": ("B", ["Psychic"]), "soak": ("B", ["Water"])}
        if move_key in changed_types:
            affected, values = changed_types[move_key]
            assertions.append({"type": "types", "side": affected, "value": values})
        if move_key == "conversion2":
            assertions.append({"type": "types_one_of", "side": "A", "values": [["Rock"], ["Steel"], ["Ghost"]]})
        if move_key == "geomancy":
            assertions.extend(({"type": "boosts", "side": "A", "values": {"spa": 0, "spd": 0, "spe": 0}, "after_turn": 1},
                               {"type": "pp_cost", "side": "A", "move": name, "value": 1}))
        if move_key in {"fling", "stuffcheeks", "teatime"}:
            assertions.append({"type": "item", "side": "A", "value": ""})
        if move_key == "recycle":
            assertions.extend(({"type": "item", "side": "A", "value": "", "initial": True},
                               {"type": "item", "side": "A", "value": "Oran Berry"}))
        if move_key == "fling":
            assertions.append({"type": "damage", "side": "B"})
        if move_key == "stuffcheeks":
            assertions.append({"type": "boosts", "side": "A", "values": {"def": 2}})
        if move_key in {"stuffcheeks", "teatime"}:
            assertions.append({"type": "heal", "side": "A"})
        if move_key == "spite":
            assertions.append({"type": "pp_cost", "side": "B", "move": "Tackle", "value": 6})
        if move_key in {"guardsplit", "powersplit", "speedswap"}:
            values = ["def", "spd"] if move_key == "guardsplit" else ["atk", "spa"] if move_key == "powersplit" else ["spe"]
            assertions.extend({"type": "stat_swapped" if move_key == "speedswap" else "stat_average", "side": side, "values": values}
                              for side in ("A", "B"))
        if move_key in {"healingwish", "lunardance"}:
            assertions.extend(({"type": "active_species", "side": "A", "value": "Eevee"},
                               {"type": "hp_fraction", "side": "A", "minimum": 1, "maximum": 1},
                               {"type": "not_status", "side": "A", "value": "psn"}))
            assertions.extend(({"type": "stored_pp", "side": "A", "index": 1, "move": "Splash", "value": 39, "after_turn": 2},
                               {"type": "stored_pp", "side": "A", "index": 1, "move": "Splash", "value": 40 if move_key == "lunardance" else 39},
                               {"type": "runtime_move", "side": "A", "value": "Splash", "pp": 40 if move_key == "lunardance" else 39}))
            limitations.append("One injured/statused replacement and actual PP spent/restored are checked; multiple reserves and deferred use need further cases.")
        if move_key == "memento":
            assertions.append({"type": "hp_fraction", "side": "A", "original": True, "minimum": 0, "maximum": 0})
        if move_key == "iondeluge":
            assertions.extend(({"type": "damage", "side": "A", "after_turn": 1},
                               {"type": "hp_loss_range", "side": "A", "minimum": 0, "maximum": 0}))
            limitations.append("Normal Tackle must hit a Ghost only during this field effect; its next-turn expiry is checked separately.")
        if move_key == "bide":
            assertions.extend(({"type": "immune", "side": "B", "after_turn": 1},
                               {"type": "immune", "side": "B", "after_turn": 2},
                               {"type": "damage", "side": "B"},
                               {"type": "pp_cost", "side": "A", "move": name, "value": 1}))
            limitations.append("Two storage turns and release damage/one-PP are asserted; exact accumulated-damage multiplier needs an additional check.")
        if move_key == "perishsong":
            assertions.extend(({"type": "volatile", "side": "A", "value": "perishsong", "after_turn": 1},
                               {"type": "volatile", "side": "B", "value": "perishsong", "after_turn": 1},
                               {"type": "hp_fraction", "side": "A", "minimum": 0, "maximum": 0},
                               {"type": "hp_fraction", "side": "B", "minimum": 0, "maximum": 0}))
            limitations.append("Both unprotected actives and the four-turn countdown are checked; Soundproof/switch-out exceptions remain unverified.")
        if move_key == "revivalblessing":
            assertions.extend(({"type": "hp_fraction", "side": "A", "index": 1, "minimum": .49, "maximum": .5},
                               {"type": "active_species", "side": "A", "value": "Mew"}))
        if move_key == "mimic":
            assertions.extend(({"type": "runtime_move", "side": "A", "value": "Tackle", "pp": 34},
                               {"type": "stored_move", "side": "A", "value": "Mimic"}))
            limitations.append("Mimic uses the copied move's full base PP under the local primary rules; five PP is the Transform rule, with its one-PP exception.")
        if move_key == "sketch":
            assertions.append({"type": "stored_move", "side": "A", "value": "Tackle"})
        if move_key == "transform":
            assertions.extend(({"type": "active_species", "side": "A", "value": "Chansey"},
                               {"type": "runtime_move", "side": "A", "value": "Splash", "pp": 4},
                               {"type": "stored_move", "side": "A", "value": "Transform"}))
        if move_key in {"forestscurse", "trickortreat"}:
            assertions.append({"type": "has_type", "side": "B", "value": "Grass" if move_key == "forestscurse" else "Ghost"})
        if move_key == "reflecttype":
            assertions.append({"type": "types", "side": "A", "value": ["Normal"]})
        if move_key in {"moonlight", "morningsun", "shoreup", "synthesis"}:
            assertions.append({"type": "heal", "side": "A"})
        if move_key == "psychoshift":
            assertions.extend(({"type": "not_status", "side": "A", "value": "psn"},
                               {"type": "status", "side": "B", "value": "psn"}))
        if move_key == "rototiller":
            assertions.append({"type": "boosts", "side": "B", "values": {"atk": 1, "spa": 1}})
        if move_key == "matblock":
            assertions.append({"type": "immune", "side": "A"})
        if move_key in {"quickguard", "wideguard"}:
            assertions.extend(({"type": "immune", "side": "A", "after_turn": 1},
                               {"type": "hp_loss_range", "side": "A", "minimum": 1}))
            if move_key == "wideguard":
                assertions.append({"type": "immune", "side": "A", "index": 1, "after_turn": 1})
        if move_key == "craftyshield":
            assertions.extend(({"type": "boosts", "side": "A", "values": {"atk": 0}, "after_turn": 1},
                               {"type": "boosts", "side": "A", "values": {"atk": -1}}))
        if move_key == "substitute":
            assertions.extend(({"type": "hp_loss_fraction", "side": "A", "numerator": 1, "denominator": 4},
                               {"type": "volatile_hp", "side": "A", "value": "substitute", "minimum": 1,
                                "below_fraction": [1, 4]}))
        if move_key == "allyswitch":
            assertions.extend(({"type": "active_species", "side": "A", "index": 0, "value": "Slowpoke"},
                               {"type": "active_species", "side": "A", "index": 1, "value": "Mew"}))
        if move_key in {"batonpass", "teleport"}:
            assertions.append({"type": "active_species", "side": "A", "value": "Eevee"})
        if move_key in {"roar", "whirlwind"}:
            assertions.append({"type": "active_species", "side": "B", "value": "Blissey"})
        if move_key in {"floralhealing", "healpulse", "junglehealing", "lunarblessing"}:
            assertions.append({"type": "heal", "side": "B" if move_key in {"floralhealing", "healpulse"} else "A"})
        if move_key in {"junglehealing", "lunarblessing"}:
            assertions.append({"type": "not_status", "side": "A", "value": "psn"})
        if move_key in {"gearup", "magneticflux", "flowershield"}:
            values = {"atk": 1, "spa": 1} if move_key == "gearup" else {"def": 1, "spd": 1} if move_key == "magneticflux" else {"def": 1}
            assertions.append({"type": "boosts", "side": "B" if move_key == "flowershield" else "A", "values": values})
        if move_key in {"guardswap", "heartswap", "powerswap", "psychup", "haze", "topsyturvy"}:
            stat = "spd" if move_key == "guardswap" else "atk"
            side = "B" if move_key in {"haze", "topsyturvy"} else "A"
            value = 0 if move_key == "haze" else -2 if move_key == "topsyturvy" else 2
            assertions.append({"type": "boosts", "side": side, "values": {stat: value}})
        if move_key == "courtchange":
            assertions.extend(({"type": "side_condition", "side": "A", "value": "reflect"},
                               {"type": "side_condition", "side": "B", "value": "reflect", "present": False}))
        if move_key in {"rest", "aquaring", "ingrain", "wish"} and not any(e["type"] == "heal" for e in assertions):
            assertions.append({"type": "heal", "side": "A"})
        if move_key == "yawn":
            assertions.append({"type": "status", "side": "B", "value": "slp"})
        if move_key == "sleeptalk":
            assertions.append({"type": "damage", "side": "B"})
        if move_key == "snatch":
            assertions.append({"type": "boosts", "side": "A", "values": {"atk": 2}})
        if move_key == "magiccoat":
            assertions.extend(({"type": "boosts", "side": "A", "values": {"atk": 0}},
                               {"type": "boosts", "side": "B", "values": {"atk": -1}}))
        if move_key in {"mefirst", "mirrormove"}:
            assertions.append({"type": "damage", "side": "B"})
        if raw.get("secondary") or raw.get("secondaries"):
            limitations.append("Secondary effect probabilities and all secondary outcomes are not proven by this probe.")
        if any(str(hook).startswith("on") for hook in raw):
            limitations.append("Custom callback branches require targeted outcome checks beyond the direct assertions.")
        if raw.get("isZ") or raw.get("isMax"):
            limitations.append("Direct prepared-move execution does not prove legal Z/Max activation or availability.")
        if move_key in NEGATIVE_PRECONDITIONS:
            limitations.append(NEGATIVE_PRECONDITIONS[move_key])
        yield DexCase(
            "move-" + move_key, "Move battle probe: " + name, a_team, b_team,
            tuple(turns), "dex", mode=mode, kind="move", subject=name, raw=raw,
            expected="A normal command resolves and spends PP; declared direct outcomes are observed or diagnosed against valid failure rules.",
            assertions=tuple(assertions), limitations=tuple(limitations),
        )


# Entry state can be checked independently of damage RNG or message wording.
ENTRY_WEATHER = {
    "drizzle": "raindance", "drought": "sunnyday", "sandstream": "sandstorm",
    "snowwarning": "snow", "primordialsea": "primordialsea",
    "desolateland": "desolateland", "deltastream": "deltastream",
}
ENTRY_TERRAIN = {"electricsurge": "electricterrain", "grassysurge": "grassyterrain",
                 "mistysurge": "mistyterrain", "psychicsurge": "psychicterrain"}


def ability_cases(dex):
    """Give every ability a native carrier and real incoming/outgoing actions."""
    carriers = {}
    for name, species in unique_entries(dex.POKEDEX):
        for ability in species.raw.get("abilities", {}).values():
            carriers.setdefault(key(ability), name)
    for name, ability in unique_entries(dex.ABILITYDEX):
        ability_key, raw = key(name), ability.raw
        a = Mon(carriers.get(ability_key, "Mew"), ("Tackle",), name, level=100)
        b = Mon("Wailord", ("Tackle",), "No Ability", level=100)
        turns, assertions, limitations = [turn("+attack Tackle", "+attack Tackle")], [], []
        if ability_key in ENTRY_WEATHER:
            assertions.append({"type": "weather", "value": ENTRY_WEATHER[ability_key], "initial": True})
        if ability_key in ENTRY_TERRAIN:
            assertions.append({"type": "terrain", "value": ENTRY_TERRAIN[ability_key], "initial": True})
        if ability_key == "intimidate":
            assertions.append({"type": "boosts", "side": "B", "values": {"atk": -1}, "initial": True})
        if ability_key in {"intrepidsword", "dauntlessshield"}:
            stat = "atk" if ability_key == "intrepidsword" else "def"
            assertions.append({"type": "boosts", "side": "A", "values": {stat: 1}, "initial": True})
        absorb_moves = {"waterabsorb": "Water Gun", "stormdrain": "Water Gun", "dryskin": "Water Gun",
                        "voltabsorb": "Thunder Shock", "lightningrod": "Thunder Shock", "motordrive": "Thunder Shock",
                        "sapsipper": "Vine Whip", "eartheater": "Mud-Slap", "wellbakedbody": "Ember",
                        "flashfire": "Ember", "levitate": "Mud-Slap"}
        if ability_key in absorb_moves:
            attack = absorb_moves[ability_key]
            a = replace(a, moves=("Splash",), hp_fraction=.5)
            b = replace(b, moves=(attack,))
            turns = [turn("+attack Splash", "+attack " + attack)]
            assertions.append({"type": "immune", "side": "A"})
            if ability_key in {"waterabsorb", "voltabsorb", "dryskin", "eartheater"}:
                assertions.append({"type": "heal", "side": "A"})
            boosts = {"stormdrain": {"spa": 1}, "lightningrod": {"spa": 1}, "motordrive": {"spe": 1},
                      "sapsipper": {"atk": 1}, "wellbakedbody": {"def": 2}}
            if ability_key in boosts:
                assertions.append({"type": "boosts", "side": "A", "values": boosts[ability_key]})
            if ability_key == "flashfire":
                assertions.append({"type": "ability_state", "side": "A", "value": "flashfire"})
        status_guards = {"immunity": ("Poison Powder", "psn"), "pastelveil": ("Poison Powder", "psn"),
                         "limber": ("Thunder Wave", "par"), "insomnia": ("Spore", "slp"),
                         "vitalspirit": ("Spore", "slp"), "sweetveil": ("Spore", "slp"),
                         "waterveil": ("Will-O-Wisp", "brn"), "waterbubble": ("Will-O-Wisp", "brn"),
                         "magmaarmor": ("Ice Beam", "frz"), "purifyingsalt": ("Spore", "slp"),
                         "goodasgold": ("Thunder Wave", "par")}
        if ability_key in status_guards:
            attack, status = status_guards[ability_key]
            a, b = replace(a, moves=("Splash",)), replace(b, moves=(attack,))
            turns = [turn("+attack Splash", "+attack " + attack)]
            assertions.append({"type": "not_status", "side": "A", "value": status})
            limitations.append("A blocked status must also be distinguished from accuracy misses and native type immunity.")
        if ability_key in {"clearbody", "whitesmoke", "fullmetalbody", "hypercutter", "bigpecks", "keeneye", "mindseye"}:
            attack, stat = ("Growl", "atk")
            if ability_key == "bigpecks":
                attack, stat = "Tail Whip", "def"
            if ability_key in {"keeneye", "mindseye"}:
                attack, stat = "Sand Attack", "accuracy"
            a, b = replace(a, moves=("Splash",)), replace(b, moves=(attack,))
            turns = [turn("+attack Splash", "+attack " + attack)]
            assertions.append({"type": "boosts", "side": "A", "values": {stat: 0}})
        if ability_key == "speedboost":
            assertions.append({"type": "boosts", "side": "A", "values": {"spe": 1}})
        if ability_key == "imposter":
            owned_pp = dex.MOVEDEX["tackle"].raw["pp"]
            assertions.extend(({"type": "active_species", "value": b.species, "initial": True},
                               {"type": "ability", "value": b.ability, "initial": True},
                               {"type": "runtime_move", "value": "Tackle", "pp": 5, "initial": True},
                               {"type": "runtime_move", "value": "Tackle", "pp": 4},
                               {"type": "stored_pp", "move": "Tackle", "value": owned_pp},
                               {"type": "damage", "side": "B"}))
        if ability_key == "terashift":
            assertions.extend(({"type": "active_species", "value": "Terapagos-Terastal", "initial": True},
                               {"type": "types", "value": ["Normal"], "initial": True},
                               {"type": "ability", "value": "Tera Shell", "initial": True},
                               {"type": "native_stats", "value": "Terapagos-Terastal", "initial": True}))
        embody = {
            "embodyaspectteal": ("Ogerpon", "Defiant", "", "Grass", "Teal", "spe"),
            "embodyaspectwellspring": ("Ogerpon-Wellspring", "Water Absorb", "Wellspring Mask", "Water", "Wellspring", "spd"),
            "embodyaspecthearthflame": ("Ogerpon-Hearthflame", "Mold Breaker", "Hearthflame Mask", "Fire", "Hearthflame", "atk"),
            "embodyaspectcornerstone": ("Ogerpon-Cornerstone", "Sturdy", "Cornerstone Mask", "Rock", "Cornerstone", "def"),
        }
        if ability_key in embody:
            species, native, mask, typ, aspect, stat = embody[ability_key]
            a, b = Mon(species, ("Splash",), native, item=mask, level=100), replace(b, moves=("Splash",))
            turns = [(("a", "+tera"), ("a", "+attack Splash"), ("b", "+attack Splash"))]
            assertions.extend(({"type": "active_species", "value": f"Ogerpon-{aspect}-Tera"},
                               {"type": "ability", "value": name}, {"type": "types", "value": [typ]},
                               {"type": "boosts", "values": {stat: 1}}))
        if ability_key in {"iceface", "disguise"}:
            attack = "Tackle" if ability_key == "iceface" else "Shadow Ball"
            a, b = replace(a, moves=("Splash",)), replace(b, moves=(attack,))
            turns = [turn("+attack Splash", "+attack " + attack)] * 2
            form = "Eiscue-Noice" if ability_key == "iceface" else "Mimikyu-Busted"
            assertions.extend(({"type": "active_species", "side": "A", "value": form, "after_turn": 1},
                               {"type": "hp_loss_range", "side": "A", "minimum": 1}))
            if ability_key == "iceface":
                assertions.append({"type": "immune", "side": "A", "after_turn": 1})
            else:
                assertions.append({"type": "hp_loss_fraction", "side": "A", "numerator": 1,
                                   "denominator": 8, "after_turn": 1})
        if not assertions:
            limitations.append("Entry plus incoming/outgoing Tackle is a smoke probe; this ability's complete trigger/outcome is unverified.")
        if ability_key not in carriers:
            limitations.append("No native carrier exists in the loaded species catalog; this is an explicitly artificial Mew fixture.")
        if raw.get("isNonstandard"):
            limitations.append("Catalog marks this ability " + str(raw["isNonstandard"]) + ".")
        yield DexCase(
            "ability-" + ability_key, "Ability battle probe: " + name, (a,), (b,), tuple(turns), "dex",
            kind="ability", subject=name, raw=raw, assertions=tuple(assertions), limitations=tuple(limitations),
            pp_source="runtime" if ability_key == "imposter" else "owned",
            entry_ability=(embody[ability_key][1] if ability_key in embody else
                           b.ability if ability_key == "imposter" else "Tera Shell" if ability_key == "terashift" else ""),
            expected="The prepared ability is present on its real battle carrier, normal actions resolve, and declared triggered outcomes match.",
        )


def catalog():
    """Load all current local entries once, without database or network access."""
    from pokemon import dex

    return tuple(species_cases(dex)) + tuple(move_cases(dex)) + tuple(ability_cases(dex)) + regression_cases()


def regression_cases():
    """Fresh live reproductions for specific candidate defects, before repairs."""
    return (
        DexCase(
            "regression-pressure-scope", "Pressure must charge the opponent, not its holder",
            (Mon("Absol", ("Tackle",), "Pressure", level=100),),
            (Mon("Wailord", ("Tackle",), "No Ability", level=100),),
            (turn("+attack Tackle", "+attack Tackle"),), "dex", kind="regression", subject="Pressure PP scope",
            assertions=({"type": "pp_cost", "side": "A", "move": "Tackle", "value": 1},
                        {"type": "pp_cost", "side": "B", "move": "Tackle", "value": 2}),
            expected="Pressure holder spends one PP; an enemy targeting that holder spends two PP.",
        ),
        DexCase(
            "regression-pressure-self-move", "Pressure does not charge a self-targeted move",
            (Mon("Absol", ("Swords Dance",), "Pressure"),),
            (Mon("Chansey", ("Splash",), "Pressure", level=30),),
            (turn("+attack Swords Dance"),), "dex", kind="regression", subject="Pressure self targeting",
            assertions=({"type": "pp_cost", "side": "A", "move": "Swords Dance", "value": 1},
                        {"type": "pp_cost", "side": "B", "move": "Splash", "value": 1}),
            expected="Self-targeted moves spend one PP even with Pressure on both sides.",
        ),
    ) + sacrifice_regressions()


def sacrifice_regressions():
    """Qualifying ordinary-player negatives for repaired sacrifice/revival moves."""
    cases = []
    for name in ("Healing Wish", "Lunar Dance"):
        cases.append(DexCase(
            "regression-" + key(name) + "-no-reserve", "Sacrifice fails without a living replacement",
            (Mon("Mew", (name,), "No Ability"),), (Mon("Chansey", ("Splash",), "No Ability"),),
            (turn("+attack " + name),), "dex", kind="regression", subject=name + " without reserve",
            assertions=({"type": "immune", "side": "A"},
                        {"type": "active_species", "side": "A", "value": "Mew"},
                        {"type": "slot_condition", "side": "A", "value": key(name), "present": False},
                        {"type": "pp_cost", "side": "A", "move": name, "value": 1}),
            expected="An attempted sacrifice without a living reserve spends PP and leaves the user alive with no slot effect.",
        ))
    cases.append(DexCase(
        "regression-revivalblessing-living-reserve", "Revival fails when every reserve is alive",
        (Mon("Mew", ("Revival Blessing",), "No Ability"), Mon("Eevee", ("Splash",), "No Ability", hp_fraction=.35)),
        (Mon("Chansey", ("Splash",), "No Ability"),), (turn("+attack Revival Blessing"),), "dex",
        kind="regression", subject="Revival Blessing without fainted reserve",
        assertions=({"type": "active_species", "side": "A", "value": "Mew"}, {"type": "immune", "side": "A"},
                    {"type": "hp_fraction", "side": "A", "index": 1, "minimum": .34, "maximum": .35},
                    {"type": "slot_condition", "side": "A", "value": "revivalblessing", "present": False},
                    {"type": "pp_cost", "side": "A", "move": "Revival Blessing", "value": 1}),
        expected="No living ally is healed or switched in and no revival slot effect remains.",
    ))
    cases.append(DexCase(
        "regression-memento-protect", "Protect prevents Memento without sacrificing its user",
        (Mon("Mew", ("Memento",), "No Ability"),), (Mon("Chansey", ("Protect",), "No Ability"),),
        (turn("+attack Memento", "+attack Protect"),), "dex", kind="regression", subject="Protected Memento",
        assertions=({"type": "immune", "side": "A"}, {"type": "boosts", "side": "B", "values": {"atk": 0, "spa": 0}},
                    {"type": "pp_cost", "side": "A", "move": "Memento", "value": 1}),
        expected="Protect prevents the stat drops and the user survives its failed Memento attempt.",
    ))
    return tuple(cases)


def serializable(cases):
    """Return a pinned, complete catalog suitable for resumable run artifacts."""
    return [asdict(case) for case in cases]


def from_dict(data):
    """Rebuild the exact saved fixture rather than silently using a newer case."""
    data = dict(data)
    for side in ("a", "b"):
        data[side] = tuple(Mon(**mon) for mon in data[side])
    return DexCase(**data)
