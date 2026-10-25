# Thirteen additional berry snacks (#866)

Accepted design scope after repairs, reporting and acquisition scope. These are PF2
feeding equivalents, not invented cartridge recovery effects. Existing Natural
Gift/Fling identities and held callbacks remain unchanged.

Use the existing `+berry snack <full berry name>=<current target>` route. Select
**10 HP** for each named berry, matching Razz's bounded food equivalent. Do not
enable `+use`, manual battle medicine or automatic held recovery for these
names. No status/PP/friendship/EV change, Nature confusion, lure, capture,
contest, progression or other hidden benefit. Ten HP is chosen PF2 policy.

| Implementation issue | Exact berries, each suffixed Berry | Effect per copy |
| --- | --- | --- |
| Small flavor berries | Bluk, Nanab, Pinap, Wepear |10 HP |
| Middle flavor berries | Cornn, Magost, Nomel, Rabuta |10 HP |
| Remaining flavor berries | Belue, Durin, Pamtre, Spelon, Watmel |10 HP |

There are13 additions in batches4/4/5; Razz is the unchanged fourteenth snack.
Extend an explicit registry, not every dex berry's `isBerry` metadata. Reuse
`BerrySnack`, `FieldProgressionUse` and the current field transaction/target
checks. The named target must still be this trainer's current ordinary party
member or actual current Fusion when locks are acquired. Reject missing,
ambiguous, foreign, boxed, egg, fainted/full, invalid saved HP, battle/pending
battle and conflicting-reservation cases. Combined companions stay frozen;
legitimate hosts follow existing field eligibility.

One useful heal and one bag debit commit together, including partial healing
up to the project-calculated max HP. Held-only stock is not a bag copy. Stock
aliases cannot duplicate consumption. Preserve saved species/nickname, ownership,
placement, genetics, statuses/sleep, moves/PP and progression. No-effect use
does not consume a copy or announce success. Failures after debit/effect/save
or an outer rollback restore SQL and caches; success waits for outer commit.
Stale prompts or two last-copy users cannot debit twice or heal a former target.

Each implementation issue includes all named positive/full/fainted/invalid/
stale/rollback/contention cases through the real command and fresh SQL, then
reconnect and subsequent battle/field state. Keep Razz, ordinary recovery and
EV berries and all existing Natural Gift/Fling regressions. A separate source
offer for each implementation batch may use100 per berry, five initial copies,
finite buy-only/no refill; installation and ordinary buy→inventory→snack proof
remain explicit acquisition/release work. Growing them is outside this design.

Create exactly three linked implementation issues with these lists and common
acceptance. Closing this scope will not mark the thirteen foods implemented,
publicly stocked or released. Implementation follow-ups are linked below.


## Implementation follow-ups

This closes the design/scoping deliverable only. Runtime effects, source installation,
migration/release operations and ordinary acceptance remain with these open issues.

| Issue | Exact delivery | Dependencies |
| --- | --- | --- |
| [#889](https://github.com/PokemonFusion/Fusion2/issues/889) | Add explicit flavor berry snack batch 1 | #866 |
| [#890](https://github.com/PokemonFusion/Fusion2/issues/890) | Add explicit flavor berry snack batch 2 | #866, #889 |
| [#891](https://github.com/PokemonFusion/Fusion2/issues/891) | Add explicit flavor berry snack batch 3 | #866, #890 |

Scope/source checks: [2026-10-25 decision receipt](../testing/item-scope-decisions-2026-10-25.md).
