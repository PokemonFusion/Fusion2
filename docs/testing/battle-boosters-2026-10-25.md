# Manual battle booster qualification (#907–#909)

Qualified locally through ordinary `+item` parsers, actual turn processing,
finite `+store`/menu acquisition and fresh PostgreSQL checks. Captured transport
is automated player-command acceptance, not a socket login or deployed proof.
Rules: [player guide](../battle-boosters.md). Machine receipts and compact
before/after observations: [report](battle-boosters-2026-10-25.json).

Eight new items: six X items (+2 matching stage), Dire Hit (actual Focus Energy,
critical stage +2 once), Guard Spec. (side Mist for five residual turns including
activation). They support current conscious owned self actors in reviewed
two-participant wild/trainer/PvP singles and doubles, with explicit doubles
selection. Wrong/no-effect inputs reject before declaration. Useful resolution
pays one action and copy; queued redundancy pays the action without spending a
copy. Invalid execution state or persistence failure rolls back the whole turn.

The exact immutable retry candidate passed **180 SQL cases**:65 booster,
8 authored finite-source,22 prior battle-item validation,50 manual recovery,
15 native pair and20 Z/status. It also passed the26 affected existing command
fixtures. Earlier focused mechanics/consumer checks passed119 cases; all are
included again in the final full suite.

Mandatory gate: **6,505 passed /4,028 skipped in each of three fresh processes**
(combined, repeat, battle-first), exit0. The entire1,170-file staged Python map
is checked against that immutable candidate before commit. Later mint WIP is
excluded;25 unrelated dirty paths in the shared checkout are preserved.

Coverage includes all eight +item flows, separate-connection last-copy races,
ordinary damage/defense/speed/accuracy, native Simple/Contrary and caps, actual
critical/blocked damage, switch/faint/end/Baton Pass, Mist opposition/self/reset/
Infiltrator/benefit rules, timer expiry, pending/rebuilt sessions, exact remaining
duration and source, partial debit/checkpoint/outer failure, sibling declarations,
and unchanged medicine/capture/native/Z paths. The accuracy consumer now applies
the reviewed net accuracy/evasion stage before its random boundary. Paid stage
markers survive ordinary turn reset; Mist survives restore without replay.

The first full run stopped with26 command-fixture errors because a capability
check eagerly imported a mocked non-package battle namespace. The production
check now uses item metadata and imports battle code only for booster requests.
Exactly those two source files changed for the retry; its SQL suites, command
fixtures and all three full orders were rerun. Failed logs/hashes are retained
in the machine report, separate from successful qualification.

The optional `world/battle_booster_counter.json` offers five finite copies of
each item: X items/Dire Hit1,000; Guard Spec.1,500, via `boosters`/`back`, buy-only.
Importing code installs/refills nothing. The index has620 definitions/472 scoped
items, preserving all464 previous hashes; all world availability remains
unverified. No migrations, service restart, shared stock, PF2-Dev release,
hosted CI or deliberately released socket acceptance is claimed. Plot-only
items, unrelated WIP and the separate #915 work are excluded.
