class Return:
    def basePowerCallback(self, pokemon):
        '''
        Function originally from TypeScript for Return.
        '''
        # return Math.floor((pokemon.happiness * 10) / 25) || 1;
        pass

class Acrobatics:
    def basePowerCallback(self, pokemon, target, move):
        '''
        Function originally from TypeScript for Acrobatics.
        '''
        # if (!pokemon.item) {
        #     this.debug("BP doubled for no item");
        #     return move.basePower * 2;
        # }
        # return move.basePower;
        pass

class CrushGrip:
    def basePowerCallback(self, pokemon, target):
        '''
        Function originally from TypeScript for CrushGrip.
        '''
        # const hp = target.hp;
        # const maxHP = target.maxhp;
        # const bp = Math.floor(Math.floor((120 * (100 * Math.floor(hp * 4096 / maxHP)) + 2048 - 1) / 4096) / 100) || 1;
        # this.debug('BP for ' + hp + '/' + maxHP + " HP: " + bp);
        # return bp;
        pass
