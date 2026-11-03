# Remaining bounded item deliveries — October 29, 2026

Contextual evolution access, Soothe Bell feeding, Mirror Herb teaching and standard NPC prize items are implemented. This is a local/private acceptance receipt. No existing world was installed, refilled or deployed.

The [player contract](../contextual-and-field-items.md) gives exact commands, prerequisites and limits. Optional finite sources are authored recipes; Day/Night Groves, Training Grounds/Trail and the teaching Classroom require explicit placement.

## Verification

| Mandatory order | Passed | Skipped | Warnings | Seconds |
| --- | ---: | ---: | ---: | ---: |
| combined | 8,187 | 4,032 | 2,142 | 707.81 |
| repeat | 8,187 | 4,032 | 2,142 | 702.99 |
| battle-first | 8,187 | 4,032 | 2,162 | 698.4 |

The canonical runner used a frozen source copy; all committed runtime/test/tool files match that candidate. The [machine receipt](remaining-item-delivery-2026-10-29.json) records working-file and Git-normalized fingerprints. Focused checks passed 47; the original worktree produced one unwritable pytest-cache warning. The mandatory gate retains its legacy skipped tests and warnings.

Disposable PostgreSQL passed 230 distinct cases: five contextual, six Bell, seven Herb and 15 prize cases, plus 197 evolution/trade-held/Link Cord/Alcremie/training/Finder regressions. These use production parsers/services and captured command transport, separately from actual sockets. Tests create model tables in random private schemas without running migrations, then remove those schemas.

Contextual cases cover actual exit commands, paid finite offers, level 1/50/100, wrong-time and native branches, actual saved position/flags, custody/egg/Fusion/battle/reservation guards, retry, real post-save rollback and concurrent evolution. Bell cases cover all six berries and tiers/caps, held-versus-bag and stale state, useful Golbat 153→160→Crobat, unchanged herbal penalties, current Fusion, Klutz, real rollback and final-copy contention.

Herb cases cover evolved/regional native ancestry, exact verified Gen 9 egg moves, actual donor knowledge at zero PP, one empty active and saved-set slot, no fee/item consumption, existing PP preservation, stale confirmation, ownership/reservations, duplicate/concurrent confirmation and real post-write rollback. Taught Wish survives PvP reconstruction and spends 10→9 PP without refreshing an old Tackle or the donor's zero PP. The [pinned Gen 9 reference](https://github.com/rh-hideout/pokeemerald-expansion/blob/8654616bd38d9b28cc7dd8f3d0b4cb030aa2d40c/src/daycare.c) supports native egg-species resolution, an empty slot and reusable Herb transfer without breeding compatibility.

Prize cases use real standard NPC KOs and unchanged base money, both names, nonstacking, bench/loss/zero and mode/source exclusions, genuine Trick timing, Explosion ending before later participation, fainted qualification, checkpoint reconstruction, current custody, paid source/equip/use, immutable pending payout and competing claims. Real post-wallet and whole-turn post-sync failures roll back the corresponding writes; ordinary retry pays once. Klutz does not suppress this physical prize condition.

## Actual private socket acceptance

An ordinary nonstaff account sent 100 inputs through actual loopback Telnet, Portal/AMP, Server and shipped command/session classes. No clock or RNG was patched. Prepared fixture prerequisites and staff setup are separate from ordinary inputs. Processes stopped before private-schema cleanup.

The player bought 14 Link Cords for 140,000, evolved all exact targets with one-copy debits, reconnected and repeated completed requests without further spending. Alolan form and all Pumpkaboo sizes were preserved. The separate 29-case SQL suite proves Karrablast/Shelmet independently without the other species; the all-14 socket cohort owns both and makes no independent-bug proof claim.

Training took 90.45 actual seconds with three active spaced inputs and a reconnect mid-session, earned exactly 64 Attack EVs, then returned to zero through a free confirmed reset. Paid contextual items produced Chansey, Weavile and Gliscor after actual public exit travel; wrong-time Happiny retained its held stone. A bought Bell plus a prepared useful berry took Golbat 153→160→Crobat while retaining the Bell.

The player reviewed native Umbreon/Jirachi Wish teaching, reconnected before confirmation, learned one Wish at 10 PP, preserved old Tackle 1 PP and donor Wish 0 PP, and repeated confirmation without a refresh or copy. Herb/donor acquisition was prepared, not publicly sourced.

The first uncontrolled Training Trail find was Pomeg Berry after 4 ordinary attempts; the player used that found copy. This is one observed random route, not a statistical estimate of its rate. A separately bought Coin earned the sealed standard NPC prize payload 40×2=80; reconnect and reward retry paid no extra money.

## Diagnoses and remaining boundary

Actual socket discovery exposed an authoring defect missed by direct traversal tests: clearing exit locks removed Evennia call access even though exits looked public. New sources preserve default security locks; retry checks call/view/traverse and refuses drift. SQL checks now cover call access without superuser bypass and do not silently repair drift. The earlier in-progress mandatory run was stopped when this source changed; only the three corrected-candidate runs above count as final verification.

Contextual evolution also now reads persisted room context instead of stale wrapper fields and rejects invalid saved levels. Prize work found that new field/prize metadata needed inert runtime item objects for ordinary physical transfers; no competitive callbacks were added. Fixture-only setup failures and expected injected SQL failures are retained privately and distinguished from these production defects.

The [refreshed source-only index](item-availability-final-index-2026-10-29.json) contains 649 definitions / 501 scoped entries, 47 Mega pairs and 69 Z mappings across 35 crystals. Every current-world availability entry remains unverified. Coarse capability labels do not certify every facet. Cleanse Tag/Pure Incense encounter reduction, broader Z mappings/berries, companion/donor access and other historical limits remain explicit. Historical reports and stock observations are unchanged.

The actual four-hour nursery driver remains separate under #948 until harvest/use and cleanup pass. Hosted CI and staging publication are recorded separately from these local results; no shared service was restarted and no deployment, stock refill or game-database migration occurred.
