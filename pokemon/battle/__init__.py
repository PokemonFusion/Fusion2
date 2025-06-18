"""Exports for the battle package with lazy loading."""

from importlib import import_module

__all__ = [
    "DamageResult",
    "damage_calc",
    "BattleData",
    "Team",
    "Pokemon",
    "TurnData",
    "Field",
    "Move",
    "calculateTurnorder",
    "execute_turn",
    "BattleInstance",
    "generate_trainer_pokemon",
    "generate_wild_pokemon",
]


_def_map = {
    "DamageResult": (".damage", "DamageResult"),
    "damage_calc": (".damage", "damage_calc"),
    "BattleData": (".battledata", "BattleData"),
    "Team": (".battledata", "Team"),
    "Pokemon": (".battledata", "Pokemon"),
    "TurnData": (".battledata", "TurnData"),
    "Field": (".battledata", "Field"),
    "Move": (".battledata", "Move"),
    "calculateTurnorder": (".turnorder", "calculateTurnorder"),
    "execute_turn": (".engine", "execute_turn"),
    "BattleInstance": (".battleinstance", "BattleInstance"),
    "generate_trainer_pokemon": (".battleinstance", "generate_trainer_pokemon"),
    "generate_wild_pokemon": (".battleinstance", "generate_wild_pokemon"),
}


def __getattr__(name):
    if name not in __all__:
        raise AttributeError(name)
    module_name, attr = _def_map[name]
    mod = import_module(module_name, __name__)
    return getattr(mod, attr)
