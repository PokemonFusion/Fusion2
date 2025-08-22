from evennia import Command


class CmdValidate(Command):
	"""Validate a character so they can enter the IC grid.

	Usage:
	  @validate <character>
	"""

	key = "@validate"
	locks = "cmd:perm(Validator)"
	help_category = "Admin"

	def func(self):
		caller = self.caller
		if not self.args:
			caller.msg("Usage: @validate <character>")
			return

		target = caller.search(self.args.strip(), global_search=True)
		if not target:
			return

		if not target.is_typeclass("typeclasses.characters.Character", exact=False):
			caller.msg("You can only validate characters.")
			return

		if not target.db.desc:
			caller.msg("Character must have a description before they can be validated.")
			return

		has_chargen_data = target.db.gender or target.db.favored_type or target.db.fusion_species
		if not has_chargen_data:
			caller.msg("Character must complete chargen before they can be validated.")
			return

		target.db.validated = True
		caller.msg(f"{target.key} has been validated.")
		if target != caller:
			target.msg("You have been validated and may now enter the IC grid.")
