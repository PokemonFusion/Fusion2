"""Per-target resolution for the two explicitly reviewed paid Z spread classes."""

from copy import copy, deepcopy

from .actions import Action, ActionType
from .active_slots import slot_for
from .z_moves import ZMoves


class ZSpread:
    """Keep target guards separate while paying/preventing/finishing one move."""

    @staticmethod
    def execute(battle, action):
        """Run actual target consumers, retaining one source after-move phase."""
        user, move = action.pokemon, action.move
        profile = move._z_profile
        targets = list(ZMoves.targets(battle, action.actor, user, profile))
        move.total_damage = 0
        move._primary_hit_successful = False
        move._stellar_boosts = {}
        parts = []
        for target in targets:
            if target.hp <= 0:
                continue
            selected = copy(move)
            selected.raw = deepcopy(move.raw)
            selected.flags = dict(move.flags)
            selected._z_spread_part = True
            selected._spread = len(targets) > 1
            participant = battle.participant_for(target)
            battle.use_move(
                Action(
                    action.actor,
                    ActionType.MOVE,
                    participant,
                    move=selected,
                    pokemon=user,
                    target_pokemon=target,
                    target_slot=slot_for(participant, target),
                ),
                called=True,
            )
            parts.append(selected)
            move.total_damage += getattr(selected, "total_damage", 0)
            move._primary_hit_successful |= bool(
                getattr(selected, "_primary_hit_successful", False)
            )
        target = targets[-1] if targets else None
        if profile.intrinsic == "soulblaze" and any(
            getattr(part, "total_damage", 0) > 0 and not getattr(part, "sheer_force_boosted", False)
            for part in parts
        ):
            from pokemon.utils.boosts import apply_boost

            before = dict(user.boosts)
            apply_boost(user, dict(profile.bonus), source=user, effect=move)
            battle.announce_stat_changes(user, before, user.boosts)
        if move._primary_hit_successful:
            battle.runEvent("AfterMoveSecondarySelf", user, target, move)
        battle.runEvent("AfterMove", user, target, move)
        battle.dispatcher.dispatch("after_move", user=user, target=target, move=move, battle=battle)
        user.tempvals["moved"] = True
        user.last_move, battle.last_move = move, move
        return parts
