"""Select AI actions from the shared legal candidates and existing move scorer."""

from __future__ import annotations

from .ai_profiles import AIDebugTrace, attach_ai_debug_trace, build_battle_ai_context
from .ai_scoring import candidate_band_for_context, choose_weighted_ai_move, fallback_scored_move, score_ai_moves
from .legal_actions import LegalActions


def select_ai_action(participant, pokemon, battle, *, logger, reserved=()):
    """Score legal moves and apply a bounded, visible-state reserve policy."""
    from .engine import MOVEDEX, get_raw

    context = build_battle_ai_context(participant, pokemon, battle)
    trace = AIDebugTrace(profile_key=context.profile.key, requested_profile_key=context.requested_profile_key,
                         actor_name=getattr(pokemon, "name", None), chosen_intent="safe_damage")
    legality = LegalActions(battle, participant, pokemon)
    actions = legality.moves()
    opponents = battle.opponents_of(participant)
    # Preserve the baseline enemy-only policy for ordinary attacks. Ally
    # strategy for moves such as Pollen Puff belongs to the later scorer work.
    actions = [action for action in actions
               if action.move.raw.get("target", "normal") not in {"normal", "any"}
               or any(action.target is opponent for opponent in opponents)]
    scored = []
    for action in actions:
        if action.move.key.lower() == "struggle":
            reason = "fallback_no_usable_moves" if getattr(pokemon, "moves", []) else "fallback_no_moves"
            score = fallback_scored_move(action.move, movedex=MOVEDEX, raw_getter=get_raw, reason=reason)
        else:
            candidates = score_ai_moves(context, [action.move], user=pokemon, target=action.target_pokemon,
                                        movedex=MOVEDEX, raw_getter=get_raw)
            score = candidates[0] if candidates else fallback_scored_move(action.move, movedex=MOVEDEX, raw_getter=get_raw)
        scored.append((action, score))
    selected = choose_weighted_ai_move([score for _, score in scored], rng=battle.rng, context=context)
    chosen = next((action for action, score in scored if score is selected), None)
    for action, score in scored:
        reasons = list(score.reasons)
        if score is selected and reasons[:1] == ["profile_weighted"]:
            reasons.insert(1, f"candidate_band_{candidate_band_for_context(context):.2f}")
        trace.add_action(score.key, score.score, *reasons)

    turn = getattr(battle, "turn_count", 0)
    last_switch = getattr(participant, "last_ai_switch_turn", -100)
    likelihood = min(1.0, max(0.0, context.profile.switch_likelihood))
    if chosen is not None and likelihood and turn - last_switch >= 3:
        current_score = max((score.score for _, score in scored), default=0)
        low_hp = getattr(pokemon, "hp", 1) <= getattr(pokemon, "max_hp", 1) / 3
        preferred = None
        preferred_score = -1
        for switch in legality.switches(reserved=reserved):
            reserve = switch.pokemon
            reserve_moves = [LegalActions(battle, participant, reserve)._move(move) for move in getattr(reserve, "moves", [])]
            scores = score_ai_moves(context, reserve_moves, user=reserve, target=chosen.target_pokemon,
                                    movedex=MOVEDEX, raw_getter=get_raw)
            quality = max((score.score for score in scores), default=0)
            healthy = getattr(reserve, "hp", 1) > getattr(reserve, "max_hp", 1) / 2
            improves = (current_score <= 8 and quality > current_score * 1.5 + 15)
            preserves = low_hp and healthy and quality >= current_score * 0.75
            trace.add_action("switch:" + getattr(reserve, "name", "Pokemon"), quality,
                             "legal_reserve", "visible_matchup" if improves else "preserve_self" if preserves else "insufficient_benefit")
            if (improves or preserves) and quality > preferred_score:
                preferred, preferred_score = switch, quality
        if preferred is not None and battle.rng.random() < likelihood:
            chosen = preferred
            trace.choose("switch:" + getattr(chosen.pokemon, "name", "Pokemon"), intent="preserve_self" if low_hp else "pivot")
    if chosen is not None:
        if chosen.move is not None:
            trace.target_name = getattr(chosen.target_pokemon, "name", None)
            trace.choose(chosen.move.key, intent="safe_damage")
            logger.info("%s chooses %s", participant.name, chosen.move.name)
        else:
            logger.info("%s chooses to switch to %s", participant.name, getattr(chosen.pokemon, "name", "Pokemon"))
    attach_ai_debug_trace(participant, battle, trace)
    return chosen
