"""Resolve the bounded ordinary Parental Bond class as two distinct hits."""


class ParentalBondAttack:
    """Keep prevention, action and PP outside this per-hit boundary."""

    @staticmethod
    def eligible(move):
        """Defer custom/charged/spread/recoil classes instead of replaying callbacks."""
        raw = getattr(move, "raw", {}) or {}
        flags = getattr(move, "flags", None) or raw.get("flags", {})
        return bool(
            move
            and move.category != "Status"
            and str(getattr(move, "key", None) or getattr(move, "id", "")).lower() != "struggle"
            and not (getattr(move, "multihit", None) or raw.get("multihit"))
            and raw.get("target", "normal") in {"normal", "adjacentFoe", "any"}
            and not any(
                flags.get(key) for key in ("noparentalbond", "charge", "recharge", "futuremove")
            )
            and not any(
                raw.get(key)
                for key in (
                    "onHit",
                    "onAfterHit",
                    "onAfterMove",
                    "onAfterMoveSecondary",
                    "onAfterMoveSecondarySelf",
                    "basePowerCallback",
                    "damageCallback",
                    "selfdestruct",
                    "recoil",
                    "drain",
                    "forceSwitch",
                    "selfSwitch",
                    "ohko",
                )
            )
            and not getattr(move, "isZ", False)
            and not getattr(move, "isMax", False)
        )

    @staticmethod
    def execute(battle, user, target, move):
        """Execute two independently applied hits, followed by one after-move phase."""
        from .engine import _apply_move_damage, _MoveResultState

        before_user, before_target = _MoveResultState.capture(user), _MoveResultState.capture(
            target
        )
        saved_accuracy, saved_multihit = move.accuracy, move.multihit
        # Each damage call is one hit. The second hit's formula multiplier is
        # applied after normal modifiers; fixed damage retains its own rule.
        move.multihit = 1
        hits = 0
        try:
            for number in (1, 2):
                if user.hp <= 0 or target.hp <= 0:
                    break
                move.parental_bond_hit = number
                move.hit = number
                if number == 2:
                    move.accuracy = True
                sub = getattr(target, "volatiles", {}).get("substitute")
                flags = getattr(move, "flags", {})
                bypass = (
                    move.raw.get("bypassSub")
                    or flags.get("bypasssub")
                    or getattr(move, "infiltrates", False)
                )
                if sub and not bypass:
                    result = _apply_move_damage(user, target, move, battle, update_hp=False)
                    damage = sum(result.debug.get("damage", []))
                    sub_hp = sub.get("hp", 0) if isinstance(sub, dict) else damage
                    actual = min(max(0, sub_hp), max(0, damage))
                    if actual:
                        move.total_damage += actual
                        if sub_hp <= damage:
                            target.volatiles.pop("substitute", None)
                        elif isinstance(sub, dict):
                            sub["hp"] = sub_hp - damage
                        battle.runEvent("AfterSubDamage", target, user, move, actual)
                    move._primary_hit_successful = damage > 0
                else:
                    battle._do_move(user, target, move)
                if not getattr(move, "_primary_hit_successful", False):
                    break
                hits += 1
        finally:
            move.accuracy = saved_accuracy
            move.multihit = saved_multihit
        move._primary_hit_successful = hits > 0
        battle.log_action(f"{user.name} hit {hits} times!")
        battle._announce_move_result(user, target, move, before_user, before_target)
        for participant in battle.participants:
            for pokemon in participant.active:
                if pokemon.hp > 0:
                    battle.dispatcher.dispatch("update", pokemon=pokemon, battle=battle)
        battle.runEvent("AfterMoveSecondary", target, user, move)
        battle.runEvent("AfterMoveSecondarySelf", user, target, move)
        battle.runEvent("AfterMove", user, target, move)
        battle.dispatcher.dispatch("after_move", user=user, target=target, move=move, battle=battle)
        user.tempvals["moved"] = True
        battle.last_move = move
