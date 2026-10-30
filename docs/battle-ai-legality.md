# Legal battle AI actions

`pokemon.battle.legal_actions.LegalActions` supplies the move/target and reserve
candidates used by ordinary trainer and gym AI. The existing profile-weighted
move scorer consumes those candidates; it does not choose from the unfiltered
move list. This is the September #710 foundation for player doubles (#708) and
later AI scoring improvements.

## Selection and execution

- Move candidates retain remaining PP, reject Disable/Taunt, Encore/locked-move
  conflicts and Choice-item conflicts, and enumerate living legal targets.
  Self, ally, foe and automatic target classes use the move's dex metadata.
- Reserves are distinct living members of the same roster, outside the active
  slots and other pending switch reservations. Voluntary switches respect
  trapping and identify the exact outgoing slot. Forced replacement uses the
  first legal reserve in party order and does not let a trap strand a fainted
  slot.
- Ordinary trainer and gym profiles can voluntarily preserve a low-HP actor
  or escape an almost unusable offensive matchup when a legal reserve has a
  visible benefit. The existing profile's switch likelihood bounds that choice.
  A side cannot voluntarily switch again for three turns after a successful
  AI switch. Wild profiles retain a zero switch likelihood.
- Preferred queued actions are revalidated before priority/speed ordering.
  An unavailable preference uses the first remaining legal candidate. A choice
  invalidated after ordering is skipped without consuming resources or giving
  a replacement attack the old switch action's priority.
- When all learned moves are unusable, the emergency move is **Struggle**.
  Choice and Disable locks cannot make that fallback loop forever. A fainted,
  replaced, foreign or terminal actor cannot receive a replacement action.

The policy uses current visible state and existing scoring weights. It does
not predict the opponent's queued move or implement the later strategy,
support/spread valuation, field reasoning or player-authored AI issues.

## Session and reload behavior

The session queue retains a declaration for every AI active slot, including
switches. Slots cannot reserve the same incoming Pokemon. Checkpoint rebuilds
restore each action's actor, exact target and outgoing switch slot. Successful
switch cooldowns are stored in the existing battle checkpoint; no schema
migration is required. Existing encounter metadata supplies the AI profile
again after rebuild.

Disable, Encore, trap volatiles and Choice-lock state are retained in Pokemon
snapshots. Move objects in those effects are serialized as name/key/PP
references, avoiding callbacks and live object graphs in the saved checkpoint.
Old checkpoints without these additional fields retain their previous defaults.

## Verification

`tests/battle/test_legal_ai_actions.py` exercises legality, target classes, invalid
actors, reserved and trapped slots, deterministic forced replacement, bounded
switching, stale preferences, late invalidation and safe move snapshots.
Existing AI scorer, PP, trainer reserve, move-control and trapping regressions
remain part of the mandatory suite.

With an explicitly configured disposable test connection:

```powershell
$env:PF2_TEST_POSTGRES_DSN = '<test PostgreSQL DSN>'
..\evenv\Scripts\python.exe -B tests/integration/ai_action_cases.py
```

The six production-session cases verify forced replacement/rebuild, a queued
voluntary switch through execution and reload, disabled saved preferences
spending only the legal move's PP, rooted/choice controls after rebuild,
Struggle advancing an exhausted ready turn, and distinct double-slot actions.
They create production model tables directly in guarded disposable schemas
and are included in lifecycle CI. They do not migrate the game or restart it.

This verifies local automated behavior. Player doubles command exposure and
ordinary-player doubles acceptance are tracked by #708; broader AI choice
quality remains separate from legality.
