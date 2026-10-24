# October onboarding implementation verification (#730)

October 23, 2026 candidate based on `cc25b15`. [JSON evidence](october-onboarding-2026-10-23.json)
records callbacks, commands and source/log fingerprints. **Website and live game
acceptance remains pending; #730 stays open until that journey is recorded.**
Local tests use actual typed User/Account models and Player permission on
task-owned PostgreSQL schemas. Outbound transport and the menu-opening constructor
are captured; callbacks, grant writes and Evennia character creation are real.
Standalone command/session facilities are bound without starting game services.

## Implemented evidence

| Criterion | Evidence |
| --- | --- |
| Self-service policy | New beta setup needs no Validator/Builder approval. `chargen` explains the policy, resumes accepted choices and closes after its durable receipt. Legacy validation/setup/progress markers never grant another free starter. |
| Human and Fusion paths | Human completion creates one level-five starter with initialized moves, calculated HP and canonical placement. Initial personal Fusion creates one reserved form, full initial level-five fighter XP and valid form references, with no second starter. |
| Resume and reviewed choices | Menu callbacks save accepted choices. Abort/runtime cache discard resumes the next required node. Final confirmation compares the reviewed choices with the fresh saved draft under the character lock; an older Squirtle review cannot grant a replacement Bulbasaur. |
| Atomicity and retries | Separate connections race final confirmation and receive one identical receipt. Fault after actual receipt insertion rolls back owned rows, placement and character/Fusion attributes together while keeping the draft. Repeated finish and later release cannot recreate a grant. |
| Character ownership | Two characters on one account and a separate account retain separate owner rosters, trainer/storage, receipts and owned UUIDs. Raw account authority is refused. Actual create-character hooks initialize the configured starting room and empty trainer/storage before setup. |
| Number allocation and inspection | Missing-trainer initialization uses saved maximum, not count. A real unique-number failure inside an outer transaction rolls back its savepoint and retries successfully. Read-only staff inspection preserves draft, owned and receipt counts. |

## Final automated checks

- **194 cases pass across 13 PostgreSQL suites**, including
  **15 dedicated onboarding cases**, canonical custody, ownership/Fusion, trades,
  marketplace, breeding, gyms and existing player routes.
- **41 focused checks pass** for menu/starter,
  roster/storage, guidance, command registration and help formatting.
- One fresh callback-enabled full suite: **4920 passed / 4014 skipped**.
- Six approved isolated migration rehearsals pass through
  `0056_onboarding_completion`, including invalid-data rollback and zero model drift.
  These rehearsals precede the final reviewed-choice/fixture-only edits; that
  change does not alter the model or migration chain.
- **1085 Python sources** remain fixed across final checks. Staged
  Git-filtered source fingerprint is added before commit; `git diff --check` passes.

See [policy and recovery](../operations/onboarding.md). The obsolete fake-only
Fusion-finish test now runs real isolated persistence coverage; pure menu tests
capture their persistence seam separately. Existing Windows logging/model-reload
diagnostics remain. No plot items, new currency, website redesign, existing game
database/service change or deployment is included. The final integrated October
battle work retains a separate three-order regression gate.
