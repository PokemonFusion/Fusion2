"""Bounded state and actual-hit accumulation for delayed move effects."""

from .effect_context import EffectContext


class BideState:
    """Accumulate actual opposing direct damage without restarting each action."""

    @staticmethod
    def before_move(user, move, battle):
        """Store for two actions, then release twice the observed damage."""
        state = getattr(user, "volatiles", {}).get("bide")
        if not isinstance(state, dict):
            battle.deduct_pp(user, move)
            battle.apply_volatile_status(user, "bide", source=user, effect=move)
            user.last_move = move
            battle.log_action(f"{user.name} began storing energy with Bide!")
            return False
        state["turns"] = state.get("turns", 1) + 1
        if state["turns"] < 3:
            battle.log_action(f"{user.name} is storing energy!")
            return False
        damage = state.get("damage", 0) * 2
        target = None
        position, slot = state.get("source_participant"), state.get("source_slot", 0)
        if isinstance(position, int) and 0 <= position < len(battle.participants):
            active = battle.participants[position].active
            target = active[slot] if isinstance(slot, int) and 0 <= slot < len(active) else None
        battle.remove_volatile(user, "bide")
        if damage > 0 and target is not None and target.hp > 0:
            from .engine import BattleMove, _apply_move_damage

            release = BattleMove("Bide", type="Normal", accuracy=True,
                                 damageCallback=lambda *args, **kwargs: damage,
                                 raw={"category": "Physical", "type": "Normal", "ignoreImmunity": True,
                                      "flags": {"contact": 1, "protect": 1}})
            if not getattr(target, "volatiles", {}).get("protect"):
                _apply_move_damage(user, target, release, battle)
            battle.log_action(f"{user.name} unleashed its stored Bide energy!")
        else:
            battle.log_action(f"{user.name}'s Bide failed without qualifying damage!")
        return False

    @staticmethod
    def record_hit(battle, target, source, move, damage):
        """Observe real HP loss after damage guards, before the next action."""
        if battle is None or damage <= 0:
            return
        if not any(key in getattr(target, "volatiles", {}) for key in ("bide", "shelltrap")):
            return
        if not callable(getattr(battle, "participant_for", None)) or not callable(getattr(battle, "opponents_of", None)):
            return
        owner, attacker = battle.participant_for(target), battle.participant_for(source)
        if owner is None or attacker not in battle.opponents_of(owner):
            return
        category = getattr(move, "category", None) or (getattr(move, "raw", {}) or {}).get("category")
        if category not in {"Physical", "Special"}:
            return
        state = getattr(target, "volatiles", {}).get("bide")
        if isinstance(state, dict):
            state["damage"] = state.get("damage", 0) + int(damage)
            state["source_participant"] = battle.participants.index(attacker)
            state["source_slot"] = next((index for index, pokemon in enumerate(attacker.active) if pokemon is source), 0)
        shell = getattr(target, "volatiles", {}).get("shelltrap")
        if isinstance(shell, dict) and category == "Physical":
            shell["triggered"] = True
