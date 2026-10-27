# Bottle Cap Hyper Training acceptance - October 22, 2026

Issue: #770. Source baseline: `f6ad4651a733a96a35dab87180d734eae15a0b06` on `staging`.

Both existing caps now work through ordinary `+use`, reusing fresh canonical party/current-Fusion checks, placement/trainer/target locks, atomic inventory writes and progression commit-aware notifications. Training uses effective IV 31 while preserving genetic IVs.

## Rules and persistence

`+use Bottle Cap=3/Atk` requires one full stat name or exact HP/Atk/Def/SpA/SpD/Spe alias (also SpAtk/SpDef and defence spellings). Numbers, prefixes and move names reject. `+use Gold Bottle Cap=3` accepts no selector and trains every remaining eligible stat with one copy. Names/full IDs, target-first syntax and current fusion/self/me retain shared field targeting.

The selected Generation-9 policy requires level 50+, consistent saved level/EXP and genetic IV below 31 in an untrained stat. The primary [Hyper Training interface](https://github.com/kwsch/PKHeX/blob/master/PKHeX.Core/PKM/Interfaces/IHyperTrain.cs) records the generation-dependent level boundary and independent stat flags; the [legality verifier](https://github.com/kwsch/PKHeX/blob/master/PKHeX.Core/Legality/Verifiers/HyperTrainingVerifier.cs) checks perfect-IV eligibility. Gold skips perfect/prior-trained stats. No eligible stat means no debit; effective training can be useful even when stat rounding initially hides the increase.

Existing `OwnedPokemon.flags` persists `hypertrained:hp`, `attack`, `defense`, `special_attack`, `special_defense` and `speed` (each with the prefix). Other flags remain intact. No schema change, migration, conversion or retroactive grant is needed. Genetic `ivs` remain identical in SQL and serialized battle payloads. Effective-IV copies feed common stats, party/battle factories and native-form recalculations. A separate optional `hyper_training` checkpoint key carries runtime training; legacy owned checkpoints recover persisted flags and standalone old/malformed payloads default to no overlay. Battle-level scaling below 50 retains training.

Fainted targets stay at zero HP. Living targets preserve absolute HP deficit when maximum HP changes; status remains untouched. Cap use does not change species, identity, ownership, placement, held item, EVs, friendship, moves or genetic/inheritance inputs. Existing evolution preserves flags. No breeding or Hidden Power implementation is added.

Unknown/battle-only and item/ability-locked forms, transformed targets, malformed genetic/EV/training data and inconsistent EXP/level reject unchanged. Shared egg, foreign/box/inactive reservation, battle lock, ambiguity and stock guards apply. Useful flags, HP and one debit commit together, including failed/partial debits, post-write faults, outer rollback and competing requests.

## Verified results

- **29 new PostgreSQL cases** cover both caps, all six selected-stat flows, mixed Gold eligibility, level threshold/fresh EXP, stat selectors, ordinary inventory/itemdex/party discovery, SQL reconnect/cache reload, genetic preservation, actual durable session rebuilds, relevant guards and atomic/concurrent failures.
- **534 PostgreSQL cases total** passed: hyper_training 29; ability_item 30; field_training 30; legacy_berry 26; battle_item_validation 22; smoke_ball 17; player_doubles 10; battle_recovery 36; pp_capacity 37; name_resolution 8; capture_ether 21; status_item 9; rare_candy 25; field_item 23; field_berry 26; field_food 70; remaining_item 8; capture_pp_item 16; leader_crest 29; evolution 28; progression 11; cloud_gameplay 9; ui 14.
- **761 focused pytest tests** passed, including overlay, stat/party display, native forms, transformation, checkpoints, medicine/berry/EV, ability, PP, inventory, evolution and battle-validation coverage.
- **Three required fresh-process orders:** combined: 4635 passed / 4014 skipped; repeat: 4635 passed / 4014 skipped; battle-first: 4635 passed / 4014 skipped.
- **977 frozen Python sources** stayed unchanged throughout verification; **58 relevant source hashes** pin code, tests, docs, workflow and canonical dex modules for staged/committed comparison.
- **62 observations** retain ordinary commands/output and independent full SQL Pokemon, placement, move, boost, bag and inventory-cache state, plus the two durable session rebuilds.
- Passing logs include dependency/cache warnings; warning-free execution is not claimed.

## Player-flow evidence

Disposable setup creates an ordinary owner, canonical slot 3, genetic IVs 0..5 and real bag copies. Production `+itemdex Bottle Cap`, `+inventory` and `+party 3` discover the route and target. Each `+use Bottle Cap=3/<stat>` trains exactly that effective IV, while Gold trains all eligible stats. `+party 3` retains the genetic IV row and adds an Effective IV row plus trained labels. Closing SQL connections, flushing the identity cache and reconstructing a production battle Pokemon preserve the result and genetics. A normal BattleSession is started, synchronized, persisted and restored twice with the trained stats and original IVs intact.

The mixed Gold case skips genetically perfect HP/SpD and prior-trained Def, training only Atk/SpA/Spe. Full/perfect/already-trained targets keep all stock. Level 1/49, inconsistent saved EXP, wrong/missing selectors, invalid arrays/flags, unknown/Mega/transformed targets, eggs, boxed/inactive reservations, foreign or changed owners, duplicate names, party gaps, missing stock and battle locks are negative cases. Fainted/full/injured HP states and an IV-30 rounding case are covered.

Debit failures before and after actual bag SQL and an exception after the real flags/HP UPDATE roll back full state. An outer transaction rollback cannot publish training or success. Competing final-copy uses produce exactly one paid effect across stats or targets. Duplicate same-stat requests spend once; two stocked different-stat requests merge their persisted flags. Gold/single-cap contention preserves the eligible set and only pays for useful training. Ordinary Fire Stone evolution, HP Up, Pomeg Berry and Potion afterward retain genetic IVs and all training flags.

The initial failures were diagnosed separately: ANSI comparison, unsaved level setup, an old model reference despite correct merged SQL flags, and the real missing required-item form guard. A later setup-only level-1 HP constraint failure was corrected using calculated HP. The expanded targeted run passed 29/29 before the complete frozen acceptance run reported above. No unrelated shared-field or battle fix was introduced for fixture failures.

## Metadata, limits and cleanup

Existing dex metadata stays Generation 7, IDs 795/796 and Fling 30. Only gameplay descriptions explain the new route. No price, shop stock, world grant, NPC, plot unlock or live obtainability claim is added; #772 retains availability work. Mints and breeding remain separate.

The [JSON report](hyper-training-2026-10-22.json) embeds rule choices, exact commands/counts/durations, command/SQL evidence, source/log hashes and cleanup. Raw logs remain in ignored `.codex-artifacts/hyper-training-20261022/`. Lifecycle CI includes the new PostgreSQL suite; hosted completion is not asserted here.

Evidence is local automated production-command/model acceptance with captured transport and real private PostgreSQL, separate from a fresh live login, current obtainability, hosted CI completion, main merge or deployment. All isolated schemas were removed, public schema is empty and the private task cluster stopped. Existing game databases, human characters, services and migrations were not used. Plot-only items, new definitions, unrelated work and broader training systems remain excluded.
