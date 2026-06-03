# Battle AI Design Reference

## Purpose

PF2 battle AI should be shared, profile-driven, explainable, and expandable.
The goal is not to build a competitive "psychic" bot. AI opponents should make
reasonable, learnable decisions from battle-visible information, with wild
Pokemon staying simple and trainers gaining sophistication through explicit
profiles and difficulty levels.

This document is a durable reference for future AI work. It is not a request to
rewrite the battle engine in one pass.

## PF1 Lessons

PF1 used one shared battle brain for wild Pokemon and NPC trainer Pokemon.
Wild and trainer encounters differed mostly in setup and team generation: both
paths placed Pokemon on the opposing side, marked them AI-controlled, and let
the shared handler choose actions.

The useful PF1 patterns were:

- Wild and trainer actions flowed through one shared selector.
- `AItype` described battle rules and setup, while trainer metadata described
  how smart the AI should be.
- `AIlevel` affected pre-battle team quality and runtime options.
- PF1 filtered illegal or bad moves before scoring.
- PF1 scored attacks using damage-like factors such as power, accuracy, STAB,
  type effectiveness, and relevant attacking stat.
- PF1 used weighted random choice, not strict deterministic best-score choice.
- Switching and item use were gated to higher AI levels.
- PF2 should copy the architecture, not the MUF property shape.

## PF2 AI Goals

PF2 should move toward:

- One shared action selector for all AI battlers.
- `AIProfile` or `AILevel` stored on the controller, trainer, or encounter
  profile, not only on raw Pokemon.
- Simple wild behavior by default.
- Smarter trainer behavior when the encounter profile asks for it.
- Gym leaders and feature NPCs with future strategy profiles.
- Anti-grind awareness so NPC battles do not become command-volume or reward
  abuse loops.
- Non-spammy battle output.
- Decisions that are fair, inspectable, and learnable.

Long-term flow:

```text
AIController
-> builds BattleAIContext
-> asks AIProfile/ProfilePolicy for allowed intents
-> IntentSelector picks intent
-> ActionGenerator lists legal actions
-> ActionScorer scores actions for that intent
-> WeightedChooser picks from top candidates
-> DebugTrace records why
```

Likely long-term intents:

- `finish_target`
- `safe_damage`
- `setup`
- `recover`
- `status_target`
- `control_field`
- `preserve_self`
- `pivot`
- `stall_turn`
- `support_ally`

These should be added in small testable phases.

## Non-Goals

- Do not build a full competitive Pokemon Showdown bot.
- Do not make AI read the player's hidden selected command.
- Do not let AI know unrevealed moves, abilities, or held items unless battle
  state has revealed them.
- Do not implement Gen 10+ mechanics.
- Do not rewrite the entire battle engine for this.

## AI Knowledge Rules

AI may know:

- Visible species.
- Visible HP.
- Visible status.
- Revealed ability.
- Revealed held item.
- Revealed moves.
- Stat boosts.
- Field effects.
- The type chart.
- Its own team, bench, and inventory.

AI should not know:

- Unrevealed player moves.
- Unrevealed player ability.
- Unrevealed player held item.
- Exact EVs or IVs unless intentionally exposed by profile.
- The player's selected action this turn.

## AI Profiles

Early profile keys:

- `wild_basic`
- `trainer_basic`
- `trainer_skilled`
- `gym_leader`
- `feature_boss`

Fields likely needed later:

- `key` or `name`
- `level`
- `personality` or `risk_tolerance`
- `switch_likelihood`
- `item_policy`
- `knowledge_policy`
- `allowed_intents`
- `strategy_key`

Profile examples:

- `wild_basic`: use visible moves and simple damage decisions; no routine
  switching or item use.
- `trainer_basic`: prefer reasonable attacks, limited status/setup awareness,
  very rare switching.
- `trainer_skilled`: use stronger move scoring, conservative switching, and
  profile-gated item logic.
- `gym_leader`: preserve key Pokemon, use defined item budgets, and follow a
  strategy profile.
- `feature_boss`: allow event-specific strategy hooks and special encounter
  rules.

## Move Selection Improvements

Staged move work should add:

- Legality filtering.
- Estimated damage.
- Expected damage as estimate times accuracy.
- STAB and type effectiveness.
- KO bonus.
- Overkill penalty.
- Setup and status context.
- Repetition penalty.
- Priority value.
- Doubles and spread-move awareness later.

The selector should still use weighted choice from strong candidates. This
keeps AI from feeling perfectly deterministic while allowing better profiles to
make consistently better choices.

## Switching Improvements

Staged switching rules:

- Most wild Pokemon do not switch.
- Basic trainers rarely switch.
- Skilled trainers switch out of awful matchups.
- Gym and feature NPCs may preserve an ace, pivot, or switch into immunities.
- Never switch if the active Pokemon can safely KO now.
- Avoid switching into hazard death.
- Avoid switching if all bench options are worse.

Switching should remain profile-gated because poor or frequent switching can
make normal encounters feel slow and frustrating.

## Item Use Improvements

Staged item policy:

- Wild Pokemon do not use items unless the encounter explicitly says otherwise.
- Trainer item use is profile-gated.
- Healing should happen only when it changes survival prospects.
- Status cures should depend on role, status severity, and profile.
- Avoid wasteful healing.
- Gym leaders may have defined item budgets.

Item use must avoid battle log spam and should be easy to disable for tests or
low-tier encounters.

## Doubles AI

Doubles needs dedicated handling rather than single-battle heuristics applied
twice. Future logic should account for:

- Target scoring.
- Spread move ally safety.
- Fake Out.
- Protect.
- Helping Hand.
- Follow Me and Rage Powder.
- Tailwind.
- Trick Room.
- Weather and terrain support.
- Avoiding ally damage unless the ally is immune, protected, or the strategy
  explicitly allows it.

## Debugging And Explainability

Desired future admin-only commands:

- `+aidebug`
- `+aidebug/last`
- `+aitest <profile> <pokemon> vs <pokemon>`

Debug traces should be non-spammy and should not appear in normal combat logs.
Admins should be able to inspect:

- Profile key.
- Chosen intent.
- Legal actions considered.
- Scores and reasons.
- Chosen action.

Debug output must not leak hidden player information.

## Implementation Roadmap

### Phase 1: Documentation And Inspection

- Document the intended architecture.
- Inspect current AI and battle action flow.
- Identify safe extension points.

### Phase 2: Profile, Context, And Trace Scaffolding

- Add `AIProfile` or equivalent profile config.
- Add `BattleAIContext` or equivalent lightweight battle view.
- Add `AIDebugTrace` or equivalent non-player-facing trace structure.
- Wire the trace into the current AI decision flow without changing battle
  outcomes heavily.

### Phase 3: Legal Move Scoring

- Filter illegal moves consistently.
- Add expected damage, STAB, type effectiveness, KO bonus, and simple
  repetition penalty.
- Keep weighted choice from good candidates.

### Phase 4: Conservative Switching

- Add profile-gated switching.
- Start with awful-matchup exits and obvious hazard checks.
- Do not add complex pivot strategy yet.

### Phase 5: Trainer Item Use

- Add profile-gated item budgets.
- Start with healing or curing only when the action materially helps.

### Phase 6: Gym And Feature Strategy Profiles

- Add explicit strategy profiles for gym leaders and feature NPCs.
- Keep strategy data safe and inspectable.

### Phase 7: Doubles-Specific Intelligence

- Add target, support, spread move, and ally-safety logic for doubles.
- Treat doubles intelligence as a separate maturity step.

## Current Implementation Notes

As of this reference, PF2's live AI action path is:

```text
BattleSession._auto_queue_ai_actions()
-> pokemon.battle.engine._select_ai_action()
-> BattleParticipant.choose_action() / choose_actions()
```

`pokemon.battle.ai.AIMoveSelector` exists as a helper, but the current live
runtime entry point is still `_select_ai_action`. Phase 2 should therefore add
scaffolding around that path first, then later decide whether the shared
selector should move into a dedicated controller class.
