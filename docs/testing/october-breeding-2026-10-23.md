# October breeding verification (#728)

October 23, 2026 candidate based on `7016524`. [JSON evidence](october-breeding-2026-10-23.json)
contains exact commands, assertions, source fingerprints and test log hashes.
These are local automated checks using actual User/Account models and Player
permission on task-owned PostgreSQL schemas. Outbound transport is captured;
live sockets, deployment and hosted CI success are not claimed.

## Acceptance evidence

| Criterion | Evidence |
| --- | --- |
| Ordinary route | `+daycare deposit`, `+breed check/start`, status, collect and hatch preserve one planned owned UUID through reconnect. Early requests refuse without changing deadlines or outcome. |
| Costs and timing | One 500-money fee, 30-minute readiness, 24-hour parent cooldown and 20-minute hatch readiness. Time-controlled fixtures are explicit; commands never advance time. Cancellation preserves cost, cooldown and plan. |
| Trait audit | Real dex/Gen 9 learnset tests cover ordinary/Ditto compatibility, incense-free babies, nature, ability slots, genetic IVs, Destiny Knot, Power items, Hyper Training separation and moves. Unsupported families/forms fail before payment. |
| Concurrency and faults | Independent connections race start, collect and hatch. Post-fee, post-egg and post-hatch receipt faults roll back money, claims, owned rows and in-memory flags. Retry reuses the same identities and outcome. |
| Current ownership | Consent-traded eggs hatch only for their current owner, including boxed eggs. Foreign and same-account alternate characters cannot claim another cycle. Full-party collection uses a box; release/replay never recreates an egg. |
| Egg restrictions | Actual PvP request and field Potion commands reject an egg before request allocation or inventory debit. Eggs remain unavailable for Fusion, battle or Daycare parenting. |
| Staff and schema | Read-only `audit_pokemon_breeding --cycle ID` and Daycare inspection identify the exact cycle/parents/egg. Deferred checks and sealed records reject plan/cooldown/custody/hatch tampering; historical identities survive release. |

## Final checks

- **253 cases pass across 14 PostgreSQL suites**, including
  **13 dedicated breeding cases** and existing custody, transfer, field item,
  doubles, gym and UI routes.
- **23 focused checks pass**, including a fresh
  subprocess for six actual-dex inheritance cases to avoid legacy fake catalogs.
- One fresh callback-enabled full suite: **4919 passed / 4014 skipped**.
- Six approved isolated migration rehearsals pass: fresh, upgrade and invalid
  reservation, marketplace, Daycare and breeding rollout/rollback. The invalid
  breeding plan blocks installation without partial checks; deliberate QA-row
  removal permits retry. Model drift is empty.
- **1076 Python sources** remain fixed across final checks. The staged
  Git-filtered blob fingerprint is added before commit; `git diff --check` passes.

See [breeding rules and recovery](../operations/breeding.md) for policy, canonical
references and explicit exclusions. Guaranteed production, costs, wall-clock
timing, box hatching and friendship 100 are PF2 beta policies. This adds no plot
items, passive EXP/healing, hatch-step grind, Masuda/Charm modifiers or special
form inheritance. Existing Windows logging/model-reload diagnostics remain;
no unrelated logging, service or live-character changes are included.
