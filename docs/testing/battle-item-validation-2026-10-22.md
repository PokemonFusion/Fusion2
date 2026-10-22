# Battle item validation acceptance - October 22, 2026

Issue: #766. Source baseline: `ecc7b38894573320d53cd8e99615406d4d2413c1` on `staging`.

Unsupported manual battle items now fail before an actor is reserved, a declaration is persisted, inventory is debited or the turn advances. A single capability policy recognizes the existing 21 battle medicines and real capture-ball metadata, with balls still restricted to wild battles. Fresh Water and Oran Berry retain their field routes; Smoke Ball retains +hold/+flee. No new manual battle feeding is added.

The command, PlayerChoices, compatibility queue, restored declarations, deferred pending/PositionData views, engine pre-turn check and final dispatch use the same policy. Invalid old choices are removed from both saved declaration views before readiness, preserving valid sibling actions. Direct engine entry rejects invalid pending items before counters, conditions, transformations, opponents or residual effects can advance.

## Current proof

- **22 new PostgreSQL cases** run actual +item input with persistent bag/target rows and production BattleSession, queue, engine and rebuild code. They cover stocked Fresh Water/Oran rejection; capacity/progression/held/unknown items; direct choices and public queues; supported Potion, reserve Revive, selected Ether, Elixir/Max Ether and Master Ball; no-effect/stock policy; actor ownership; doubles siblings; repeated rebuilds; stale captures; and null/empty deferred/final dispatch guards.
- **419 PostgreSQL cases total** passed: battle_item_validation 22; smoke_ball 17; player_doubles 10; battle_recovery 36; pp_capacity 37; name_resolution 8; capture_ether 21; status_item 9; rare_candy 25; field_item 23; field_berry 26; field_food 70; remaining_item 8; capture_pp_item 16; leader_crest 29; evolution 28; progression 11; cloud_gameplay 9; ui 14.
- **324 focused pytest tests** passed, including command/queue/turn/restore/capture, Smoke Ball, PP, field and import-isolation checks.
- **Mandatory fresh-process gate:** combined: 4624 passed / 4014 skipped; repeat: 4624 passed / 4014 skipped; battle-first: 4624 passed / 4014 skipped.
- **968 frozen Python files** remained unchanged during final verification. The JSON pins 40 relevant source/test/workflow/help hashes for comparison with committed blobs.
- **28 ordinary command/SQL observations** retain input, messages, pending/declaration/PositionData views, turn counts, inventory/cache, complete SQL Pokemon/move/placement rows and capture receipts.
- Passing results include warnings in local logs; the report does not claim a warning-free environment.

## Ordinary player routes

Disposable setup creates tagged normal User characters, canonical party members and real Trainer.add_item stock. A controlled Splash-only wild opponent keeps injury/cure/revival/PP assertions deterministic. Setup is separate from player acceptance; successful effects use the production command, choices, queue, transaction and engine implementations.

With an injured target, +item Fresh Water and +item Oran Berry (including explicit A1/target syntax and normalized spelling) leave all recorded state unchanged. The next +item Potion still uses turn 1, heals 1 to 21, and debits stock 2 to 1. A supported full-health Potion intentionally advances one turn without a debit, preserving the existing distinction between supported no-effect use and an unsupported item.

Reserve Revive restores the actual fainted slot, selected Ether restores only Water Gun, and Elixir/Max Ether retain raw PP capacities through rebuilds. Master Ball still catches and saves exactly one wild Pokemon after a rejected item and rebuild. Trainer/PvP balls are rejected without an action. Doubles inputs require owned acting slots: invalid A2/B2 items preserve A1/B1, and a bad restored A2 item leaves A1 Splash queued to spend PP exactly once.

Legacy unsupported declarations are discarded before restored readiness, including a second rebuild. Orphan pending/PositionData views cannot bypass the policy. Session turn entry discards stale items; direct engine turn entry raises before turn start; final dispatch logs rejection without changing Pokemon, inventory or capture state. Existing Smoke Ball restore coverage now requires early discard rather than constructing a harmless no-effect item action.

## Scope and evidence limits

The [JSON report](battle-item-validation-2026-10-22.json) embeds command/SQL walkthroughs, exact test commands, durations, log hashes, source hashes, fixture diagnoses and cleanup. Raw logs remain under ignored .codex-artifacts/battle-item-validation-20261022/.

This is local automated production-command/session/model acceptance with captured transport and private PostgreSQL. It is separate from a fresh Telnet/WebSocket login, hosted CI completion, main merge, deployment or live stock audit. No existing game database, human character, game service or migration runner was used. Disposable schemas were removed and the private test cluster stopped.

The completed Rare Candy and PP-capacity repairs, field foods/berries/medicine, supported battle effects, capture and held escape regressions passed. No plot-only content, new item definitions, unrelated WIP or manual battle food/berry expansion is included. The lifecycle workflow now runs the new PostgreSQL suite; its future hosted result is not asserted here.

Preliminary failures were fixture/runner setup errors, including incorrect constructor use, stale HP setup through Evennia identity caching and observing a session after capture ended it. Corrections preserve required effect expectations. Only final frozen-build results count as acceptance.
