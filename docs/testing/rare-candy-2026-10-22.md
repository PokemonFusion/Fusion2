# Rare Candy field-use acceptance — October 22, 2026

Issue: #764. Source baseline: `d4450420a5905e9c379ca619796e4b2ef22139fa` on `staging`.

Rare Candy now uses the shared field-item storage/trainer/Pokemon lock and validation boundary. A successful `+use` consumes one bag item and commits one next-level EXP threshold, saved level and level-up learning together. A failed debit/write/learning operation commits none of them. Full-moveset prompts and success messages are deferred until commit; a UI transport failure cannot undo or misreport a committed use.

Targets retain canonical gapped party slots, full UUIDs, unambiguous names and the actual reserved current Fusion (`fusion`/`self`/`me`). Eggs, boxes, foreign ownership, inactive reservations, battle locks, inconsistent saved EXP/level and level 100 are rejected without consumption. Intentional subsequent uses remain valid; one final bag copy cannot fund two concurrent gains. Existing HP/status/friendship/held-item and level-trigger behavior is preserved.

## Current proof

- **25 new PostgreSQL cases** exercise real `+use`, inventory/party discovery, ordinary deposit, SQL reload, current-Fusion aliases, ambiguous/foreign/stale targets, caps, partial EXP, learning, rollback, real EvMenu, postcommit UI failure and two independent-connection contention cases.
- **259 PostgreSQL cases total** passed: rare_candy 25; field_item 23; field_berry 26; field_food 70; remaining_item 8; capture_pp_item 16; leader_crest 29; evolution 28; progression 11; cloud_gameplay 9; ui 14.
- **162 focused pytest tests** passed. The exact selection/commands, durations and output hashes are in the [JSON report](rare-candy-2026-10-22.json).
- **Mandatory fresh-process gate:** combined: 4596 passed / 4014 skipped; repeat: 4596 passed / 4014 skipped; battle-first: 4596 passed / 4014 skipped.
- **963 frozen Python files** remained unchanged during the final checks. The JSON pins 28 relevant source/test/workflow/help hashes using normalized LF text for committed-blob comparison.

## Ordinary player flow

Fixture setup creates tagged disposable characters and actual bag stock through the production inventory writer. Setup is separate from acceptance. Ordinary commands then discover the item with `+inventory` and the full ID with `+party 3`, use `+use Rare Candy=3`, rebuild captured session transport and use `+use Rare Candy=<full ID>` for a second paid level. Both inputs, messages and SQL before/after states are retained in JSON. Name/legacy target-first syntax, current Fusion, partial-EXP and level-up-learning flows are separately retained.

The free-level audit reproduction now leaves EXP, level and stock unchanged when consumption fails. Additional tests fail after a real debit, level save and move-learning writes, proving rollback rather than replacing success effects. A normal box deposit or stale owner/egg/placement cannot bypass the fresh checks. The existing Leader's Crest suite still qualifies Bisharp through real victories, uses Rare Candy for the next level, and evolves normally.

## Limits and preservation

This is automated local production-command/model acceptance on a private loopback PostgreSQL fixture, with captured session transport and actual EvMenu. It is not a fresh Telnet/WebSocket login, hosted CI result, main merge, public deployment or a statement about live Rare Candy availability. No game database, existing human character, running game service or migration runner was used. Disposable schemas were removed and the private test cluster stopped.

PP Up/PP Max remain unchanged for #765. Medicine, berry and food regressions passed; no battle runtime, generated dex data, new items or plot-only content is included. The lifecycle workflow runs the new production-model suite on future CI runs.

Preliminary fixture/bootstrap failures and the robust-callback logging correction are retained in local logs and diagnosed in JSON. Only the final frozen-build results above are acceptance evidence. Raw logs/fixture tools are local under `.codex-artifacts/rare-candy-20261022/`; the committed JSON embeds walkthrough state and exact commands/output hashes without credentials.
