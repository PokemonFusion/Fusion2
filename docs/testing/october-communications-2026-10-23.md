# October communications implementation verification (#732)

October 23, 2026 candidate based on `610876e`. [JSON evidence](october-communications-2026-10-23.json)
records commands, fixture boundaries and source/log fingerprints. **Live ordinary
game acceptance remains pending; #732 stays open.** Tests use actual typed
Player characters/accounts and real persisted Msg, Script, channel and tag rows.
Outbound transport and editor presentation are captured; command/service writes,
permissions, subscriptions and rollback boundaries are real.

## Implemented evidence

| Criterion | Evidence |
| --- | --- |
| Mail routes | Normal recipient lookup finds the actual User typeclass. Send, read, reply, unread and archive use the caller character; foreign IDs and raw account actors cannot consume another character's inbox. |
| Independent state | Shared messages retain recipient-local read/unread overrides and hide/archive state. Independent connections preserve both readers. Reply failures roll back both the new message and old unread state; notification failures do not lose committed mail. |
| Boards | Persisted Saver mappings render correctly. Script-row serialization protects posts and read maps; rollback refreshes cached Attributes. New stable post IDs prevent deleted positions from inheriting unread history. |
| Stale editors | Opening captures a stable post ID; save checks fresh access and identity. A deleted/replaced post or revoked staff privilege cannot overwrite a different post. |
| Channels | Command identity comes from the real session and verified puppet ownership. Foreign/stale/ambiguous sessions use marked account identity. Current listen permissions are rechecked for persisted subscribers, while mutes and recipient hooks remain effective. |
| Account separation | Same-account alternates and a separate account retain independent inbox and board state. Account selector unread counts include owned characters only. Staff setup is separate from ordinary Player evidence. |

## Final automated checks

- **211 cases pass across 14 PostgreSQL suites**, including
  **17 dedicated communications cases** and ownership, onboarding, trade, market,
  Daycare, breeding, gyms, battle and UI regressions.
- **47 focused checks pass** for communications,
  account/roster views, command aliases, guidance and help formatting.
- One callback-enabled full suite: **4921 passed / 4014 skipped**.
- **1090 Python sources** remain fixed across final checks. Staged
  Git-filtered fingerprints are added before commit; `git diff --check` passes.
- No model/schema changes or new migration rehearsal for this feature.

See [operations and legacy limits](../operations/communications.md). Historic
shared-message recipient activity cannot be recovered from the old global flag;
untouched recipients keep that baseline until their own action. Existing Windows
logging/model-reload diagnostics remain. No plot items, unrelated work, deployment
or existing game service/database change is included.
