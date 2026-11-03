# Existing item repair candidate — October 29, 2026

Local implementation for #922–#928, with #929 reconciliation. Based on staging
`9c36beec68b2e3b6a413b2c4c93785f620831e48`; the [machine receipt](item-repairs-2026-10-29.json) pins the
changed sources. Publication, deployment and socket acceptance are separate.

## Exact inventory and behavior

| Issue | Inventory | Delivered facet |
| --- | --- | --- |
| #922 | Liechi, Ganlon, Salac, Petaya, Apicot, Starf Berry | Canonical stages, Contrary/Simple, caps, effective Gluttony and battle-owned Starf randomness |
| #923 | Absorb Bulb, Cell Battery, Luminous Moss, Snowball, Kee Berry, Maranga Berry, Weakness Policy, Throat Spray | Canonical deltas and AfterBoost consumers, retaining guarded triggers/history |
| #924 | Electric, Grassy, Misty, Psychic Seed | Matching terrain uses one copy through canonical boost and history rules |
| #925 | Black Sludge, Sticky Barb, Rocky Helmet, Jaboca Berry, Rowap Berry | Typed indirect damage; Magic Guard and legitimate suppression; retained contact/category rules |
| #926 | Leftovers, Poison-type Black Sludge | TryHeal, Heal Block/Psychic Noise expiry, capped useful healing and no revival |
| #927 | Standard medicine and the already permitted recovery foods/berries | Active recipient Embargo rejection before queuing and revalidation at execution; reserves/partners retain eligibility |
| #928 | Berserk Gene | Attack-only boost, normal confusion/Own Tempo, guarded single-copy consumption and Recycle |

The [player guide](../held-item-repairs.md) and [bag contract](../battle-recovery-items.md)
state the selected interactions. Qualifying stat consumables are used even at a
cap. Starf samples uniformly from five non-accuracy/evasion stats below +6 before
ability modification; all-capped eating has no stage effect. Its optional RNG
checkpoint accepts validated JSON and Evennia saved sequences, leaving global
randomness untouched. Absent legacy state keeps the existing battle route.

Jaboca/Rowap retain their copy against effective Magic Guard, following the
pinned primary reference; suppressed Magic Guard allows ordinary retaliation.
Damage rounds down with a minimum of one and reports actual HP loss. Sticky Barb
physical contact transfer also reuses the existing TakeItem/transfer boundary.

Gastro Acid is now respected by the shared effective-ability reader. Heal Block
retains structured duration state, does not refresh an existing block, and expires
after five residuals (two for Psychic Noise). Scoped residual dispatch honors
declared residual order, so healing remains blocked on the expiry boundary.

## Verification ledger

- 311 new stat engine cases cover all 18 names across ordinary/Contrary/Simple,
  prior stages −6/−2/0/+2/+6, real calculated stats, Gluttony, suppression,
  terrain entry/change, Recycle and random-state validation.
- 36 new engine cases cover the five damage effects, native Magic Guard and
  Gastro Acid, both residual healers, real blocking moves/expiry, caps/fainting,
  and native ordinary/Own Tempo/Contrary/Simple Berserk Gene users.
- 16 target-policy cases cover medicine families, reserve/actor distinction,
  field use and held suppression. The preserved core assertions now read the
  canonical stage keys instead of asserting the obsolete alias representation.
- The focused repair selection passed 669 tests; the separate medicine/healing
  selection passed 158. These selections overlap and are not summed.
- Disposable PostgreSQL: the final stat runner contains 92 cases (18 names ×
  five ordinary/native-ability/suppression/rollback routes, plus earned Swords
  Dance and opposing Mirror Herb cases). **All 92 passed**, recording 845 ordinary command inputs.
- Disposable PostgreSQL: 52 HP/medicine/Gene cases passed. Eleven exact medicine
  names each cover blocked declaration, useful unaffected reserve and stale
  queued Embargo; doubles keeps a sibling declaration while targeting another
  recipient. Fifteen damage cases, two healing/expiry routes and native Own Tempo
  Gene/Recycle complete this matrix.
- The earlier #920 and #921 command matrices were replayed together: 67 cases
  passed (21 Mega theft and 46 reactive-consumption routes). Their original
  reports remain dated evidence; the new replay preserves prior coverage on
  this candidate.
- Mandatory gate **returned zero** for all three fresh processes: combined
  8,082 passed / 4,032 skipped / 2,143 warnings (399.86s), repeat the same
  counts (377.90s), and battle-first 8,082 passed / 4,032 skipped / 2,163
  warnings (334.90s). Model re-registration and denied pytest-cache writes remain
  visible in the log; skipped cases establish no acceptance.
- The three SQL matrices total **211 passing cases and 2,234 ordinary command
  inputs**. The 144 new cases include 18 post-consumption write-failure retries.
  All disposable schemas were dropped; the private test endpoint is separate
  from the game database.

Every SQL route uses production command parsers, owned models, real native
abilities/stats, turn transactions and saved checkpoint rebuilds. Known move
fixtures are checked against native learnset metadata. Setup supplies explicitly
labelled disposable owners, Pokémon, legal known slots, injuries/PP and bag stock;
it does not prove public capture, teaching or item acquisition. Transport is
captured, without logged-in sockets. Failure injection remains separately labelled.

## Diagnosis, limits and preservation

The direct stat writes, indirect HP assignments, healer bypass and missing manual
Embargo check were confirmed mechanics defects. The missing Gastro Acid consumer
guard and overwritten Heal Block timer were found while exercising real controls.
The shared helpers repair those paths without changing ordinary direct damage.

An early test used moves absent from the prepared native learnset, another ran
out of Rain Dance PP, and the first persisted random-state loader rejected
Evennia's saved sequence wrapper. Native move prerequisites, a durable legal idle
move and sequence validation corrected these distinct fixture/runtime issues.
Test logs also exposed a rotating shared battle-log handle; new SQL runners now
use private test logs and close only their own handles. Failed preliminary logs
remain outside the repository as diagnostic evidence.

An AST comparison changes exactly the 25 named item callback classes. Mega Stone
identity hooks, CAP, generated item/species/learnset definitions, Link Cord and
trade-held evolution semantics are preserved. No sources, stock, migrations,
human fixtures, shared service restarts or deployments are included.

The source-only index has 642 definitions / 494 scoped capabilities; capability
labels do not establish every facet or public availability. The separately dated
October 29 read-only PF2-Dev stock inspection describes its older checkout,
without qualifying these local repairs. Existing Belch selection integration,
broader Pickup eligibility, unreviewed Z sources, other berry-growing species,
post-hatch Mirror Herb teaching and the remaining scoped additions stay explicit
follow-up work. #930–#938 retain their dependency on repair acceptance.
