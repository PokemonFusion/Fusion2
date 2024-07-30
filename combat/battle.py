from .player import Player

class Battle:
    def __init__(self, options):
        self.format = options['format']
        self.p1 = Player(options['p1'])
        self.p2 = Player(options['p2'])
        self.turn = 0
        # Additional setup...

    def run_turn(self):
        self.turn += 1
        for pokemon in self.get_all_active():
            action = self.choose_action(pokemon)
            self.execute_action(pokemon, action)
        self.check_end_of_battle()

    def get_all_active(self):
        return self.p1.active + self.p2.active

    def choose_action(self, pokemon):
        # Logic to choose action
        pass

    def execute_action(self, pokemon, action):
        # Execute the chosen action
        pass

    def check_end_of_battle(self):
        # Check if the battle has ended
        pass
