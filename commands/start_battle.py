from evennia import Command
from combat.battle import Battle

class CmdStartBattle(Command):
    """
    Start a Pokémon battle.

    Usage:
      startbattle <opponent>

    This will initiate a Pokémon battle with the specified opponent.
    """
    key = "startbattle"
    locks = "cmd:all()"

    def func(self):
        caller = self.caller
        args = self.args.strip()

        if not args:
            caller.msg("You need to specify an opponent.")
            return

        opponent = caller.search(args)
        if not opponent:
            caller.msg("Could not find the opponent.")
            return

        # Example teams - replace with actual logic to get the teams
        options = {
            'format': 'standard',
            'p1': {
                'name': caller.key,
                'team': [
                    {'name': 'Pikachu'},
                    {'name': 'Bulbasaur'},
                ],
            },
            'p2': {
                'name': opponent.key,
                'team': [
                    {'name': 'Eevee'},
                    {'name': 'Squirtle'},
                ],
            }
        }

        battle = Battle(options)
        battle.run_turn()
        caller.msg("Battle started!")
        opponent.msg("You have been challenged to a battle by {}!".format(caller.key))
