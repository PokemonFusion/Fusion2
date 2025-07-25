from .functions.conditions_funcs import *

py_dict = {
    'brn': {
        'name': 'brn',
        'effectType': 'Status',
        'onStart': 'Brn.onStart',
        'onResidualOrder': 10,
        'onResidual': 'Brn.onResidual',
    },
    'par': {
        'name': 'par',
        'effectType': 'Status',
        'onStart': 'Par.onStart',
        'onModifySpePriority': -101,
        'onModifySpe': 'Par.onModifySpe',
        'onBeforeMovePriority': 1,
        'onBeforeMove': 'Par.onBeforeMove',
    },
    'slp': {
        'name': 'slp',
        'effectType': 'Status',
        'onStart': 'Slp.onStart',
        'onBeforeMovePriority': 10,
        'onBeforeMove': 'Slp.onBeforeMove',
    },
    'frz': {
        'name': 'frz',
        'effectType': 'Status',
        'onStart': 'Frz.onStart',
        'onBeforeMovePriority': 10,
        'onBeforeMove': 'Frz.onBeforeMove',
        'onModifyMove': 'Frz.onModifyMove',
        'onAfterMoveSecondary': 'Frz.onAfterMoveSecondary',
        'onDamagingHit': 'Frz.onDamagingHit',
    },
    'psn': {
        'name': 'psn',
        'effectType': 'Status',
        'onStart': 'Psn.onStart',
        'onResidualOrder': 9,
        'onResidual': 'Psn.onResidual',
    },
    'tox': {
        'name': 'tox',
        'effectType': 'Status',
        'onStart': 'Tox.onStart',
        'onSwitchIn': 'Tox.onSwitchIn',
        'onResidualOrder': 9,
        'onResidual': 'Tox.onResidual',
    },
    'confusion': {
        'name': 'confusion',
        'onStart': 'Confusion.onStart',
        'onEnd': 'Confusion.onEnd',
        'onBeforeMovePriority': 3,
        'onBeforeMove': 'Confusion.onBeforeMove',
    },
    'flinch': {
        'name': 'flinch',
        'duration': 1,
        'onBeforeMovePriority': 8,
        'onBeforeMove': 'Flinch.onBeforeMove',
    },
    'trapped': {
        'name': 'trapped',
        'noCopy': True,
        'onTrapPokemon': 'Trapped.onTrapPokemon',
        'onStart': 'Trapped.onStart',
    },
    'trapper': {
        'name': 'trapper',
        'noCopy': True,
    },
    'partiallytrapped': {
        'name': 'partiallytrapped',
        'duration': 5,
        'durationCallback': 'Partiallytrapped.durationCallback',
        'onStart': 'Partiallytrapped.onStart',
        'onResidualOrder': 13,
        'onResidual': 'Partiallytrapped.onResidual',
        'onEnd': 'Partiallytrapped.onEnd',
        'onTrapPokemon': 'Partiallytrapped.onTrapPokemon',
    },
    'lockedmove': {
        'name': 'lockedmove',
        'duration': 2,
        'onResidual': 'Lockedmove.onResidual',
        'onStart': 'Lockedmove.onStart',
        'onRestart': 'Lockedmove.onRestart',
        'onEnd': 'Lockedmove.onEnd',
        'onLockMove': 'Lockedmove.onLockMove',
    },
    'twoturnmove': {
        'name': 'twoturnmove',
        'duration': 2,
        'onStart': 'Twoturnmove.onStart',
        'onEnd': 'Twoturnmove.onEnd',
        'onLockMove': 'Twoturnmove.onLockMove',
        'onMoveAborted': 'Twoturnmove.onMoveAborted',
    },
    'choicelock': {
        'name': 'choicelock',
        'noCopy': True,
        'onStart': 'Choicelock.onStart',
        'onBeforeMove': 'Choicelock.onBeforeMove',
        'onDisableMove': 'Choicelock.onDisableMove',
    },
    'mustrecharge': {
        'name': 'mustrecharge',
        'duration': 2,
        'onBeforeMovePriority': 11,
        'onBeforeMove': 'Mustrecharge.onBeforeMove',
        'onStart': 'Mustrecharge.onStart',
        'onLockMove': 'recharge',
    },
    'futuremove': {
        'name': 'futuremove',
        'onStart': 'Futuremove.onStart',
        'onResidualOrder': 3,
        'onResidual': 'Futuremove.onResidual',
        'onEnd': 'Futuremove.onEnd',
    },
    'healreplacement': {
        'name': 'healreplacement',
        'onStart': 'Healreplacement.onStart',
        'onSwitchIn': 'Healreplacement.onSwitchIn',
    },
    'stall': {
        'name': 'stall',
        'duration': 2,
        'counterMax': 729,
        'onStart': 'Stall.onStart',
        'onStallMove': 'Stall.onStallMove',
        'onRestart': 'Stall.onRestart',
    },
    'gem': {
        'name': 'gem',
        'duration': 1,
        'affectsFainted': True,
        'onBasePowerPriority': 14,
        'onBasePower': 'Gem.onBasePower',
    },
    'raindance': {
        'name': 'RainDance',
        'effectType': 'Weather',
        'duration': 5,
        'durationCallback': 'Raindance.durationCallback',
        'onWeatherModifyDamage': 'Raindance.onWeatherModifyDamage',
        'onFieldStart': 'Raindance.onFieldStart',
        'onFieldResidualOrder': 1,
        'onFieldResidual': 'Raindance.onFieldResidual',
        'onFieldEnd': 'Raindance.onFieldEnd',
    },
    'primordialsea': {
        'name': 'PrimordialSea',
        'effectType': 'Weather',
        'duration': 0,
        'onTryMovePriority': 1,
        'onTryMove': 'Primordialsea.onTryMove',
        'onWeatherModifyDamage': 'Primordialsea.onWeatherModifyDamage',
        'onFieldStart': 'Primordialsea.onFieldStart',
        'onFieldResidualOrder': 1,
        'onFieldResidual': 'Primordialsea.onFieldResidual',
        'onFieldEnd': 'Primordialsea.onFieldEnd',
    },
    'sunnyday': {
        'name': 'SunnyDay',
        'effectType': 'Weather',
        'duration': 5,
        'durationCallback': 'Sunnyday.durationCallback',
        'onWeatherModifyDamage': 'Sunnyday.onWeatherModifyDamage',
        'onFieldStart': 'Sunnyday.onFieldStart',
        'onImmunity': 'Sunnyday.onImmunity',
        'onFieldResidualOrder': 1,
        'onFieldResidual': 'Sunnyday.onFieldResidual',
        'onFieldEnd': 'Sunnyday.onFieldEnd',
    },
    'desolateland': {
        'name': 'DesolateLand',
        'effectType': 'Weather',
        'duration': 0,
        'onTryMovePriority': 1,
        'onTryMove': 'Desolateland.onTryMove',
        'onWeatherModifyDamage': 'Desolateland.onWeatherModifyDamage',
        'onFieldStart': 'Desolateland.onFieldStart',
        'onImmunity': 'Desolateland.onImmunity',
        'onFieldResidualOrder': 1,
        'onFieldResidual': 'Desolateland.onFieldResidual',
        'onFieldEnd': 'Desolateland.onFieldEnd',
    },
    'sandstorm': {
        'name': 'Sandstorm',
        'effectType': 'Weather',
        'duration': 5,
        'durationCallback': 'Sandstorm.durationCallback',
        'onModifySpDPriority': 10,
        'onModifySpD': 'Sandstorm.onModifySpD',
        'onFieldStart': 'Sandstorm.onFieldStart',
        'onFieldResidualOrder': 1,
        'onFieldResidual': 'Sandstorm.onFieldResidual',
        'onWeather': 'Sandstorm.onWeather',
        'onFieldEnd': 'Sandstorm.onFieldEnd',
    },
    'hail': {
        'name': 'Hail',
        'effectType': 'Weather',
        'duration': 5,
        'durationCallback': 'Hail.durationCallback',
        'onFieldStart': 'Hail.onFieldStart',
        'onFieldResidualOrder': 1,
        'onFieldResidual': 'Hail.onFieldResidual',
        'onWeather': 'Hail.onWeather',
        'onFieldEnd': 'Hail.onFieldEnd',
    },
    'snowscape': {
        'name': 'Snowscape',
        'effectType': 'Weather',
        'duration': 5,
        'durationCallback': 'Snowscape.durationCallback',
        'onModifyDefPriority': 10,
        'onModifyDef': 'Snowscape.onModifyDef',
        'onFieldStart': 'Snowscape.onFieldStart',
        'onFieldResidualOrder': 1,
        'onFieldResidual': 'Snowscape.onFieldResidual',
        'onFieldEnd': 'Snowscape.onFieldEnd',
    },
    'deltastream': {
        'name': 'DeltaStream',
        'effectType': 'Weather',
        'duration': 0,
        'onEffectivenessPriority': -1,
        'onEffectiveness': 'Deltastream.onEffectiveness',
        'onFieldStart': 'Deltastream.onFieldStart',
        'onFieldResidualOrder': 1,
        'onFieldResidual': 'Deltastream.onFieldResidual',
        'onFieldEnd': 'Deltastream.onFieldEnd',
    },
    'dynamax': {
        'name': 'Dynamax',
        'noCopy': True,
        'onStart': 'Dynamax.onStart',
        'onTryAddVolatile': 'Dynamax.onTryAddVolatile',
        'onBeforeSwitchOutPriority': -1,
        'onBeforeSwitchOut': 'Dynamax.onBeforeSwitchOut',
        'onSourceModifyDamage': 'Dynamax.onSourceModifyDamage',
        'onDragOutPriority': 2,
        'onDragOut': 'Dynamax.onDragOut',
        'onResidualPriority': -100,
        'onResidual': 'Dynamax.onResidual',
        'onEnd': 'Dynamax.onEnd',
    },
    'commanded': {
        'name': 'Commanded',
        'noCopy': True,
        'onStart': 'Commanded.onStart',
        'onDragOutPriority': 2,
        'onDragOut': 'Commanded.onDragOut',
        'onTrapPokemonPriority': -11,
        'onTrapPokemon': 'Commanded.onTrapPokemon',
    },
    'commanding': {
        'name': 'Commanding',
        'noCopy': True,
        'onDragOutPriority': 2,
        'onDragOut': 'Commanding.onDragOut',
        'onTrapPokemonPriority': -11,
        'onTrapPokemon': 'Commanding.onTrapPokemon',
        'onInvulnerability': False,
        'onBeforeTurn': 'Commanding.onBeforeTurn',
    },
    'arceus': {
        'name': 'Arceus',
        'onTypePriority': 1,
        'onType': 'Arceus.onType',
    },
    'silvally': {
        'name': 'Silvally',
        'onTypePriority': 1,
        'onType': 'Silvally.onType',
    },
    'rolloutstorage': {
        'name': 'rolloutstorage',
        'duration': 2,
        'onBasePower': 'Rolloutstorage.onBasePower',
    },
}

