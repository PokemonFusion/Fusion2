# Item repair #858: held-status-berries (2026-10-25)

Status: **accepted local repair**. Pecha Berry and PSN Cure Berry cure psn/tox; Burnt Berry cures frz only.

This issue is one of four separate repairs (#858/#873/#874/#875) qualified on the
same corrected frozen tree with #859 reporting above baseline `65e8e246bb50f4672ffdffa79740999251950b7a`. See the
[machine receipt](held-status-berries-2026-10-25.json) for exact source hashes, commands, raw-receipt
identity, independent SQL/runtime/inventory checks and retained pilot diagnoses.
This does not claim acceptance of each intermediate commit in isolation.

- New offline regressions for this issue: 39; affected focused suite: 1776 passed.
- New ordinary owned-player PostgreSQL cases: 31 (25 effect/lifecycle, three missing-stock and three rollback controls).
- Compatibility: 426 cases across field/legacy berries, manual recovery foods, status/medicine, four-controller Multi and native Origin/Primal/Rusted routes.
- Mandatory fresh-process gate: 6142 passed / 4028 skipped in each of combined, repeat and battle-first; wrapper exit0.
- All 25 unrelated shared-checkout paths remain unchanged; 1133 Python sources pinned.

Player cases use actual nickname input, `+hold`, `+attack`, durable queued and
completed checkpoints, end cleanup and `+hold 3=`. Source PP falls once; bag
copies do not change during held effects. Useful eating consumes exactly one
physical copy; no-effect cases return both original copies after unhold.
Controller UUID mappings prevent sorted-row order from masquerading as ownership.
Genetics, level, native species, original ownership and canonical placements remain stable.

The Ice Beam case naturally freezes with ordinary RNG seed3. Toxic/poison/burn/
paralysis, Magic Room, Embargo and Unnerve/Skill Swap use legal native moves and
abilities. Freeze and sleep are not Synchronize-reflected statuses. Embargo's
completed-turn durations are 4,3,2,1,0,0; eating follows expiry at the next update,
including reconnects. Legacy boolean Embargo has no reconstructable elapsed timer
and receives a bounded five-residual countdown when resumed.

Existing field and manual amounts/policy are unchanged. Supported no-effect
manual medicine spends its queued action without consuming a copy; unsupported
items reject before declaration. The original failing fixture assumption is
retained, as are the actual Synchronize, reconnect and Embargo failures.

These are local automated production-command/model checks in disposable schemas,
with separate tagged stock/capture prerequisites. They are not a socket login,
shared-game deployment, permanent item source, hosted CI result or proof that
every catalog combination works. #860 owns a fresh released-candidate walkthrough.
No plot/CAP item, unrelated WIP, existing human character or live game data changed.
