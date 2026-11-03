# Bounded item additions — October 29, 2026

Candidate based on repair commit `af476a950cd21842050c3e79c58adb1731b75c47`.
This adds #932's six exact Z mappings and #935's four field recovery medicines.
The [Z receipt](z-next-six-sources-2026-10-29.md) and [medicine guide](../remedy-recovery.md)
state their reviewed effects, source limits and selected primary references.
The [machine receipt](item-additions-2026-10-29.json) pins the final accepted
local candidate. Publication and deployment remain separate.

The focused additions selection passed **169 tests**, with a separate 11-case
existing-source selection also passing. The new coverage comprises 18 Z engine
cases, 31 recovery effect cases and four additional parameterized field-only
definition cases. Existing generic/status/signature/Ultra and original recovery
equivalent tests remain in the mandatory suite.

Disposable PostgreSQL results:

- **94 Z cases passed**, including configured native acquisition and actual
  command/PP/budget/rollback controls.
- **24 new medicine cases passed**: each of the four exact names covers normal
  purchase/discovery/use/reconnect, healthy/fainted no effect, fresh ownership/
  egg/box/battle/held-only guards, current versus inactive Fusion, two post-write
  rollback injections and concurrent final-copy requests. Foreign controllers
  have their own bag stock, so their refusal exercises ownership eligibility.
- **Eight original Rage Candy Bar/Hopo Berry cases passed**, retaining their
  exact HP/status/PP, Fusion, rollback and contention routes.

Production fields and statistics are used throughout. Test setup is separately
tagged; stock, injuries, native species and known moves are not attributed to
public player acquisition. Transports are captured. No human fixtures, shared
world installation, stock/refill, migrations, restarts or deployment occurred.

The first native-boundary expectations used current-generation levels instead
of PF2's combined-generation minimum levels. Fixtures now match the existing
learning service, without changing it. Older negative tests used Fire Blast as
an example of an unreviewed source; Fire Punch remains that control after the
explicit Fire Blast addition. One incomplete gate was deliberately stopped
after finding that stale expectation; the final complete gate is recorded
separately in the machine receipt.

## Final gate and preservation

All three fresh mandatory processes returned zero:

| Order | Passed | Skipped | Warnings | Seconds |
| --- | --- | --- | --- | --- |
| combined | 8,135 | 4,032 | 2,143 | 377.99 |
| repeat | 8,135 | 4,032 | 2,143 | 350.69 |
| battle-first | 8,135 | 4,032 | 2,163 | 310.89 |

Model re-registration and denied pytest-cache writes remain visible; skipped
cases establish no acceptance. The three SQL matrices total126 passing cases.
The private PostgreSQL helper was stopped after verifying zero remaining
disposable schemas; the game database and running services were not altered.

AST comparison preserves the original31 generic additions and14 status entries;
all16 signatures and the separate Ultra profile are unchanged. All494 prior
scoped definition fingerprints match the preceding repair index exactly. The
four new definitions produce646 total /498 scoped items. The source-only index
keeps live availability unknown and records the separately deferred or scoped
missing definitions without manufacturing supported catalog rows.
