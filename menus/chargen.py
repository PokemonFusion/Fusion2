"""
Chargen EvMenu nodes for Pokémon Fusion.
Moved out of commands/cmd_chargen.py to centralize menus.
"""

from __future__ import annotations

from typing import Dict

from pokemon.data.generation import NATURES as NATURES_MAP
from pokemon.data.generation import generate_pokemon
from pokemon.data.starters import STARTER_LOOKUP, get_starter_names
from pokemon.dex import POKEDEX
from pokemon.helpers.pokemon_helpers import create_owned_pokemon
from pokemon.models.storage import ensure_boxes
from utils.enhanced_evmenu import INVALID_INPUT_MSG
from utils.fusion import record_fusion

# ────── BUILD UNIVERSAL POKEMON LOOKUP ─────────────────────────────────────────

# Map lowercased raw key → key, and lowercased display name → key
POKEMON_KEY_LOOKUP: Dict[str, str] = {}
for key, mon in POKEDEX.items():
    POKEMON_KEY_LOOKUP[key.lower()] = key
    raw = mon.raw or {}
    display_name = raw.get("name", mon.name)
    POKEMON_KEY_LOOKUP[display_name.lower()] = key

# ────── CONSTANTS ──────────────────────────────────────────────────────────────

TYPES = [
    "Bug",
    "Dark",
    "Dragon",
    "Electric",
    "Fighting",
    "Fire",
    "Flying",
    "Ghost",
    "Grass",
    "Ground",
    "Ice",
    "Normal",
    "Poison",
    "Psychic",
    "Rock",
    "Steel",
    "Water",
]
NATURE_NAMES = list(NATURES_MAP.keys())
NATURE_LOOKUP = {n.lower(): n for n in NATURE_NAMES}

# Starter sets
# - STARTER_LOOKUP is assumed to map lowercased names/aliases → canonical key
# - We keep its key set for help text, and also precompute the *canonical key* set
STARTER_NAMES = set(STARTER_LOOKUP.keys())
STARTER_KEY_SET = set(STARTER_LOOKUP.values())

ABORT_INPUTS = {"abort", ".abort", "q", "quit", "exit"}
ABORT_OPTION = {"key": ("q", "quit", "exit"), "desc": "Abort", "goto": "node_abort"}


# ────── HELPERS ────────────────────────────────────────────────────────────────


def _invalid(caller):
    """Notify caller of invalid input."""
    # Use our shared, width-safe message from enhanced_evmenu for consistency
    caller.msg(INVALID_INPUT_MSG)


def format_columns(items, columns=4, indent=2):
    """Return items formatted into evenly spaced columns using spaces."""
    lines = []
    col_width = max((len(str(it)) for it in items), default=0) + 2
    for i in range(0, len(items), columns):
        row = items[i : i + columns]
        padded = [str(it).ljust(col_width) for it in row]
        lines.append(" " * indent + "".join(padded).rstrip())
    return "\n".join(lines)


def _normalize_species_key(maybe_key: str) -> str:
    """
    Resolve any user or display name into the canonical POKEDEX key.
    Falls back to the input so we can surface a helpful error if needed.
    """
    if not maybe_key:
        return ""
    return POKEMON_KEY_LOOKUP.get(maybe_key.lower(), maybe_key)


def _generate_instance(species_key: str, level: int):
    """Return a generated Pokémon instance or ``None`` if invalid, after normalization."""
    key = _normalize_species_key(species_key)
    # Extra guard: if it's not in POKEDEX, bail early with a clear signal
    if key not in POKEDEX:
        return None
    try:
        return generate_pokemon(key, level=level)
    except ValueError:
        return None


def _build_owned_pokemon(
    char,
    instance,
    ability: str,
    gender: str,
    nature: str,
    level: int,
):
    """Create an ``OwnedPokemon`` from a generated instance."""
    chosen_gender = gender or instance.gender
    chosen_nature = nature or instance.nature
    return create_owned_pokemon(
        instance.species.name,
        char.trainer,
        level,
        gender=chosen_gender,
        nature=chosen_nature,
        ability=ability or instance.ability,
        ivs=[
            instance.ivs.hp,
            instance.ivs.attack,
            instance.ivs.defense,
            instance.ivs.special_attack,
            instance.ivs.special_defense,
            instance.ivs.speed,
        ],
        evs=[0, 0, 0, 0, 0, 0],
    )


def _add_pokemon_to_storage(char, pokemon) -> None:
    """Place a Pokémon into the caller's active party."""
    storage = ensure_boxes(char.storage)
    storage.add_active_pokemon(pokemon)


def _create_starter(
    char,
    species_key: str,
    ability: str,
    gender: str,
    nature: str,
    level: int = 5,
):
    """Instantiate and store a starter Pokémon for the player."""
    normalized = _normalize_species_key(species_key)
    instance = _generate_instance(normalized, level)
    if not instance:
        char.msg(f'|rThat species does not exist|n (input="{species_key}", normalized="{normalized}").')
        return None

    pokemon = _build_owned_pokemon(char, instance, ability, gender, nature, level)
    _add_pokemon_to_storage(char, pokemon)
    return pokemon


# ────── MENU NODES ─────────────────────────────────────────────────────────────


def start(caller, raw_string):
    text = (
        "Welcome to Pokemon Fusion 2!\n"
        "A: Play a human trainer with a starter Pokémon.\n"
        "B: Play a Fusion without a starter.\n"
        "______________________________________________________________________________"
    )
    options = (
        {"key": ("A", "a"), "desc": "Human trainer", "goto": ("human_gender", {})},
        {
            "key": ("B", "b"),
            "desc": "Fusion (no starter)",
            "goto": ("fusion_gender", {}),
        },
        ABORT_OPTION,
        {"key": "_default", "goto": "_repeat", "exec": _invalid},
    )
    return text, options


def human_gender(caller, raw_string, **kwargs):
    caller.ndb.chargen = {"type": "human"}
    text = "Choose your gender: (M)ale or (F)emale"
    options = (
        {"key": ("M", "m"), "desc": "Male", "goto": ("human_type", {"gender": "Male"})},
        {
            "key": ("F", "f"),
            "desc": "Female",
            "goto": ("human_type", {"gender": "Female"}),
        },
        ABORT_OPTION,
        {"key": "_default", "goto": "_repeat", "exec": _invalid},
    )
    return text, options


def fusion_gender(caller, raw_string, **kwargs):
    caller.ndb.chargen = {"type": "fusion"}
    text = "Choose your gender: (M)ale or (F)emale"
    options = (
        {
            "key": ("M", "m"),
            "desc": "Male",
            "goto": ("fusion_species", {"gender": "Male"}),
        },
        {
            "key": ("F", "f"),
            "desc": "Female",
            "goto": ("fusion_species", {"gender": "Female"}),
        },
        ABORT_OPTION,
        {"key": "_default", "goto": "_repeat", "exec": _invalid},
    )
    return text, options


def human_type(caller, raw_string, **kwargs):
    # stash gender so we can re-enter with the same kwarg
    gender = kwargs["gender"]
    caller.ndb.chargen["player_gender"] = gender

    text = "Choose your favored Pokémon type:\n" + format_columns(TYPES) + "\n"

    # build all the real type-choices
    opts = [{"key": t.lower(), "desc": t, "goto": ("starter_species", {"type": t})} for t in TYPES]
    # abort stays the same
    opts.append(ABORT_OPTION)
    # on anything else, show our invalid-entry msg *and* go back into human_type
    opts.append(
        {
            "key": "_default",
            "exec": _invalid,
            "goto": ("human_type", {"gender": gender}),
        }
    )

    return text, tuple(opts)


def fusion_species(caller, raw_string, **kwargs):
    """Prompt for the player's fusion species."""
    if "gender" in kwargs:
        caller.ndb.chargen["player_gender"] = kwargs["gender"]
    text = "Enter the species for your fusion:"
    options = (
        {"key": "_default", "goto": _handle_fusion_species_input},
        ABORT_OPTION,
    )
    return text, options


def _handle_fusion_species_input(caller, raw_input, **kwargs):
    """Validate fusion species input and route to ability selection."""
    entry = (raw_input or "").strip()
    if entry.lower() in ABORT_INPUTS:
        return node_abort(caller)
    key = POKEMON_KEY_LOOKUP.get(entry.lower())
    if not key:
        caller.msg("|rInvalid species.|n Try again.")
        return "fusion_species"
    mon = POKEDEX[key]
    caller.ndb.chargen.update({"species_key": key, "species": mon.raw.get("name", mon.name)})
    return "fusion_ability"


def fusion_ability(caller, raw_string, **kwargs):
    """Display ability options for the chosen fusion species."""
    key = caller.ndb.chargen.get("species_key")
    if not key:
        caller.msg("|rInvalid state.|n Choose a species first.")
        return "fusion_species"

    mon = POKEDEX[key]
    abilities = mon.raw.get("abilities", {}) or {}

    numeric_keys = sorted(k for k in abilities if k.isdigit())

    lines = ["Choose one of the following abilities:"]
    for k in numeric_keys:
        lines.append(f"  {int(k) + 1}: {abilities[k]}")
    if "H" in abilities:
        lines.append(f"  H: {abilities['H']}")
    text = "\n".join(lines)

    mapping: dict[str, str] = {str(int(k) + 1): abilities[k] for k in numeric_keys}
    if "H" in abilities:
        mapping.update({"H": abilities["H"], "h": abilities["H"]})

    def _pick_ability(caller, raw, **k):
        choice = mapping.get((raw or "").strip())
        if not choice:
            _invalid(caller)
            caller.msg("|rInvalid ability.|n Pick |w1|n, |w2|n… or |wH|n.")
            return "fusion_ability", k
        k = dict(k)
        k["ability"] = choice
        return "fusion_nature", k

    options = [ABORT_OPTION, {"key": "_default", "goto": _pick_ability}]
    return text, tuple(options)


def fusion_nature(caller, raw_string, **kwargs):
    """Prompt for fusion nature."""
    if kwargs.get("ability"):
        caller.ndb.chargen["ability"] = kwargs["ability"]
    text = "Choose your fusion's nature:\n" + format_columns(NATURE_NAMES, columns=5) + "\n"
    options = (
        ABORT_OPTION,
        {"key": "_default", "goto": "fusion_confirm"},
    )
    return text, options


def starter_species(caller, raw_string, **kwargs):
    """Prompt for starter Pokémon species."""
    if "type" in kwargs:
        caller.ndb.chargen["favored_type"] = kwargs["type"]

    text = "Enter the species for your starter Pokémon\n" "(use 'starterlist' or 'pokemonlist' to view valid options):"
    options = [
        {
            "key": ("starterlist", "starters", "pokemonlist"),
            "exec": lambda cb: cb.msg("Starter Pokémon:\n" + ", ".join(get_starter_names())),
            "goto": (
                "starter_species",
                {"type": caller.ndb.chargen["favored_type"]},
            ),
        },
        ABORT_OPTION,
        {"key": "_default", "goto": _handle_starter_species_input},
    ]
    return text, tuple(options)


def _handle_starter_species_input(caller, raw_input, **kwargs):
    """Validate starter species input and show ability options."""
    entry = (raw_input or "").strip().lower()
    if entry in ABORT_INPUTS:
        return node_abort(caller)
    if entry in ("starterlist", "starters", "pokemonlist"):
        caller.msg("Starter Pokémon:\n" + ", ".join(get_starter_names()))
        return (
            "starter_species",
            {"type": caller.ndb.chargen.get("favored_type")},
        )
    # First, resolve whatever the player typed (display name or key) to a canonical dex key
    key = POKEMON_KEY_LOOKUP.get(entry)
    # If that fails, fall back to any alias in STARTER_LOOKUP (covers custom starter aliases)
    if not key:
        key = STARTER_LOOKUP.get(entry)

    # Must be a real Pokémon and also be allowed as a starter
    if not key or key not in POKEDEX or key not in STARTER_KEY_SET:
        _invalid(caller)
        caller.msg("|rInvalid starter species.|n Use |wstarterlist|n or |wpokemonlist|n.")
        return ("starter_species", {"type": caller.ndb.chargen.get("favored_type")})

    caller.ndb.chargen["species_key"] = key
    caller.ndb.chargen["species"] = POKEDEX[key].raw.get("name", key)
    return "starter_ability", {}


def starter_ability(caller, raw_string, **kwargs):
    """Display ability options for the chosen starter species."""
    key = caller.ndb.chargen.get("species_key")
    if not key:
        caller.msg("|rInvalid state.|n Choose a species first.")
        return (
            "starter_species",
            {"type": caller.ndb.chargen.get("favored_type")},
        )

    mon = POKEDEX[key]
    abilities = mon.raw.get("abilities", {}) or {}

    numeric_keys = sorted(k for k in abilities if k.isdigit())

    lines = ["Choose one of the following abilities:"]
    for k in numeric_keys:
        lines.append(f"  {int(k) + 1}: {abilities[k]}")
    if "H" in abilities:
        lines.append(f"  H: {abilities['H']}")
    text = "\n".join(lines)

    mapping: dict[str, str] = {str(int(k) + 1): abilities[k] for k in numeric_keys}
    if "H" in abilities:
        mapping.update({"H": abilities["H"], "h": abilities["H"]})

    def _pick_ability(caller, raw, **k):
        choice = mapping.get((raw or "").strip())
        if not choice:
            _invalid(caller)
            caller.msg("|rInvalid ability.|n Pick |w1|n, |w2|n… or |wH|n.")
            return "starter_ability", k
        k = dict(k)
        k["ability"] = choice
        return "starter_nature", k

    options = [ABORT_OPTION, {"key": "_default", "goto": _pick_ability}]
    return text, tuple(options)


def starter_nature(caller, raw_string, **kwargs):
    """Prompt for starter nature."""
    if kwargs.get("ability"):
        caller.ndb.chargen["ability"] = kwargs["ability"]
    text = "Choose your starter's nature:\n" + format_columns(NATURE_NAMES, columns=5) + "\n"
    options = (
        ABORT_OPTION,
        {"key": "_default", "goto": "starter_gender"},
    )
    return text, options


def starter_gender(caller, raw_string, **kwargs):
    """Prompt for the starter Pokémon's gender."""

    entry = raw_string.strip().lower()
    if entry in ABORT_INPUTS:
        return node_abort(caller)
    nature = NATURE_LOOKUP.get(entry)
    if not nature:
        _invalid(caller)
        caller.msg("|rInvalid nature.|n Try again.")
        return starter_nature(caller, "")
    caller.ndb.chargen["nature"] = nature

    key = caller.ndb.chargen.get("species_key")
    data = POKEDEX[key]
    ratio = getattr(data, "gender_ratio", None)
    gender = getattr(data, "gender", None)

    options: list[dict] = []
    valid: list[str] = []

    if gender in ("M", "F", "N"):
        desc = {"M": "Male", "F": "Female", "N": "Genderless"}[gender]
        valid.append(gender)
        options.append(
            {
                "key": (gender, gender.lower()),
                "desc": desc,
                "exec": lambda cb, g=gender: cb.ndb.chargen.__setitem__("starter_gender", g),
                "goto": ("starter_confirm", {"gender": gender}),
            }
        )
    else:
        m, f = (ratio.M, ratio.F) if ratio else (0.5, 0.5)
        if m > 0:
            valid.append("M")
            options.append(
                {
                    "key": ("M", "m"),
                    "desc": "Male",
                    "exec": lambda cb: cb.ndb.chargen.__setitem__("starter_gender", "M"),
                    "goto": ("starter_confirm", {"gender": "M"}),
                }
            )
        if f > 0:
            valid.append("F")
            options.append(
                {
                    "key": ("F", "f"),
                    "desc": "Female",
                    "exec": lambda cb: cb.ndb.chargen.__setitem__("starter_gender", "F"),
                    "goto": ("starter_confirm", {"gender": "F"}),
                }
            )
        if m == 0 and f == 0:
            valid.append("N")
            options.append(
                {
                    "key": ("N", "n"),
                    "desc": "Genderless",
                    "exec": lambda cb: cb.ndb.chargen.__setitem__("starter_gender", "N"),
                    "goto": ("starter_confirm", {"gender": "N"}),
                }
            )

    labels = {"M": "(M)ale", "F": "(F)emale", "N": "(N) Genderless"}
    choice_text = " or ".join(labels[v] for v in valid)
    text = f"Choose your starter's gender: {choice_text}"

    options += [
        ABORT_OPTION,
        {"key": "_default", "goto": "_repeat", "exec": _invalid},
    ]
    return text, tuple(options)


def starter_confirm(caller, raw_string, **kwargs):
    """Confirm the player's starter Pokémon selection."""
    data = caller.ndb.chargen or {}

    if kwargs.get("ability"):
        data["ability"] = kwargs["ability"]
    if kwargs.get("gender"):
        data["starter_gender"] = kwargs["gender"]

    species = data.get("species")
    ability = data.get("ability")
    nature = data.get("nature")
    gender = data.get("starter_gender")

    if not all([species, ability, nature, gender]):
        missing = [
            name
            for name, val in (
                ("species", species),
                ("ability", ability),
                ("nature", nature),
                ("gender", gender),
            )
            if not val
        ]
        caller.msg(f"|rStarter information incomplete|n ({', '.join(missing)} missing). Please choose again.")
        return starter_species(caller, "", type=data.get("favored_type"))

    if species and species.lower() in ABORT_INPUTS:
        return node_abort(caller)
    if species and species.lower() in ("starterlist", "starters", "pokemonlist"):
        caller.msg("Starter Pokémon:\n" + ", ".join(get_starter_names()))
        return starter_species(caller, "", type=data.get("favored_type"))
    # Validate using the canonical key to avoid display-name vs key mismatches
    if data.get("species_key") not in STARTER_KEY_SET:
        caller.msg("Invalid starter species.\nUse 'starterlist' or 'pokemonlist'.")
        return starter_species(caller, "", type=data.get("favored_type"))

    text = (
        f"You chose {species} "
        f"({gender}) with ability {ability} "
        f"and nature {nature} as your starter.\n"
        "Proceed? (Y/N)"
    )
    options = (
        {"key": ("Y", "y"), "desc": "Yes", "goto": "finish_human"},
        {
            "key": ("N", "n"),
            "desc": "No",
            "goto": ("starter_species", {"type": data.get("favored_type")}),
        },
        ABORT_OPTION,
        {"key": "_default", "goto": "_repeat", "exec": _invalid},
    )
    return text, options


def fusion_confirm(caller, raw_string, **kwargs):
    if kwargs.get("ability"):
        caller.ndb.chargen["ability"] = kwargs["ability"]

    entry = raw_string.strip().lower()
    if entry:
        if entry in ABORT_INPUTS:
            return node_abort(caller)
        nature = NATURE_LOOKUP.get(entry)
        if not nature:
            _invalid(caller)
            caller.msg("|rInvalid nature.|n Try again.")
            return fusion_nature(caller, "")
        caller.ndb.chargen["nature"] = nature

    species = caller.ndb.chargen["species"]
    if species.lower() in ABORT_INPUTS:
        return node_abort(caller)

    text = (
        f"You chose to fuse with {species} having ability {caller.ndb.chargen['ability']} "
        f"and nature {caller.ndb.chargen['nature']}.\nProceed? (Y/N)"
    )
    options = (
        {"key": ("Y", "y"), "desc": "Yes", "goto": "finish_fusion"},
        {"key": ("N", "n"), "desc": "No", "goto": "fusion_species"},
        ABORT_OPTION,
        {"key": "_default", "goto": "_repeat", "exec": _invalid},
    )
    return text, options


def finish_human(caller, raw_string):
    """Create the chosen starter Pokémon and finish human character creation."""
    data = caller.ndb.chargen or {}
    key = data.get("species_key")
    if not key:
        caller.msg("Error: No starter selected.")
        return None, None

    pk = _create_starter(
        caller,
        key,
        data.get("ability"),
        data.get("starter_gender"),
        data.get("nature"),
    )
    if not pk:
        caller.msg("Starter creation failed. Please try again.")
        return None, None
    caller.db.gender = data.get("player_gender")
    caller.db.favored_type = data.get("favored_type")
    caller.msg(f"You received {pk.name} with ability {pk.ability} and nature {pk.nature} as your starter!")
    caller.msg("Character generation complete.")
    return None, None


def finish_fusion(caller, raw_string):
    data = caller.ndb.chargen or {}
    caller.db.gender = data.get("player_gender")
    caller.db.fusion_species = data.get("species")
    fused = None
    species_key = data.get("species_key")
    trainer = getattr(caller, "trainer", None)
    if species_key and trainer:
        try:
            instance = _generate_instance(species_key, 5)
            if instance:
                gender_letter = (data.get("player_gender") or "N")[0].upper()
                fused = _build_owned_pokemon(
                    caller,
                    instance,
                    data.get("ability"),
                    gender_letter,
                    data.get("nature"),
                    5,
                )
                record_fusion(fused, trainer, fused, permanent=True)
                caller.db.fusion_id = getattr(fused, "unique_id", None)
                caller.db.level = getattr(fused, "level", None)
                caller.db.total_exp = getattr(fused, "total_exp", None)
        except Exception:  # pragma: no cover - defensive
            fused = None
    caller.db.fusion_ability = data.get("ability")
    caller.db.fusion_nature = data.get("nature")
    caller.msg(
        "You are now a fusion with "
        f"{data.get('species')} having ability {data.get('ability')} "
        f"and nature {data.get('nature')}"
        "."
    )
    caller.msg("Character generation complete.")
    return None, None


def node_abort(caller, raw_string=None):
    caller.msg("Character generation aborted.")
    return None, None
