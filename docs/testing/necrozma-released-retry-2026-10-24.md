# Native Necrozma released local acceptance (#831)

**Passed** on October 24, 2026, using deliberately released candidate
`e3557aadced7fc5897b7024d1377047117735a64` in `necrozma-release-05e2205bda484d27a13099e03698300c`. The user explicitly approved the local dev
retry. All 1,116 Python files in both the archive and isolated checkout match
the committed candidate's Git blobs; no product code changed during this run.
The [lossless redacted JSON](necrozma-released-retry-2026-10-24.json) contains
**186 ordinary socket observations, 13 independent SQL snapshots and
three read-only runtime observations**, with separate staff preparation,
expected/observed checks, diagnostics, integrity verification and teardown.
Transport was automated input over two real ordinary telnet sessions, not manual
human testing. Both accounts remained non-superuser Player throughout.

The [first released attempt](necrozma-released-local-2026-10-24.md) remains a
failed historical receipt. Its zero-PP defect was fixed in `e3557aa` and
[qualified separately](necrozma-pp-repair-2026-10-24.json): 181 focused checks,
182 production-model PostgreSQL cases across nine suites, and three fresh full
orders of **4,933 passed / 4,014 skipped each**. This replacement walkthrough
completes that remaining release gate; it does not overwrite the failed attempt.

## Ordinary player results

| Player route | Expected and observed |
| --- | --- |
| Register, human chargen, travel, finite store and hunt/capture | Two new ordinary accounts completed onboarding, bought their own balls/crystals/medicine and genuinely captured base Necrozma plus Solgaleo/Lunala. Separate staff configured finite stock, wallets and base charts; no source, fused row or bag grants. |
| Center combine/review | Outside-Center use rejected; cancellation made no pair; changing a held item invalidated exact review. Fresh confirmations produced both native forms on their original host UUIDs and reserved unchanged companions. |
| Inspection and party | Reserved companion inspect remained read-only; companions stayed outside playable rosters and independent use. |
| Ordinary attacks and signatures | Sunsteel Strike and Moongeist Beam dealt real damage; Searing Sunraze Smash and Menacing Moonraze Maelstrom dealt real damage, each spending one source PP. Both source banks ended at 3/5 after one ordinary plus one Z action. No hit/damage/RNG outcome was forced. |
| Side budgets and reconnect | Both side budgets became spent, repeated Z requests rejected, crystals remained held and the spent state survived an ordinary reconnect. Ordinary concession ended the battle and released locks. |
| Field items | Real battle-fainted Dusk used Revive; both used Ether, then PP Up/PP Max through displayed move selection. Separately labelled source-PP0 prerequisites followed by ordinary Ether restored exactly 6/6 and 8/8. |
| Full-party and boxed/fainted separation | Dusk captured enough extra Eevees to fill all six playable slots: Solgaleo returned to Box 1 without eviction. Labelled HP0 Dawn separated while fainted, retaining HP0 and returning Lunala to its prior Box 2/position 1. Fainted recombine rejected until ordinary Revive. |
| Zero/boosted cycles | Both recombined with the same boxed companions: source PP stayed0, capacities stayed6/8, active/saved source identity stayed valid. |
| Repaired zero-PP battle route | In a fresh active PvP battle, both ordinary source attacks rejected as unusable and both Z requests rejected for no PP. Before/after runtime and independent SQL were identical: turn 1, empty declarations/pending actions/Z budgets, unchanged HP and source PP0. No action, damage or side use was spent. |
| Final separation/integrity | Both companions' complete owned rows, active/saved/learned moves and boosts matched capture baselines in all 13 SQL snapshots. Protected sentinel and ordinary permissions stayed unchanged. No pair/reservation/actionable review/battle lock/orphan resource remained. |

## Retained diagnostics and limits

Three raw runner expectations failed without a mechanics defect: the stale
message used “stale” instead of the expected “changed”; the PvP start text used
lowercase “battle”; and a capture attempt followed an ordinary cooldown refusal.
The full failed checks remain in JSON. Waiting normally and retrying the hunt
completed the full party. The private read-only evaluator was corrected to use
the existing `bonus_pp` field and to recognize an expired stale review as
nonactionable history. An observer attempted after logout found no attached
account; reconnecting restored that read-only prerequisite and final observation
passed. None of these changed product code or forced gameplay outcomes.

Before teardown, two owned dormant source banks (PP0) and one expired stale
review receipt remained valid history. The expired review rejected ordinary
resumption, reserved no source and disappeared with its disposable schema.
Optional PP0/HP0 setup is labelled separately from real battle outcomes.
No general public source availability or shared-world deployment is claimed.
Ultra, plot-only items, permanent grants and unrelated work remain excluded.

## Cleanup and publication boundary

Both pairs separated and both ordinary clients quit. The supervisor stopped
only this archived instance, verified ports 53241–53245 closed and dropped only
`pf2_recovery_test_e02362a93af948c7bb5200833fad0696`. Independent teardown inspection confirmed no public
tables or disposable schemas. Only this task's PostgreSQL fixture was stopped.
All 24 unrelated shared UI hashes and four inline compact-prompt additions were
verified unchanged; no shared checkout product file was written. PF2-Dev,
existing game services/databases and human characters were untouched.
