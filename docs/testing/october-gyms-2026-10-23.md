# October authored gym verification (#729)

October 23, 2026 candidate based on `141474b`. [JSON evidence](october-gyms-2026-10-23.json)
records exact commands, source/content/log fingerprints and separate fixture limits.
Local automated tests use actual User/Account records with Player permission and
task-owned PostgreSQL schemas. Outbound transport is captured; the standalone
search facade resolves real ORM dbrefs. No live sockets, deployment or hosted CI
success is claimed.

## Acceptance evidence

| Criterion | Evidence |
| --- | --- |
| Reusable author path | The same strict JSON parser and atomic installer load Tempo doubles/Trick Room/24-hour cooldown and optional validation singles/basic gym AI/one-badge prerequisite/zero cooldown. No gym-specific battle branch is added. |
| Validation before allocation | Unsupported format, AI, strategy, reward policy, unknown fields, bad bounds/native ability/moves/genetics and direct installed-row drift refuse before encounter allocation. The author command supports read-only `--check` and actionable errors. |
| Ordinary route | Actual `+gym check/challenge/claim` with an ordinary User agrees with selected singles format, eligibility and authored rules. Legal engine declarations win first clear and immediate practice; one badge and no repeat money, items, XP or EV rewards. Concession awards nothing and allows retry. |
| Version/rebuild/reward | A launched encounter keeps its full definition, version, fingerprint, old team and AI through real room-checkpoint rebuild after a higher-version installation. An injected post-badge-write delivery failure rolls back and the old saved victory remains claimable once through `+gym claim`. |
| Idempotency and recovery | Exact repeat and independent-connection concurrent installation preserve trainer/profile/badge/team identities. Same-version replacement, downgrade and reward identity reassignment are refused. A fault after a real roster write rolls back the entire version. Unknown/duplicate roster rows require review. |
| First production gym separate | The original ten-case Tempo suite still exercises its full strategy, first clear, practice cooldown, loss/concession, pending recovery and concurrent launch. The additional ten-case authoring suite proves configuration separately; #712 remains the first-gym tracker. |

## Final checks

- **225 cases pass across 16 PostgreSQL suites**, including
  ten new authored-content cases and ten original Tempo production-gym cases.
- **76 focused checks pass** for gym policy,
  discovery/commands, trainer generation, seed/admin/rewards and help formatting.
- One fresh callback-enabled full suite: **4920 passed / 4014 skipped**.
- Six approved isolated fresh/upgrade/invalid-data migration rehearsals pass
  through `0055_gym_content`; model drift is empty. Existing unversioned gyms
  retain compatibility until deliberate installation.
- **1080 Python sources** and both authored JSON definitions remain fixed
  during verification. Staged Git-filtered source fingerprint is added before
  commit; `git diff --check` passes.

See [authoring and recovery](../operations/gym-content.md) for supported rules,
version updates, identity conflicts and install commands. Presentation prose
describes supported rules; it does not execute arbitrary battle clauses. Validation
singles is optional QA content and Tempo seed never installs it automatically.
No full league, plot items, new AI strategy or reward ledger is added. Existing
Windows log-rotation/model-reload diagnostics remain without unrelated changes.
