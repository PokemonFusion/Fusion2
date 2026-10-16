"""Select AI actions from the shared legal candidates and existing move scorer."""

from __future__ import annotations

from .ai_action_scoring import AIActionScorer
from .ai_profiles import AIDebugTrace, attach_ai_debug_trace, build_battle_ai_context
from .ai_scoring import candidate_band_for_context, choose_weighted_ai_move, score_ai_moves
from .legal_actions import LegalActions


def select_ai_action(participant, pokemon, battle, *, logger, reserved=(), planned=()):
    """Score legal moves and apply a bounded, visible-state reserve policy."""
    from .engine import MOVEDEX, get_raw

    context = build_battle_ai_context(participant, pokemon, battle)
    trace = AIDebugTrace(profile_key=context.profile.key, requested_profile_key=context.requested_profile_key,
                         actor_name=getattr(pokemon, "name", None), chosen_intent="safe_damage")
    legality = LegalActions(battle, participant, pokemon)
    scorer = AIActionScorer(context, battle, participant, pokemon, movedex=MOVEDEX, raw_getter=get_raw, planned=planned)
    assessed = scorer.assess(legality.moves())
    selected = choose_weighted_ai_move([entry.scored for entry in assessed], rng=battle.rng, context=context)
    decision = next((entry for entry in assessed if entry.scored is selected), None)
    chosen = decision.action if decision else None
    for entry in assessed:
        action, score = entry.action, entry.scored
        reasons = list(score.reasons)
        if score is selected and reasons[:1] == ["profile_weighted"]:
            reasons.insert(1, f"candidate_band_{candidate_band_for_context(context):.2f}")
        targets = entry.targets if action.move.raw.get("target") in legality.automatic_targets else (action.target_pokemon,)
        trace.add_action(score.key, score.score, *reasons, target=", ".join(scorer.target_label(mon) for mon in targets))

    turn = getattr(battle, "turn_count", 0)
    last_switch = getattr(participant, "last_ai_switch_turn", -100)
    likelihood = min(1.0, max(0.0, context.profile.switch_likelihood))
    if chosen is not None and likelihood and turn - last_switch >= 3:
        current_score = max((entry.scored.score for entry in assessed), default=0)
        low_hp = getattr(pokemon, "hp", 1) <= getattr(pokemon, "max_hp", 1) / 3
        preferred = None
        preferred_score = -1
        for switch in legality.switches(reserved=reserved):
            reserve = switch.pokemon
            reserve_moves = [LegalActions(battle, participant, reserve)._move(move) for move in getattr(reserve, "moves", [])]
            scores = score_ai_moves(context, reserve_moves, user=reserve, target=scorer.foes[0] if scorer.foes else chosen.target_pokemon,
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
            trace.target_name = scorer.target_label(chosen.target_pokemon)
            trace.choose(chosen.move.key, intent=decision.intent)
            logger.info("%s chooses %s", participant.name, chosen.move.name)
        else:
            logger.info("%s chooses to switch to %s", participant.name, getattr(chosen.pokemon, "name", "Pokemon"))
    attach_ai_debug_trace(participant, battle, trace)
    return chosen
