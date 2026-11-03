# Training Grounds and nursery delivery — October 29, 2026

Training/retraining and named training supplies are implemented. The nursery allowlist also adds Chesto, Sitrus and Lum, with its four-hour acceptance still running separately. No existing world was installed or refilled.

The player contract is in [Training Grounds](../training-grounds.md). `+train` previews and confirms free 64-EV sessions through three active 30-second steps; resets are free, explicit and confirmed. Six feathers and six EV berries are supplementary Finder rewards; Candy and Caps also have earned session milestones. All existing level, EV, ownership and Hyper Training rules remain in force.

## Verification

| Gate order | Passed | Skipped | Warnings | Seconds |
| --- | ---: | ---: | ---: | ---: |
| combined | 8,164 | 4,032 | 2,142 | 712.99 |
| repeat | 8,164 | 4,032 | 2,142 | 666.93 |
| battle-first | 8,164 | 4,032 | 2,162 | 678.67 |

The canonical mandatory runner used a frozen source copy so later batches could not change the tested tree. Frozen working-file and repository-normalized SHA256 values are in the [machine receipt](training-grounds-delivery-2026-10-29.json). Staged contents are checked against the frozen files after Git line-ending normalization. Warnings are predominantly legacy Django model re-registration. The original-worktree focused run passed 103 checks, with an unwritable pytest-cache warning.

Disposable PostgreSQL passed 94 distinct cases: 16 training/retraining, eight named Finder, 63 nursery and seven legacy Potion Finder cases. Training includes all six stats, useful partial caps, no effect, current Fusion, custody/room/battle/egg/fainted/reservation guards, stale reviews, reconnect, duplicate/concurrent final steps and resets, and real post-EV/reward/reset SQL rollback. The 61-session command replay verifies every six/twelve-session milestone and one Gold at 60; resets do not advance rewards.

One captured ordinary session used unpatched clocks and fresh connections for 90.39 actual seconds. Three spaced inputs produced exactly 64 EVs; waiting alone produced none. This is actual elapsed command/SQL evidence, separate from logged-in sockets.

Native Hardy level-50 Mew was compared in NPC and disposable PvP battles against a level-55 peer. Eight controlled sessions produced 252 Attack/252 Speed: actual Attack/Speed 105→136, Pound damage 16→21 with the same RNG seed, and action order changed from second to first in both modes. A confirmed full reset returned both battles to the original damage and action order. No PvP win is needed to earn training progress.

Finder tests cover every weighted boundary, all 15 real find→bag→use effects, five-percent success/failure boundaries, mixed/unknown source refusal, cooldown, replay, reconnect, post-credit rollback and competing claims. Legacy Potion behavior also passed its seven database cases. Rolls are controlled in these cases; they do not establish random acquisition in a deployed public world.

Nursery tests cover all 16 watering masks for each of three seeds, original timer/yield rules, stale selections, rollback, concurrent operations and paid source travel without stock refill. The separate actual four-hour driver remains running after its first hourly checkpoint; #948 stays open pending its harvest/use and cleanup. The eight-seed allowlist changes no timer or yield.

The initial broad run identified a registry-test fixture missing CmdTrain and unescaped literal pipes in two help groups. The fixture now tests CmdTrain registration with alpha enabled and disabled, and help pipes are escaped; the three fresh gate orders above passed afterward.

## Source and release limits

Training Grounds/Trail and day/night grove recipes require an explicit selected hub. The Chesto source is finite 200×5, while Sitrus/Lum keep their existing source policy. A separate Link Cord counter recipe plans finite 10,000×20 stock using the existing reference price, with no refill or resale; it performs no automatic evolution or extra held-item requirement. Authoring is not installation.

No shared-world installation, migration, restart, deployment or human-character/Pokemon change was performed. Later Soothe Bell, contextual evolution guards, Mirror Herb and NPC-prize work is outside this tested commit. Hosted CI for previous source is tracked separately and is not asserted green by these local results.
