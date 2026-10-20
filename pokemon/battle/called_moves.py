"""Execute internally called or reflected moves through the real move pipeline."""

import copy

from .effect_context import EffectContext


class CalledMoveExecutor:
    """Keep target selection, recursion bounds and PP ownership explicit."""

    def __init__(self, battle):
        self.battle = battle

    def execute(self, user, selected, target=None, *, power_multiplier=1.0, reflected=False,
                spend_pp=False):
        """Execute a fresh action; instructed repeats spend their learned PP."""
        from pokemon.dex.functions.moves.damage_moves import _battle_move_from_name
        from .actions import Action, ActionType

        depth = getattr(self.battle, "_called_move_depth", 0)
        if user is None or depth >= 8:
            return False
        name = selected if isinstance(selected, str) else getattr(selected, "name", "")
        move = _battle_move_from_name(name)
        if move is None:
            return False
        if spend_pp:
            from .copied_moves import BattleCopyState

            index = BattleCopyState.temporary_index(user, move)
            current = getattr(user.moves[index], "pp", None) if index is not None else next(
                (remaining for _, learned, remaining, _, _ in self.battle._move_pp_states(user)
                 if EffectContext.key(learned) == EffectContext.key(move)), getattr(selected, "pp", None))
            if current is not None and current <= 0:
                return False
        move._called_use = not spend_pp
        move.has_bounced = reflected
        if power_multiplier != 1:
            move.power = int(move.power * power_multiplier)
            move.raw = copy.deepcopy(move.raw)
            move.raw["basePower"] = move.power
        participant = self.battle.participant_for(user)
        if participant is None:
            return False
        target_class = move.raw.get("target", "normal")
        if target_class in {"self", "allySide", "allyTeam", "allies"}:
            target = user
        elif target is None or target is user:
            target = next((pokemon for part in self.battle.opponents_of(participant)
                           for pokemon in part.active if pokemon.hp > 0), None)
        if target is None:
            return False
        self.battle._called_move_depth = depth + 1
        try:
            self.battle.use_move(Action(participant, ActionType.MOVE,
                                       self.battle.participant_for(target), move,
                                       pokemon=user, target_pokemon=target), called=not spend_pp)
            self.battle.called_moves = list(getattr(self.battle, "called_moves", [])) + [move.name]
            user.tempvals["called_move"] = move.name
            return bool(move._primary_hit_successful)
        finally:
            self.battle._called_move_depth = depth

    def reflect(self, user, target, move):
        """Reflect only eligible moves, with a per-copy recursion guard."""
        if (target is None or target is user or getattr(move, "has_bounced", False)
                or not move.raw.get("flags", {}).get("reflectable")):
            return False
        ability = EffectContext.key(EffectContext.ability(target))
        ignores = self.battle._move_ignores_target_ability(user, target, move)
        rebound = ability == "rebound" and getattr(target, "tempvals", {}).get("entry_action_turn") == self.battle.turn_count
        if not (((ability == "magicbounce" or rebound) and not ignores)
                or "magiccoat" in getattr(target, "volatiles", {})):
            return False
        self.execute(target, move, user, reflected=True)
        self.battle.log_action(f"{target.name} reflected {move.name}!")
        return True
