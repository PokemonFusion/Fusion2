# Integration runners

[Application tests](../README.md) | [Code map](../../docs/code-map.md) |
[Testing and evidence](../../docs/testing/README.md)

These guarded standalone programs retain their existing paths. Application
tests often invoke them in isolated subprocesses. This index groups them by
system without changing their execution or safety boundaries.

Read each program's module documentation and environment checks before running
it. Database programs use explicitly configured disposable test resources;
player-flow and lifecycle programs have separate prerequisites. An entry here
does not authorize a live migration, fixture setup, reload, or cleanup.

Full local offline qualification uses the [mandatory gate](../../tools/run_mandatory_tests.py).
PostgreSQL integration coverage is a separate evidence category, including in
the [lifecycle CI workflow](../../.github/workflows/lifecycle-integrity.yml).

## Adventure, gyms, and trainer encounters

- [adventure_lifecycle_cases](adventure_lifecycle_cases.py)
- [adventure_player_cases](adventure_player_cases.py)
- [gym_content_cases](gym_content_cases.py)
- [production_gym_cases](production_gym_cases.py)
- [trainer_challenge_cases](trainer_challenge_cases.py)

## Battle forms and held-item identity

- [legendary_item_cases](legendary_item_cases.py)
- [mega_evolution_cases](mega_evolution_cases.py)
- [mega_stone_cases](mega_stone_cases.py)
- [mega_stone_theft_cases](mega_stone_theft_cases.py)
- [memory_drive_theft_cases](memory_drive_theft_cases.py)
- [mint_necrozma_cases](mint_necrozma_cases.py)
- [mochi_necrozma_cases](mochi_necrozma_cases.py)
- [necrozma_cases](necrozma_cases.py)
- [necrozma_lifecycle_cases](necrozma_lifecycle_cases.py)
- [necrozma_migrations](necrozma_migrations.py)
- [necrozma_player_cases](necrozma_player_cases.py)
- [origin_primal_rusted_theft_cases](origin_primal_rusted_theft_cases.py)
- [plate_theft_cases](plate_theft_cases.py)
- [terastallization_cases](terastallization_cases.py)
- [ultra_battle_cases](ultra_battle_cases.py)
- [ultra_contention_cases](ultra_contention_cases.py)
- [ultra_preparation_cases](ultra_preparation_cases.py)
- [z_additional_status_sources_cases](z_additional_status_sources_cases.py)
- [z_existing_sources_cases](z_existing_sources_cases.py)
- [z_generic_cases](z_generic_cases.py)
- [z_move_cases](z_move_cases.py)
- [z_native_cases](z_native_cases.py)
- [z_next_six_sources_cases](z_next_six_sources_cases.py)
- [z_physical_sources_cases](z_physical_sources_cases.py)
- [z_signature_cases](z_signature_cases.py)
- [z_special_sources_cases](z_special_sources_cases.py)
- [z_status_cases](z_status_cases.py)

## Battles, AI, capture, and presentation

- [ai_action_cases](ai_action_cases.py)
- [ai_scoring_cases](ai_scoring_cases.py)
- [battle_booster_cases](battle_booster_cases.py)
- [battle_booster_source_cases](battle_booster_source_cases.py)
- [battle_item_validation_cases](battle_item_validation_cases.py)
- [battle_mechanic_completion_cases](battle_mechanic_completion_cases.py)
- [battle_recovery_cases](battle_recovery_cases.py)
- [battle_recovery_food_cases](battle_recovery_food_cases.py)
- [capture_ether_cases](capture_ether_cases.py)
- [capture_pp_item_cases](capture_pp_item_cases.py)
- [damp_player_cases](damp_player_cases.py)
- [multi_battle_cases](multi_battle_cases.py)
- [player_doubles_cases](player_doubles_cases.py)
- [recovery_cases](recovery_cases.py)
- [ui_cases](ui_cases.py)

## Items, acquisition, evolution, and progression

- [ability_item_cases](ability_item_cases.py)
- [alcremie_cases](alcremie_cases.py)
- [berry_growing_cases](berry_growing_cases.py)
- [contextual_evolution_cases](contextual_evolution_cases.py)
- [ev_mochi_cases](ev_mochi_cases.py)
- [evolution_cases](evolution_cases.py)
- [exp_candy_cases](exp_candy_cases.py)
- [exp_candy_native_cases](exp_candy_native_cases.py)
- [field_berry_cases](field_berry_cases.py)
- [field_food_cases](field_food_cases.py)
- [field_item_cases](field_item_cases.py)
- [field_training_cases](field_training_cases.py)
- [finite_item_supply_cases](finite_item_supply_cases.py)
- [flavor_snack_cases](flavor_snack_cases.py)
- [gimmighoul_coin_cases](gimmighoul_coin_cases.py)
- [held_status_berry_cases](held_status_berry_cases.py)
- [hyper_training_cases](hyper_training_cases.py)
- [incense_cases](incense_cases.py)
- [item_availability_cases](item_availability_cases.py)
- [item_feedback_cases](item_feedback_cases.py)
- [item_medicine_and_hp_cases](item_medicine_and_hp_cases.py)
- [item_next_action_cases](item_next_action_cases.py)
- [item_repair_cases](item_repair_cases.py)
- [item_replenishment_cases](item_replenishment_cases.py)
- [item_stat_batch_cases](item_stat_batch_cases.py)
- [item_supply_cases](item_supply_cases.py)
- [itemfinder_cases](itemfinder_cases.py)
- [kubfu_cases](kubfu_cases.py)
- [leader_crest_cases](leader_crest_cases.py)
- [legacy_berry_cases](legacy_berry_cases.py)
- [link_cord_cases](link_cord_cases.py)
- [mirror_herb_cases](mirror_herb_cases.py)
- [native_stat_item_cases](native_stat_item_cases.py)
- [nature_mint_cases](nature_mint_cases.py)
- [nature_mint_migrations](nature_mint_migrations.py)
- [npc_prize_item_cases](npc_prize_item_cases.py)
- [nursery_next_three_cases](nursery_next_three_cases.py)
- [nursery_seed_cases](nursery_seed_cases.py)
- [peat_block_cases](peat_block_cases.py)
- [pp_capacity_cases](pp_capacity_cases.py)
- [progression_cases](progression_cases.py)
- [rare_candy_cases](rare_candy_cases.py)
- [reactive_consumption_cases](reactive_consumption_cases.py)
- [recovery_equivalent_cases](recovery_equivalent_cases.py)
- [recovery_move_sources_cases](recovery_move_sources_cases.py)
- [remaining_item_cases](remaining_item_cases.py)
- [remedy_recovery_cases](remedy_recovery_cases.py)
- [renewable_source_cases](renewable_source_cases.py)
- [shop_purchase_cases](shop_purchase_cases.py)
- [smoke_ball_cases](smoke_ball_cases.py)
- [soothe_bell_cases](soothe_bell_cases.py)
- [status_item_cases](status_item_cases.py)
- [status_move_type_sources_cases](status_move_type_sources_cases.py)
- [training_finder_cases](training_finder_cases.py)
- [training_grounds_cases](training_grounds_cases.py)
- [wild_held_item_cases](wild_held_item_cases.py)

## Ownership, accounts, communication, and player services

- [breeding_cases](breeding_cases.py)
- [breeding_rule_cases](breeding_rule_cases.py)
- [cloud_gameplay_cases](cloud_gameplay_cases.py)
- [communication_cases](communication_cases.py)
- [daycare_cases](daycare_cases.py)
- [egg_roster_cases](egg_roster_cases.py)
- [fusion_cases](fusion_cases.py)
- [market_cases](market_cases.py)
- [name_resolution_cases](name_resolution_cases.py)
- [onboarding_cases](onboarding_cases.py)
- [ownership_cases](ownership_cases.py)
- [ownership_migrations](ownership_migrations.py)
- [placement_cases](placement_cases.py)
- [sheet_cases](sheet_cases.py)
- [trade_cases](trade_cases.py)
- [trade_held_cases](trade_held_cases.py)

## Protocols, lifecycle, and framework compatibility

- [amp_reload_cases](amp_reload_cases.py)
- [migration_graph](migration_graph.py)
- [recovery_migrations](recovery_migrations.py)
- [reload_socket_cases](reload_socket_cases.py)
- [server_shutdown_cases](server_shutdown_cases.py)
- [telnet_protocol_cases](telnet_protocol_cases.py)

## Shared guards and fixtures

- [battle_player_fixtures](battle_player_fixtures.py)
- [isolated_battle_logs](isolated_battle_logs.py)
- [isolated_postgres](isolated_postgres.py)
- [ordinary_player_fixtures](ordinary_player_fixtures.py)
