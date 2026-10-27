# Native Necrozma item closeout (#825–#830)

Both native forms pass local ordinary-player command, field, battle and
independent SQL acceptance. The public command is registered in the tested
source; a running game must deliberately release that build and migrate first.
**#831 remains open for separately approved released-build socket acceptance.**

Implementation: `a45eed73d953f7350d9510482aac5534fac7ef51`. [Player guide](../necrozma.md) ·
[rules](../design/necrozma-combination.md) · [operations](../operations/necrozma-combination.md) ·
[lossless commands, SQL and validation JSON](necrozma-items-2026-10-24.json).

**51 new native / 618 total PostgreSQL cases**, seven
approved migration rehearsals, **178 focused checks**,
and three fresh combined/repeat/battle-first orders of **4930 passed / 4014
skipped each** pass. All production and each executed domain harness remained
unchanged during their qualifying checks. The final three full orders use one
frozen **1116 Python file** identity, compared to committed Git blobs
before publication. Fixture corrections and their scope are recorded in the JSON.
The JSON retains 516 exact command/menu/state observations with verified
lossless deltas; chart/stock and explicit damaged/depleted/invalid preconditions
remain separately labelled fixture setup.

## Player and integrity proof

- Actual configured hunts and ordinary Master Ball capture supply base
  Necrozma and Solgaleo/Lunala. No fused row or companion is granted. Real
  Center-only `+necrozma` review, yes/no, reconnect/review, inspection and
  separation bind current UUIDs, gapped slots, exact terms and five-minute expiry.
  The real PokemonCoreCmdSet exposes the same accepted command class.
- Same host identity/owner/placement, its own genetics/progression/held item,
  and current absolute HP deficit/status persist. The unchanged companion is a
  second owned row in canonical `combined` custody without legacy mirrors.
  Companion writers, foreign/same-account selectors, unsupported claims, direct
  fused grants/captures and unreviewed host changes reject before debit/write.
- Selected actual slot, including an empty gap, uses one durable source bank.
  PP5 is introduced once; zero and bonuses survive cycles/companion changes.
  Actual attack/Z, field/battle Ether, PP Up/Max and healing commit canonical PP
  and bank together. Hidden displaced/dormant moves cannot heal. Separation
  restores only that slot, retaining other current PP, earned base knowledge,
  EXP, Rare Candy, EV and Hyper Training effects. Old PP prompts cannot affect a
  new lifecycle.
- Both forms use ordinary attacks and their existing held Z signatures through
  current native proof. Real two-controller doubles retain useful damage,
  quarter Protect damage, sleep prevention and type/ability boundaries. Native
  Lunala/Solgaleo profile tuples and fingerprints remain byte-for-byte stable.
  Switch, checkpoint rebuild, faint/Revive, end, flee and concession preserve the
  pair; companion SQL remains unchanged. A controller's later trainer Fusion,
  forged/stale provenance and incompatible stacked mechanics reject.
- Write faults after every combine/separate stage, parent rollback, stale and
  exact receipt replay, later release, no destination/full party/deleted-box
  returns and independent connection races retain one lawful custody outcome.
  Races include combine/combine, separate/separate, older-cycle combine/separate,
  placement, release, field use, trainer Fusion, transfer reservations and battle
  admission. SQL constraints reject raw bulk ownership/source/mirror corruption.
- Migrations rehearse fresh install, upgrade, legacy fused/source refusal before
  feature writes, invalid integrity refusal, unused rollback/reapply and used-data
  reversal refusal. Existing assets survive and model drift is empty. Only the
  explicitly approved random schemas on the new task cluster were used.

## Regression suites

| Disposable PostgreSQL suite | Passed |
| --- | --- |
| schema | 15 |
| lifecycle | 22 |
| player | 14 |
| placement | 20 |
| ownership | 23 |
| fusion | 22 |
| field_item | 23 |
| pp_capacity | 37 |
| hyper_training | 31 |
| evolution | 28 |
| ability_item | 30 |
| trade | 19 |
| market | 18 |
| daycare | 11 |
| breeding | 13 |
| mega_evolution | 60 |
| mega_stone | 50 |
| z_move | 37 |
| z_generic | 17 |
| z_status | 20 |
| z_signature | 22 |
| z_native | 9 |
| wild_held_item | 8 |
| battle_recovery | 36 |
| multi_battle | 33 |

## Diagnostics, cleanup and limits

The JSON retains failed exploratory log hashes and diagnoses, including the
missing host mirror dispatch, early reconnect check, legacy moveset callback,
fixture location/metadata assumptions, an overkill-clipped damage control and
a legitimate perfect-IV Bottle Cap no-op. Superseded source runs are excluded
from final qualification. The frozen
candidate includes the fresh human-controller battle guard. Legacy factory/cap
fixture fixes and the moveset callback fix are separate commits from the native
feature. No unrelated compact battle UI work is included.

All test-owned schemas are removed, public schema has no test tables and the
task cluster is stopped. Existing game databases/services and human characters
were untouched. PF2-Dev was inspected read-only: its clean `af0eca6` release has
migrations through 0045, so deploying there would also require the intervening
October migration chain. A [new local release plan](necrozma-release-plan-2026-10-24.md)
keeps that shared environment unchanged and still requires separate approval.

This is local automated acceptance, not an actual socket login, hosted CI result
or shared-server deployment. #831 stays open until the deliberately released
walkthrough and protected-data/fixture cleanup receipts pass. Source availability
still depends on authored content. Plot-only items and Ultra remain excluded.
