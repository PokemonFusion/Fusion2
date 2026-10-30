# Tagged Fusion cleanup supplement (2026-10-26)

**Proposal only.** This supplements the [approved remaining-item plan](remaining-item-release-plan-2026-10-26.md)
for **4347e76b046d2c59bd8bcf1eabe3535ebeaa95a9**, #904 and its exact four ordinary QA Players. The
approved release/migration/counters and two Evennia stop/start cycles remain
unchanged. The release is already independently verified at0059; this document
does not request or perform another migration, source release or extra restart.

The ordinary Fusion walkthrough exposed a mismatch in my original plan:
`+unfuse` correctly preserves a permanent unlocked form, while the reviewed
cleanup accepts only party/box placements. There is no ordinary permanent-form
forget command. A legitimate initial Fusion source therefore remains reserved
after returning to human form. Do not rewrite gameplay or bypass the old guard.

## Exact bounded change

Keep **all six originally reviewed controller files byte-identical**, including
`cleanup.py`. Add only the reviewed `cleanup_fusion.py` from the
[complete source and four-case SQL receipt](remaining-item-fusion-cleanup-supplement-2026-10-26.json).
Its UTF-8/LF SHA256 is **`0bd383dff2fa3eee8431bd41c0284269cdb5d5b4aeee8a4f05bb67fa13aea2a7`**.

The new controller retains every original tag/identity/custody/occupant/held-item/
closed-history/collector/all-other-row comparison. It additionally accepts a
reserved Fusion placement only when the **same exact tagged QA owner's** fresh
`FusionTransitions.inspect()` proves no active form, no custody/reference
problems, matching owned UUIDs and exactly matching saved unlocked forms.
Active, orphan, mismatched or foreign forms still refuse atomically. It deletes
only the already approved new QA identities, their owned sources/private world
and exact closed histories. Permanent counters, finite sales, original sources
and all pre-existing human data remain protected.

The four isolated cases passed: ordinary exact cleanup; unfamiliar-occupant
refusal; active Fusion refusal followed by actual ordinary +unfuse then safe
inactive-form cleanup; and foreign-form refusal with every object/owned row
preserved. Two initial fixture-import errors are retained separately. These are
new disposable local model tables, with no migrations or shared-game deletion.
The application build remains the original qualified1,188-file candidate.

## Execution after separate explicit approval

1. Record the actual supplemental human response and exact controller SHA in
   private `fusion-cleanup-approval.json` under
   `/home/evennia/testing/.remaining-items-20261026-2259c9`. The JSON approval template remains false until
   that response. Stage the exact new controller without changing the six old
   files or their original approval/plan hash.
2. Finish the approved ordinary flows, use ordinary `+unfuse` to return the Fusion
   QA character to human form and log out all four. Require no active native
   pairs, battles, held items, open ownership/Daycare/breeding work or unfamiliar
   occupants, and preserve all original baseline checks.
3. During the **already approved second guarded Evennia stop/start cycle**, after
   proving allfive instance ports closed, run exactly
   `/home/evennia/testing/evenv/bin/python3 -B /home/evennia/testing/.remaining-items-20261026-2259c9/cleanup_fusion.py --cleanup-approved`
   in `/home/evennia/testing/fusion2` with the original reviewed environment.
   Its original `authorize()` still validates the approved build/database/plan
   and all six old controller hashes, followed by its separate supplemental
   approval and own source hash. It writes the same one-use cleanup receipt;
   never run both cleanup controllers.
4. Require the unchanged all-other-row digest, no remaining tagged QA, permanent
   sales intact, and original same-build start/independent health checks.
   Refusal preserves everything for review; no automatic repair follows.

The [original approved plan](remaining-item-release-plan-2026-10-26.md) explicitly
pins **"every controller hash"**. This proposed helper changes that reviewed
cleanup behavior, so I am requesting supplemental approval before running it.
No existing human fixture, additional account, stock/refill, migration, package,
gameplay edit, plot-only item or unrelated work is included.
