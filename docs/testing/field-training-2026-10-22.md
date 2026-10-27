# Vitamin and feather field training acceptance - October 22, 2026

Issue: #768. Source baseline: `e6855ad94e2c3d8e9d8450a9bf9304019f91af76` on `staging`.

The twelve existing vitamins and feathers now work through ordinary `+use`. FieldTrainingUse shares the fresh owner/party/current-Fusion checks, placement/trainer locks and transaction used by field medicine. One effect validates saved EVs, clips a useful increase to legal capacity, debits one bag item, recalculates stats and saves EVs/HP atomically. No new definitions or existing EV-berry behavior are introduced.

## Selected rules

| Stat (EV index) | Vitamin (up to +10) | Feather (+1) |
| --- | --- | --- |
| HP (0) | HP Up | Health Feather |
| Attack (1) | Protein | Muscle Feather |
| Defense (2) | Iron | Resist Feather |
| Special Attack (3) | Calcium | Genius Feather |
| Special Defense (4) | Zinc | Clever Feather |
| Speed (5) | Carbos | Swift Feather |

The current-generation supplement policy permits vitamins above 100 EVs up to **252 per stat and 510 total**. The [official Sword/Shield supplement explanation](https://swordshield.pokemon.com/en-gb/gameplay/features-raise-pokemon/) supports reaching maximum base points through supplements. Existing PF2 callbacks supply the reviewed +10/+1 amounts and existing EV validators supply the caps; these source files are pinned below.

Gain is the minimum of the item amount and remaining stat/total capacity. Protein at 250 Attack adds 2, spending one copy; at 252 it does nothing and spends none. Invalid saved array shape, out-of-range EVs or total over 510 are rejected unchanged. Positive EV gains count even before stat rounding produces a displayed increase. This bounded EV route leaves friendship, IVs, held items, level, moves and other fields unchanged, with no friendship-only use at an EV cap.

Stats refresh immediately using the existing helpers. Match the EV-berry HP convention: retain the absolute HP deficit when maximum HP changes, clamp living HP to 1..new maximum, and keep fainted HP zero. Non-HP training does not heal ordinary injured Pokemon. No move selector, party-wide target or battle use is added.

## Verified results

- **30 new PostgreSQL cases** cover all twelve ordinary discover/use/reload flows; exact names and inventory aliases; full, one-point and two-point stat/total caps; above-100 vitamins; EV gains hidden by rounding; full/injured/fainted HP; bad saved EVs; fresh eligibility and stale caps; current Fusion; real deposit then stale-ID rejection; ambiguous/foreign/egg/box/reservation/battle/selector guards; failed/partial debits; post-SQL rollback/cache recovery; per-item last-copy races; different-target contention; competing stats and terminal stat capacity.
- **475 total PostgreSQL cases** passed: field_training 30; legacy_berry 26; battle_item_validation 22; smoke_ball 17; player_doubles 10; battle_recovery 36; pp_capacity 37; name_resolution 8; capture_ether 21; status_item 9; rare_candy 25; field_item 23; field_berry 26; field_food 70; remaining_item 8; capture_pp_item 16; leader_crest 29; evolution 28; progression 11; cloud_gameplay 9; ui 14.
- **530 focused pytest tests** passed, including EV/stat, inventory, field medicine/food, held effects, prior PP, battle validation, capture and evolution regressions.
- **Mandatory fresh-process orders:** combined: 4624 passed / 4014 skipped; repeat: 4624 passed / 4014 skipped; battle-first: 4624 passed / 4014 skipped.
- **971 frozen Python sources** stayed unchanged. The report pins **40 relevant source hashes** for staged/committed blob comparison.
- **169 ordinary command/SQL observations** preserve inputs, output, full Pokemon/placement/move/boost rows and inventory/cache before/after use.
- Passing logs contain dependency/cache warnings; no warning-free environment is claimed.

After all suites finished, staged diff checking found one extra empty line at the end of the new test file. It was removed before commit. The original tested source manifest was retained, exact before/after hashes recorded, and Python AST identity verified. All other Python sources remained byte-identical; no executable tokens or gameplay code changed, so the full gates were not repeated for this formatting-only cleanup. The JSON source hashes describe the final committed text.

## Player-flow and failure evidence

Disposable setup creates tagged normal User owners and canonical party members with calculated stats, active move gaps and real stock. Every item appears in `+inventory` and its target in `+party 3`, then the production `+use <item>=3` command changes exactly the mapped EV stat and any required max-HP adjustment. An initial 3 EVs at level 100 makes each feather's stat effect observable. Tests independently read SQL, close connections, flush the identity cache and verify the same saved state and stats after reload.

Protein and Muscle Feather examples distinguish +10 from +1. All items can use the final legal stat/total point; vitamins also clip to 2. A Muscle Feather at zero Attack EVs consumes once and persists 1 EV even though the displayed stat has not yet changed. HP Up/Health Feather retain the injury deficit; every item preserves zero HP on fainted targets. All twelve accept current fusion/self/me; unambiguous names, full IDs and target-first syntax work, with canonical party gaps retained.

Wrong targets, eggs, box deposits, inactive Fusion reservations, persisted/runtime battle locks, absent stock, ambiguous names, illegal selectors and invalid EV arrays leave saved state and inventory untouched. Failed debits both before and after actual inventory SQL roll back, as do exceptions injected after actual EV/HP saves. Full SQL snapshots, inventory cache, model fields and calculated stats recover to persisted state.

Two independent connections competing for each item's last copy yield exactly one legal increase/debit. One copy cannot train two different party members. Different-stat vitamin/feather pairs competing for the final total-cap point produce one gain and leave the unused copy; two stocked Protein uses at 251 Attack produce 252 and retain the second copy. Existing EV-lowering berries, recovery berries, medicine/food, Rare Candy, PP items, held effects and battle-input checks retain regression coverage.

## Scope and cleanup

The [JSON report](field-training-2026-10-22.json) embeds raw command/SQL observations, exact test commands, counts/durations, log/source hashes, rules and cleanup. Raw logs remain under ignored `.codex-artifacts/field-training-20261022/`. The initial 29-case run also passed; only the expanded final frozen-build runs count as final acceptance. Lifecycle CI now runs the new suite.

Evidence is local automated production-command/model acceptance with captured session transport and private PostgreSQL. It is separate from fresh live login, current stock availability, hosted CI completion, main merge or deployment. All isolated schemas were removed, public schema is empty and the private task cluster stopped. No existing game database, human character, service or migration runner was used.

Plot-only content, unrelated work, new training definitions, Pretty Feather, mints, Bottle Caps, ability-item routes, friendship-only use and battle training are outside this change. Existing EV-berry behavior and held callbacks are unchanged.
