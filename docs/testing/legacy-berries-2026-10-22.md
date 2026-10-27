# Legacy recovery berry acceptance - October 22, 2026

Issue: #767. Source baseline: `f6e042a11c8b9984a11e23fa17993d4eca722fe2` on `staging`.

Nine existing legacy recovery berries now work through ordinary `+use`. They reuse FieldMedicineUse's fresh owned-party/current-Fusion eligibility, placement/trainer locks, medicine effects and PP restoration. Failed berry debits raise inside that transaction, including a writer that changes inventory before returning failure. No new definitions or held callbacks are added.

## Reviewed field effects

| Item | Effect |
| --- | --- |
| Berry | Restore up to 10 HP |
| Gold Berry | Restore up to 30 HP |
| Burnt Berry | Cure freeze only |
| Ice Berry | Cure burn only |
| Mint Berry | Cure sleep and clear saved sleep turns |
| Miracle Berry | Cure paralysis, sleep, poison, toxic poison, burn or freeze |
| Mystery Berry | Restore up to 5 PP to one current active move |
| PRZ Cure Berry | Cure paralysis |
| PSN Cure Berry | Cure poison or toxic poison |

The [primary reference item implementation](https://github.com/smogon/pokemon-showdown/blob/master/data/items.ts) was reviewed for the explicit mappings. Burnt thaws freeze and Ice cures burn. Existing PF2 held Burnt also cures burn; held PSN Cure handles ordinary poison only. Those held differences are unchanged and documented separately from the field policy. Miracle cures saved major status; Bitter/Persim only cure battle confusion and remain outside field feeding.

## Current proof

- **26 new PostgreSQL cases** cover each of the nine inventory/party/use/reload flows; exact normalized names and legacy inventory aliases; fixed HP and caps above held thresholds; every persistent status and wrong-status no-effect; current Fusion; real gapped move slots, names, default selection and boosted PP caps; target/battle/stock/egg/box/reservation/ambiguity guards; held-copy independence; failed and partial debits; post-write rollback/cache recovery; last-copy concurrency for every berry; and terminal HP contention.
- **445 PostgreSQL cases total** passed: legacy_berry 26; battle_item_validation 22; smoke_ball 17; player_doubles 10; battle_recovery 36; pp_capacity 37; name_resolution 8; capture_ether 21; status_item 9; rare_candy 25; field_item 23; field_berry 26; field_food 70; remaining_item 8; capture_pp_item 16; leader_crest 29; evolution 28; progression 11; cloud_gameplay 9; ui 14.
- **530 focused pytest tests** passed, retaining held berry/runtime regressions, field food/medicine, PP-capacity, inventory, battle input/queue/turn, capture and prior evolution checks.
- **Mandatory fresh-process gate:** combined: 4624 passed / 4014 skipped; repeat: 4624 passed / 4014 skipped; battle-first: 4624 passed / 4014 skipped.
- **969 frozen Python files** remained unchanged during final verification. The JSON pins 36 relevant source/test/workflow/help hashes for staged and committed-blob checks.
- **65 command/SQL observations** retain actual input, messages, complete Pokemon/placement/move/boost rows, bag quantities and inventory cache before/after use.
- Passing runs include local dependency warnings; this report does not claim a warning-free environment.

## Ordinary player routes

Disposable setup creates a normal User owner, a level-50 Mew in canonical party slot 3, actual Tackle/Water Gun active slots 1/4, and real bag stock. Each legacy berry is shown through `+inventory` and `+party 3`, used with `+use <full item name>=3`, then checked through independently read SQL and after closing database connections and flushing the owned-model identity cache. Successful effects and placement/consumption use production code.

Berry heals 1 to 11 HP; Gold heals 1 to 31. Both cap at calculated maximum HP and leave fainted/full-health targets unchanged. Burnt only thaws freeze, Ice only cures burn, Mint clears sleep and saved turns, Miracle handles all six major status codes, PRZ cures paralysis, and PSN cures normal/toxic poison. Wrong-status or fainted targets spend no stock.

`+use Mystery Berry=3/WATER GUN` restores slot 4 from 0 to 5 PP; `/4` restores it to 10. A saved raw +15 Water Gun PP bonus caps a later use at 40. Nonexistent slot 2, partial/unknown move names and a full slot change nothing. With no selector, only the first depleted active move receives 5 PP. The shared PP restoration implementation remains authoritative.

All nine work on the actual current Fusion through fusion/self/me; normal names, full IDs and target-first syntax remain supported. Egg, boxed, foreign, ambiguous and inactive Fusion targets cannot spend items. A real `+deposit` followed by stale-ID use is rejected. Persisted and runtime battle locks reject feeding. `+hold 3=Berry` and subsequent `+use Berry=3` consume independent bag/held copies; a held-only copy cannot be debited, and `+hold 3=` returns it normally.

Failed debits and injected exceptions after real HP/status/PP SQL writes leave bag, effect, placement, moves and inventory cache unchanged. Independent-connection last-copy contention produces exactly one effect/debit for each of the nine berries. Two Gold Berries competing at max-minus-one HP yield one useful feed, with the unused copy retained.

## Scope and evidence limits

The [JSON report](legacy-berries-2026-10-22.json) embeds command/SQL walkthroughs, exact commands, test counts, durations, log hashes, source hashes and cleanup. Raw logs are retained locally under ignored `.codex-artifacts/legacy-berries-20261022/`. Its initial targeted run also passed; only the final frozen-build runs count as final acceptance.

This is local automated production-command/model acceptance with captured session transport and real private PostgreSQL. It is separate from a fresh live Telnet/WebSocket login, hosted CI completion, main merge, deployment or current stock availability. No existing game database, human character, game service or migration runner was used. Disposable schemas were removed and the private task cluster stopped.

The existing 20 modern berries, Berry Juice, EV reduction/friendship, food/medicine, Rare Candy, PP Up/Max, battle validation, capture, held items and evolution regressions passed. The field allowlist is now 29 berries plus Berry Juice. Plot-only items, combat/contest-only feeding, new definitions and unrelated work are excluded. Manual battle feeding remains #773. Lifecycle CI now includes the new suite; its future hosted result is not claimed here.
