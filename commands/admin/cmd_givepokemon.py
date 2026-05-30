from evennia import Command

import menus.give_pokemon as give_pokemon
from utils.dex_suggestions import is_species_not_found_error, species_not_found_message
from utils.enhanced_evmenu import EnhancedEvMenu


class CmdGivePokemon(Command):
	"""Give a Pokemon to a character for debugging.

	Usage:
	  @givepokemon <character>
	  @givepokemon <character>=<species>[, level]
	"""

	key = "@givepokemon"
	locks = "cmd:perm(Builder)"
	help_category = "Admin"

	def func(self):
		"""Launch the give pokemon menu or quick-grant a generated Pokemon."""
		if not self.args:
			self.caller.msg("Usage: @givepokemon <character>")
			return

		target_expr = self.args
		quick_spec = ""
		if "=" in self.args:
			target_expr, quick_spec = [part.strip() for part in self.args.split("=", 1)]

		target = self.caller.search(target_expr.strip(), global_search=True)
		if not target:
			return
		if not target.is_typeclass("evennia.objects.objects.DefaultCharacter", exact=False):
			self.caller.msg("You can only give Pokemon to characters.")
			return

		if quick_spec:
			parts = [part.strip() for part in quick_spec.split(",") if part.strip()]
			if not parts:
				self.caller.msg("Usage: @givepokemon <character>=<species>[, level]")
				return
			species = parts[0]
			try:
				level = int(parts[1]) if len(parts) > 1 else 5
			except ValueError:
				self.caller.msg("Level must be a number.")
				return
			from utils.pokemon_utils import grant_generated_pokemon

			try:
				grant_generated_pokemon(target, species, max(1, level), caller=self.caller)
			except ValueError as err:
				if is_species_not_found_error(err):
					self.caller.msg(species_not_found_message(species))
				else:
					self.caller.msg(str(err))
			return

		EnhancedEvMenu(
			self.caller,
			give_pokemon,
			startnode="node_start",
			startnode_input=(None, {"target": target}),
		)
