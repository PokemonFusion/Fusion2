class Brn:
    def onResidual(self, *args, **kwargs):
        pass
    def onStart(self, *args, **kwargs):
        pass

class Par:
    def onBeforeMove(self, *args, **kwargs):
        pass
    def onModifySpe(self, *args, **kwargs):
        pass
    def onStart(self, *args, **kwargs):
        pass

class Slp:
    def onBeforeMove(self, *args, **kwargs):
        pass
    def onStart(self, *args, **kwargs):
        pass

class Frz:
    def onAfterMoveSecondary(self, *args, **kwargs):
        pass
    def onBeforeMove(self, *args, **kwargs):
        pass
    def onDamagingHit(self, *args, **kwargs):
        pass
    def onModifyMove(self, *args, **kwargs):
        pass
    def onStart(self, *args, **kwargs):
        pass

class Psn:
    def onResidual(self, *args, **kwargs):
        pass
    def onStart(self, *args, **kwargs):
        pass

class Tox:
    def onResidual(self, *args, **kwargs):
        pass
    def onStart(self, *args, **kwargs):
        pass
    def onSwitchIn(self, *args, **kwargs):
        pass

class Confusion:
    def onBeforeMove(self, *args, **kwargs):
        pass
    def onEnd(self, *args, **kwargs):
        pass
    def onStart(self, *args, **kwargs):
        pass

class Flinch:
    def onBeforeMove(self, *args, **kwargs):
        pass

class Trapped:
    def onStart(self, *args, **kwargs):
        pass
    def onTrapPokemon(self, *args, **kwargs):
        pass

class Trapper:
    pass

class Partiallytrapped:
    def durationCallback(self, *args, **kwargs):
        pass
    def onEnd(self, *args, **kwargs):
        pass
    def onResidual(self, *args, **kwargs):
        pass
    def onStart(self, *args, **kwargs):
        pass
    def onTrapPokemon(self, *args, **kwargs):
        pass

class Lockedmove:
    def onEnd(self, *args, **kwargs):
        pass
    def onLockMove(self, *args, **kwargs):
        pass
    def onResidual(self, *args, **kwargs):
        pass
    def onRestart(self, *args, **kwargs):
        pass
    def onStart(self, *args, **kwargs):
        pass

class Twoturnmove:
    def onEnd(self, *args, **kwargs):
        pass
    def onLockMove(self, *args, **kwargs):
        pass
    def onMoveAborted(self, *args, **kwargs):
        pass
    def onStart(self, *args, **kwargs):
        pass

class Choicelock:
    def onBeforeMove(self, *args, **kwargs):
        pass
    def onDisableMove(self, *args, **kwargs):
        pass
    def onStart(self, *args, **kwargs):
        pass

class Mustrecharge:
    def onBeforeMove(self, *args, **kwargs):
        pass
    def onStart(self, *args, **kwargs):
        pass

class Futuremove:
    def onEnd(self, *args, **kwargs):
        pass
    def onResidual(self, *args, **kwargs):
        pass
    def onStart(self, *args, **kwargs):
        pass

class Healreplacement:
    def onStart(self, *args, **kwargs):
        pass
    def onSwitchIn(self, *args, **kwargs):
        pass

class Stall:
    def onRestart(self, *args, **kwargs):
        pass
    def onStallMove(self, *args, **kwargs):
        pass
    def onStart(self, *args, **kwargs):
        pass

class Gem:
    def onBasePower(self, *args, **kwargs):
        pass

class Raindance:
    def durationCallback(self, *args, **kwargs):
        pass
    def onFieldEnd(self, *args, **kwargs):
        pass
    def onFieldResidual(self, *args, **kwargs):
        pass
    def onFieldStart(self, *args, **kwargs):
        pass
    def onWeatherModifyDamage(self, *args, **kwargs):
        pass

class Primordialsea:
    def onFieldEnd(self, *args, **kwargs):
        pass
    def onFieldResidual(self, *args, **kwargs):
        pass
    def onFieldStart(self, *args, **kwargs):
        pass
    def onTryMove(self, *args, **kwargs):
        pass
    def onWeatherModifyDamage(self, *args, **kwargs):
        pass

class Sunnyday:
    def durationCallback(self, *args, **kwargs):
        pass
    def onFieldEnd(self, *args, **kwargs):
        pass
    def onFieldResidual(self, *args, **kwargs):
        pass
    def onFieldStart(self, *args, **kwargs):
        pass
    def onImmunity(self, *args, **kwargs):
        pass
    def onWeatherModifyDamage(self, *args, **kwargs):
        pass

class Desolateland:
    def onFieldEnd(self, *args, **kwargs):
        pass
    def onFieldResidual(self, *args, **kwargs):
        pass
    def onFieldStart(self, *args, **kwargs):
        pass
    def onImmunity(self, *args, **kwargs):
        pass
    def onTryMove(self, *args, **kwargs):
        pass
    def onWeatherModifyDamage(self, *args, **kwargs):
        pass

class Sandstorm:
    def durationCallback(self, *args, **kwargs):
        pass
    def onFieldEnd(self, *args, **kwargs):
        pass
    def onFieldResidual(self, *args, **kwargs):
        pass
    def onFieldStart(self, *args, **kwargs):
        pass
    def onModifySpD(self, *args, **kwargs):
        pass
    def onWeather(self, *args, **kwargs):
        pass

class Hail:
    def durationCallback(self, *args, **kwargs):
        pass
    def onFieldEnd(self, *args, **kwargs):
        pass
    def onFieldResidual(self, *args, **kwargs):
        pass
    def onFieldStart(self, *args, **kwargs):
        pass
    def onWeather(self, *args, **kwargs):
        pass

class Snowscape:
    def durationCallback(self, *args, **kwargs):
        pass
    def onFieldEnd(self, *args, **kwargs):
        pass
    def onFieldResidual(self, *args, **kwargs):
        pass
    def onFieldStart(self, *args, **kwargs):
        pass
    def onModifyDef(self, *args, **kwargs):
        pass

class Deltastream:
    def onEffectiveness(self, *args, **kwargs):
        pass
    def onFieldEnd(self, *args, **kwargs):
        pass
    def onFieldResidual(self, *args, **kwargs):
        pass
    def onFieldStart(self, *args, **kwargs):
        pass

class Dynamax:
    def onDragOut(self, *args, **kwargs):
        pass
    def onEnd(self, *args, **kwargs):
        pass
    def onResidual(self, *args, **kwargs):
        pass
    def onSourceModifyDamage(self, *args, **kwargs):
        pass
    def onStart(self, *args, **kwargs):
        pass
    def onTryAddVolatile(self, *args, **kwargs):
        pass
    def onBeforeSwitchOut(self, *args, **kwargs):
        pass

class Commanded:
    def onDragOut(self, *args, **kwargs):
        pass
    def onStart(self, *args, **kwargs):
        pass
    def onTrapPokemon(self, *args, **kwargs):
        pass

class Commanding:
    def onBeforeTurn(self, *args, **kwargs):
        pass
    def onDragOut(self, *args, **kwargs):
        pass
    def onTrapPokemon(self, *args, **kwargs):
        pass

class Arceus:
    def onType(self, *args, **kwargs):
        pass

class Silvally:
    def onType(self, *args, **kwargs):
        pass

class Rolloutstorage:
    def onBasePower(self, *args, **kwargs):
        pass
