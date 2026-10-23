# October Fusion verification (#723, #722 compatibility)

October 23, 2026 candidate based on `b67d12a`. The [JSON record](october-fusion-2026-10-23.json)
contains commands, immutable source/log fingerprints and captured command/state
evidence. These are fresh local automated checks with actual PostgreSQL models
and player typeclasses. They do not certify a live server or deployment.

## Acceptance evidence

| Criterion | Evidence |
| --- | --- |
| Complete atomic transitions | Actual temporary activation, permanent unlock, unlocked switch and unfuse; fault after EXP/view writes restores the previous form, references, EXP and canonical placements. |
| No repeated unlock EXP | Exact request replay after cache discard/reconnect, separate repeated unlocks and concurrent unlocks preserve one award. Existing fighter EXP aliases remain coherent. |
| Temporary source return | Preferred canonical slot retained; another free slot or a box handles conflicts/full parties. UUID, HP/status and PP remain intact. |
| Shared reservations and contention | Independent connections race different activations, activation/unfuse, release/storage and consent-transfer preparation. System claims and battle state are checked under the common lock boundary. |
| Reconnect and runtime view | SQL-backed owned references, kind and EXP survive cache discard. Unfuse clears cached battle annotations from the returned source. Existing growth/boost rules are retained. |
| Fresh target/character authority | Source slot, bond, egg, held item and breeding flags rechecked; a command target changed after preflight is rejected. Actual same-account characters cannot supply foreign sources/forms or act on another character's transfer. |
| Ordinary player flow | Recorded `+fuse/temp`, `+unfuse`, `+fuse/permanent ... confirm`, `+fusion` selection and repeat unfuse on actual User models with Player permission. Outbound transport captured; staff/fault/operator fixtures are separately labelled. |
| Staff inspection/recovery | Shipped read-only CLI, stale-fingerprint refusal, receipt/note for reference-only recovery, and refusal to guess an unreferenced owned reservation. No Pokémon ownership or progression repair is inferred. |

## Final local verification

- **253 passed across 12 PostgreSQL suites**, including 22 dedicated Fusion cases
  and 21 explicit durable-write fault boundaries,
  ownership, placement, evolution, medicine, berries, abilities, progression,
  doubles, gyms, battle recovery and UI.
- **41 focused tests passed** for Fusion commands, chargen compatibility, sheet,
  growth and boost behavior.
- Three-order mandatory gate: **4909, 4909, 4909 passed**, respectively, with 4,014 skipped
  in each fresh process; callbacks enabled and ambient pytest options cleared.
- Approved fresh/upgrade/guarded-invalid-data migration rehearsals pass again.
  This cohort adds no migration; Fusion receipts reuse persistent Attributes.
- **1046 Python files** held fixed across the gate, with raw source hashes
  in JSON and a Git-filtered blob fingerprint added before committing.
- `git diff --check` passes. Existing import/deprecation/log warnings remain
  diagnostic limits; no warning-free operational claim is made.

The final full-suite gate also includes the dedicated Fusion subprocess. During
development, one race fixture reused an occupied party slot across two scenarios;
the fixture now releases only its own known source between scenarios. This was
separate from the cache-annotation defect that received a production repair.

## Compatibility and limits

Known older permanent starters recorded in party remain owner checked and battle
usable. Their next atomic Fusion transition reserves that exact existing source,
with no new EXP or HP/PP reset. Storage/release/transfer cannot bypass those
references, including alternate UUID spelling. This closes the compatibility
follow-up recorded in the [ownership foundation report](october-ownership-2026-10-23.md).

Full onboarding remains #730. Unknown kinds, orphan reservations, invalid owned
placements and malformed form-list state still require deliberate review. The
[operator contract](../operations/fusion-transitions.md) limits automatic recovery
to reviewed invalid references and never invents ownership or returns another
character's Pokémon. No existing game characters, migrations, services or
Adventure-room setup were touched. Plot-only assets and unrelated work are excluded.
