import logging

from evennia import Command

try:  # pragma: no cover - Evennia may be stubbed in tests
    from evennia.utils import logger as evennia_logger
except Exception:  # pragma: no cover
    evennia_logger = None

from utils.dex_suggestions import move_not_found_message, pokemon_not_found_message

log = logging.getLogger(__name__)


def _db_bool(obj, attr, default=False):
    """Return a boolean persistent db attribute from an Evennia-ish object."""
    db = getattr(obj, "db", None)
    if db is None:
        return default
    try:
        return bool(getattr(db, attr))
    except Exception:
        return default


def _set_db_bool(obj, attr, value):
    """Set a boolean persistent db attribute on an Evennia-ish object."""
    db = getattr(obj, "db", None)
    if db is not None:
        setattr(db, attr, bool(value))


def _attribute_bool(obj, attr, default=False):
    """Return a boolean AttributeHandler value from an Evennia-ish object."""
    attributes = getattr(obj, "attributes", None)
    get = getattr(attributes, "get", None)
    if not callable(get):
        return default
    try:
        return bool(get(attr, default=default))
    except TypeError:
        try:
            return bool(get(attr))
        except Exception:
            return default
    except Exception:
        return default


def _html_flagged(obj):
    """Return whether a recipient has opted into HTML-targeted emits."""
    return (
        _db_bool(obj, "html")
        or _db_bool(obj, "html_enabled")
        or _attribute_bool(obj, "html")
        or _attribute_bool(obj, "html_enabled")
    )


def _spoof_identity(caller):
    """Return the MUX-style NOSPOOF identity string for an emitter."""
    name = getattr(caller, "key", None) or getattr(caller, "name", None) or str(caller)
    dbref = getattr(caller, "id", None)
    return f"{name}(#{dbref})" if dbref is not None else str(name)


def _is_room(obj):
    """Best-effort room check that works in Evennia and lightweight tests."""
    if not obj:
        return False
    is_typeclass = getattr(obj, "is_typeclass", None)
    if callable(is_typeclass):
        for path in (
            "typeclasses.rooms.FusionRoom",
            "typeclasses.rooms.Room",
            "evennia.objects.objects.DefaultRoom",
        ):
            try:
                if is_typeclass(path, inherit=True):
                    return True
            except TypeError:
                if is_typeclass(path):
                    return True
            except Exception:
                continue
    return obj.__class__.__name__.lower().endswith("room")


def _outer_room(obj):
    """Walk outward from an object/container until a room is found."""
    current = obj
    seen = set()
    while current and id(current) not in seen:
        seen.add(id(current))
        if _is_room(current):
            return current
        current = getattr(current, "location", None)
    return obj


def _emit_to_location(caller, location, message, html_only=False):
    """Emit to a location, showing attribution only to NOSPOOF recipients."""
    if not location:
        caller.msg("You have no location to spoof from.")
        return

    identity = _spoof_identity(caller)
    attributed = f"[{identity}] {message}"
    for receiver in list(getattr(location, "contents", []) or []):
        if html_only and not _html_flagged(receiver):
            continue
        msg = getattr(receiver, "msg", None)
        if not callable(msg):
            continue
        msg(attributed if _db_bool(receiver, "nospoof") else message)

    room_name = getattr(location, "key", None) or getattr(location, "name", None) or location
    audit = f"SPOOF {identity} in {room_name}: {message}"
    if evennia_logger and hasattr(evennia_logger, "log_info"):
        evennia_logger.log_info(audit)
    else:
        log.info(audit)


def heal_party(char):
    """Heal all active Pokemon for the given character."""
    storage = getattr(char, "storage", None)
    if not storage:
        return
    party = storage.get_party()
    for mon in party:
        if hasattr(mon, "heal"):
            mon.heal()


class CmdShowPokemonOnUser(Command):
    """
    Show your current party.

    Usage:
        +party/raw

    Examples:
        +party/raw

    Notes:
        Use +party for the polished party display. This command keeps the
        older raw party output available for compatibility.
    """

    key = "+party/raw"
    aliases = ["showpokemononuser"]
    locks = "cmd:all()"
    help_category = "Pokemon"

    def func(self):
        self.caller.msg(f"Pokémon on {self.caller.key}:")
        self.caller.msg(self.caller.show_pokemon_on_user())


class CmdShowPokemonInStorage(Command):
    """
    Show all Pokemon currently in storage.

    Usage:
        +box/all

    Examples:
        +box/all

    Notes:
        Use +box <number> for a specific storage box.
    """

    key = "+box/all"
    aliases = ["showpokemoninstorage"]
    locks = "cmd:all()"
    help_category = "Pokemon"

    def func(self):
        self.caller.msg(f"Pokémon in storage for {self.caller.key}:")
        self.caller.msg(self.caller.show_pokemon_in_storage())


class CmdAddPokemonToUser(Command):
    """
    Add a Pokémon to the user

    Usage:
        @addpokemontouser <name> <level> <type>

    Adds a Pokémon to the user's active Pokémon list.
    """

    key = "@addpokemontouser"
    aliases = ["addpokemontouser"]
    locks = "cmd:perm(Builder)"
    help_category = "Admin"

    def func(self):
        if not self.args:
            self.caller.msg("Usage: @addpokemontouser <name> <level> <type>")
            return
        try:
            name, level, type_ = self.args.split()
            level = int(level)
            self.caller.add_pokemon_to_user(name, level, type_)
            self.caller.msg(f"Added {name} (Level {level}, Type: {type_}) to your active Pokémon.")
        except ValueError:
            self.caller.msg("Usage: @addpokemontouser <name> <level> <type>")


class CmdAddPokemonToStorage(Command):
    """
    Add a Pokémon to the storage

    Usage:
        @addpokemontostorage <name> <level> <type>

    Adds a Pokémon to the user's storage.
    """

    key = "@addpokemontostorage"
    aliases = ["addpokemontostorage"]
    locks = "cmd:perm(Builder)"
    help_category = "Admin"

    def func(self):
        if not self.args:
            self.caller.msg("Usage: @addpokemontostorage <name> <level> <type>")
            return
        try:
            name, level, type_ = self.args.split()
            level = int(level)
            self.caller.add_pokemon_to_storage(name, level, type_)
            self.caller.msg(f"Added {name} (Level {level}, Type: {type_}) to your storage.")
        except ValueError:
            self.caller.msg("Usage: @addpokemontostorage <name> <level> <type>")


class CmdGetPokemonDetails(Command):
    """
    Show details for one of your Pokemon by unique id.

    Usage:
        +pokemon <pokemon_id>

    Examples:
        +pokemon abc123

    Notes:
        Use +party or +box first if you need to find the id.
    """

    key = "+pokemon"
    aliases = ["getpokemondetails"]
    locks = "cmd:all()"
    help_category = "Pokemon"

    def func(self):
        if not self.args:
            self.caller.msg("Usage: +pokemon <pokemon_id>")
            return
        pokemon_id = self.args.strip()
        pokemon = self.caller.get_pokemon_by_id(pokemon_id)
        if pokemon:
            self.caller.msg(str(pokemon))
        else:
            self.caller.msg(f"No Pokémon found with ID {pokemon_id}.")


class CmdUseMove(Command):
    """Use a Pokémon move in a simple battle simulation.

    Usage:
      @usemove <move> <attacker> <target>
    """

    key = "@usemove"
    aliases = ["usemove"]
    locks = "cmd:perm(Builder)"
    help_category = "Admin"

    def func(self):
        if not self.args:
            self.caller.msg("Usage: @usemove <move> <attacker> <target>")
            return
        try:
            move_name, attacker_name, target_name = self.args.split()
        except ValueError:
            self.caller.msg("Usage: @usemove <move> <attacker> <target>")
            return

        inst = getattr(self.caller.ndb, "battle_instance", None)
        if inst:
            inst.queue_move(move_name, caller=self.caller)
            return

        import copy

        from pokemon.battle import damage_calc
        from pokemon.dex import MOVEDEX, POKEDEX, Move

        # MOVEDEX keys are stored in lowercase
        movedata = MOVEDEX.get(move_name.lower())
        if not movedata:
            self.caller.msg(move_not_found_message(move_name, f"Unknown move '{move_name}'."))
            return

        attacker = POKEDEX.get(attacker_name.lower())
        target = POKEDEX.get(target_name.lower())
        if not attacker:
            self.caller.msg(pokemon_not_found_message(attacker_name, "Unknown attacker Pokemon name."))
            return
        if not target:
            self.caller.msg(pokemon_not_found_message(target_name, "Unknown target Pokemon name."))
            return

        move = Move.from_dict(move_name.capitalize(), movedata)
        att = copy.deepcopy(attacker)
        tgt = copy.deepcopy(target)
        att.current_hp = att.base_stats.hp
        tgt.current_hp = tgt.base_stats.hp

        result = damage_calc(att, tgt, move)
        total_dmg = sum(result.debug.get("damage", []))
        tgt.current_hp = max(0, tgt.current_hp - total_dmg)
        if tgt.current_hp == 0:
            result.fainted.append(tgt.name)

        out = result.text
        out.append(f"{tgt.name} has {tgt.current_hp} HP remaining.")
        if getattr(tgt, "status", None):
            out.append(f"{tgt.name} is now {tgt.status}.")
        self.caller.msg("\n".join(out))


class CmdChooseStarter(Command):
    """Open or resume starter selection through chargen.

    Usage:
      +starter

    Examples:
      +starter

    Notes:
      Direct +starter <pokemon> creation is deprecated. Starter selection now
      happens through the chargen menu because it includes ability, nature, and
      gender choices.
    """

    key = "+starter"
    aliases = ["choosestarter"]
    locks = "cmd:all()"
    help_category = "Pokemon"

    def func(self):
        caller = self.caller
        requested_species = (self.args or "").strip()
        if requested_species:
            from pokemon.data.starters import resolve_starter_key

            if not resolve_starter_key(requested_species):
                caller.msg("That is not a valid starter species. Use |w+starters|n to list valid starters.")
            else:
                caller.msg(
                    "Direct starter creation with |w+starter <pokemon>|n is deprecated. "
                    "Use |w+starter|n with no Pokemon name to open or resume chargen starter selection."
                )
            return

        if _db_bool(caller, "validated", False):
            caller.msg("You have already completed chargen; starter selection is closed.")
            return

        if _caller_has_party_pokemon(caller):
            caller.msg("You already have a starter Pokemon.")
            return

        target = _starter_menu_target(caller)
        if target is None:
            return
        startnode, raw_input, kwargs = target
        if startnode == "start":
            caller.msg("Starting chargen. Starter selection now happens inside this menu.")
        else:
            caller.msg("Opening chargen starter selection.")

        from menus import chargen as chargen_menu
        from utils.enhanced_evmenu import EnhancedEvMenu

        EnhancedEvMenu(
            caller,
            chargen_menu,
            startnode=startnode,
            startnode_input=(raw_input, kwargs),
            cmd_on_exit=None,
            on_abort=lambda menu_caller: menu_caller.msg("Character generation aborted."),
            numbered_options=False,
            show_options=False,
        )


def _caller_has_party_pokemon(caller) -> bool:
    storage = getattr(caller, "storage", None)
    has_party = getattr(storage, "has_party_pokemon", None)
    if callable(has_party):
        return bool(has_party())
    get_party = getattr(storage, "get_party", None)
    if callable(get_party):
        return bool(get_party())
    return False


def _starter_menu_target(caller):
    data = getattr(getattr(caller, "ndb", None), "chargen", None)
    if not isinstance(data, dict) or not data:
        return "start", "", {}

    chargen_type = data.get("type")
    if chargen_type == "fusion":
        caller.msg("Fusion chargen does not include a starter Pokemon.")
        return None
    if chargen_type != "human":
        return "start", "", {}

    player_gender = data.get("player_gender")
    if not player_gender:
        return "human_gender", "", {}

    favored_type = data.get("favored_type")
    if not favored_type:
        return "human_type", "", {"gender": player_gender}

    if not data.get("species_key"):
        return "starter_species", "", {"type": favored_type}

    if not data.get("ability"):
        return "starter_ability", "", {}

    if not data.get("nature"):
        return "starter_nature", "", {}

    if not data.get("starter_gender"):
        return "starter_gender", data.get("nature", ""), {}

    return "starter_confirm", "", {"gender": data.get("starter_gender")}


class CmdSpoof(Command):
    """
    Emit text to the current room without attribution.

    Usage:
        spoof <message>
        @emit[/here||/room] <message>

    Examples:
        spoof A sign flashes.
        @emit/here A bell rings.

    Notes:
        Players with NOSPOOF enabled will see the source of raw emits.
    """

    key = "spoof"
    aliases = ["@emit"]
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        """Send the raw message, with attribution for NOSPOOF recipients."""
        message = self.args.strip()
        if not message:
            self.caller.msg("Usage: spoof <message>")
            return
        location = self.caller.location
        if not location:
            self.caller.msg("You have no location to spoof from.")
            return
        switches = {switch.lower() for switch in getattr(self, "switches", [])}
        html_only = "html" in switches
        targets = []
        if not (switches & {"here", "room"}) or "here" in switches:
            targets.append(location)
        if "room" in switches:
            targets.append(_outer_room(location))

        seen = set()
        for target in targets:
            if id(target) in seen:
                continue
            seen.add(id(target))
            _emit_to_location(self.caller, target, message, html_only=html_only)


class CmdNoSpoof(Command):
    """Toggle whether raw emits show their source.

    Usage:
      nospoof
      nospoof on
      nospoof off

    Examples:
      nospoof on

    Notes:
      This only affects what you see when someone uses raw emit-style commands.
    """

    key = "nospoof"
    aliases = ["@nospoof", "+nospoof"]
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        """Toggle or set the caller's NOSPOOF preference."""
        arg = (self.args or "").strip().lower()
        current = _db_bool(self.caller, "nospoof")
        if not arg:
            new_value = not current
        elif arg in {"on", "yes", "true", "1"}:
            new_value = True
        elif arg in {"off", "no", "false", "0"}:
            new_value = False
        else:
            self.caller.msg("Usage: nospoof [on||off]")
            return

        _set_db_bool(self.caller, "nospoof", new_value)
        status = "ON" if new_value else "OFF"
        self.caller.msg(f"NOSPOOF is now {status}.")


class CmdExpShare(Command):
    """Toggle the EXP Share effect for your party.

    Usage:
      +expshare

    Examples:
      +expshare

    Notes:
      Running the command again turns EXP Share back off.
    """

    key = "+expshare"
    locks = "cmd:all()"
    help_category = "Pokemon"

    def func(self):
        current = bool(self.caller.db.exp_share)
        if current:
            self.caller.db.exp_share = False
            self.caller.msg("EXP Share is turned OFF.")
        else:
            self.caller.db.exp_share = True
            self.caller.msg("EXP Share is turned ON.")


class CmdHeal(Command):
    """Heal your Pokemon party at a Pokemon Center.

    Usage:
      +heal

    Examples:
      +heal

    Notes:
      You must be in a room marked as a Pokemon Center.
    """

    key = "+heal"
    locks = "cmd:all()"
    help_category = "Pokemon"

    def func(self):
        location = self.caller.location
        if not (location and location.db.is_pokemon_center):
            self.caller.msg("You must be at a Pokémon Center to heal.")
            return
        heal_party(self.caller)
        self.caller.msg("Your Pokémon have been fully healed.")


class CmdAdminHeal(Command):
    """Heal another player's Pokémon party.

    Usage:
      @adminheal [<player>]
    """

    key = "@adminheal"
    aliases = ["+adminheal"]
    locks = "cmd:perm(Wizards)"
    help_category = "Admin"

    def parse(self):
        self.target_name = self.args.strip()

    def func(self):
        target = self.caller
        if self.target_name:
            target = self.caller.search(self.target_name, global_search=True)
            if not target:
                return
        heal_party(target)
        if target.location:
            target.location.msg_contents(f"{self.caller.key} heals {target.key}'s Pokémon party.")
        self.caller.msg(f"{target.key}'s Pokémon have been healed.")
        if target != self.caller:
            target.msg("Your Pokémon have been healed by an admin.")
