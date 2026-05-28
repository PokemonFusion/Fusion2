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
	Show Pokémon on user

	Usage:
	    showpokemononuser

	Shows the Pokémon currently on the user.
	"""

	key = "showpokemononuser"
	locks = "cmd:all()"
	help_category = "Pokemon"

	def func(self):
		self.caller.msg(f"Pokémon on {self.caller.key}:")
		self.caller.msg(self.caller.show_pokemon_on_user())


class CmdShowPokemonInStorage(Command):
	"""
	Show Pokémon in storage

	Usage:
	    showpokemoninstorage

	Shows the Pokémon currently in storage.
	"""

	key = "showpokemoninstorage"
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
	Get details of a Pokémon by ID

	Usage:
	    getpokemondetails <pokemon_id>

	Retrieves details of a Pokémon by its ID.
	"""

	key = "getpokemondetails"
	locks = "cmd:all()"
	help_category = "Pokemon"

	def func(self):
		if not self.args:
			self.caller.msg("Usage: getpokemondetails <pokemon_id>")
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
			self.caller.msg(
				move_not_found_message(move_name, f"Unknown move '{move_name}'.")
			)
			return

		attacker = POKEDEX.get(attacker_name.lower())
		target = POKEDEX.get(target_name.lower())
		if not attacker:
			self.caller.msg(
				pokemon_not_found_message(attacker_name, "Unknown attacker Pokemon name.")
			)
			return
		if not target:
			self.caller.msg(
				pokemon_not_found_message(target_name, "Unknown target Pokemon name.")
			)
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
	"""Choose your first Pokémon.

	Usage:
	  choosestarter <pokemon>
	"""

	key = "choosestarter"
	locks = "cmd:all()"
	help_category = "Pokemon"

	def func(self):
		if not self.args:
			self.caller.msg("Usage: choosestarter <pokemon>")
			return
		result = self.caller.choose_starter(self.args.strip())
		self.caller.msg(result)


class CmdSpoof(Command):
	"""
	Emit text to the current room without attribution.

	Usage:
	    spoof <message>
	    @emit[/here|/room] <message>
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
			self.caller.msg("Usage: nospoof [on|off]")
			return

		_set_db_bool(self.caller, "nospoof", new_value)
		status = "ON" if new_value else "OFF"
		self.caller.msg(f"NOSPOOF is now {status}.")


class CmdExpShare(Command):
	"""Toggle the EXP Share effect for your party.

	Usage:
	  +expshare
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
	"""Heal your Pokémon party at a Pokémon Center.

	Usage:
	  +heal
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
