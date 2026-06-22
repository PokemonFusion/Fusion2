# Pokemon Inventory Audit - 2026-06-22

Scope: current local `fusion2` checkout, loaded `pokemon.dex.POKEDEX` entries with `num >= 0`.
Negative-number CAP and Pokestar-style entries were intentionally excluded.

Inventory file: `docs/pokemon-inventory-2026-06-22.csv`

## Summary

| Measure | Count |
| --- | ---: |
| Loaded POKEDEX entries | 1421 |
| Excluded negative dex entries | 92 |
| Audited non-negative dex entries | 1329 |
| Positive dex entries | 1328 |
| Zero dex entries | 1 |
| Alternate/form entries | 303 |
| Base entries advertising otherFormes | 174 |
| Base entries with canGigantamax | 34 |
| Gmax form entries | 32 |
| Evolution links from audited entries | 530 |
| Evolution links with level/item-supported data shape | 422 |
| Evolution links reachable by current lookup and level/item rules | 388 |
| Unique required form items | 79 |
| Required form items missing from ITEMDEX | 0 |
| Unique ability names on audited entries | 310 |
| Ability names not runtime-resolvable | 0 |
| Catch-rate rows in generated table | 1673 |
| Rows with no missing categories | 819 |
| Rows with at least one missing/partial category | 510 |

## What Is In Place

- The aggregated dex imports successfully from `pokemon/dex/pokedex/__init__.py` and covers Kanto through Paldea plus `extras`.
- Every audited entry can be passed to `generate_pokemon(name, level=50)` without raising an exception.
- Every audited entry has type data, egg group data, and at least an ability-name slot in the dex row.
- All normal positive-number entries have nonzero base stats. `MissingNo.` is the only non-negative outlier and has Defense 0 in source data.
- All unique `requiredItem` values used by form entries resolve in `ITEMDEX`.
- Catch-rate lookup now resolves display names, punctuation-free names, and generated raw dex keys. The only remaining non-negative catch-rate miss is `MissingNo.`.
- Existing focused tests prove the supported generic level evolution path and representative battle-time form paths: Mega, Primal, and forced-form held items.

## Global Caveat

The `Pokemon.from_dict` entity loader currently links species abilities with `abilitydex.get(ability_name.lower())`, while `ABILITYDEX` is keyed with normalized/canonical generated names such as `Overgrow` or `Thickfat`. As a result, species dex objects carry placeholder `Ability(raw={})` entries instead of linked callback metadata. The battle runtime can still resolve normal ability-name strings through `_normalize_key`; the CSV column `ability_entity_metadata_linked` records the entity-layer gap per row.

## Missing Or Partial Functionality

| Category | Rows | Meaning | Examples |
| --- | ---: | --- | --- |
| `special_num_zero_entry` | 1 | The row is dex number 0 (`MissingNo.`), not a normal species. | MissingNo. |
| `missing_or_zero_base_stat` | 1 | At least one base stat is missing or zero. | MissingNo. |
| `no_learnset_entry` | 144 | No learnset table row exists under the dex key, display name, or normalized display name. | Venusaur-Gmax, Venusaur-Mega, Charizard-Gmax, Charizard-Mega-X, Charizard-Mega-Y, Blastoise-Gmax, Blastoise-Mega, Butterfree-Gmax, Beedrill-Mega, Pidgeot-Mega, Pikachu-Gmax, Meowth-Gmax |
| `no_levelup_moves_runtime` | 346 | `get_valid_moves(display_name, 100)` returns no level-up moves. | MissingNo., Venusaur-Gmax, Venusaur-Mega, Charizard-Gmax, Charizard-Mega-X, Charizard-Mega-Y, Blastoise-Gmax, Blastoise-Mega, Butterfree-Gmax, Beedrill-Mega, Pidgeot-Mega, Rattata-Alola |
| `wild_moves_fall_back_to_struggle` | 346 | `choose_wild_moves(display_name, 50)` returns only `Struggle`. | MissingNo., Venusaur-Gmax, Venusaur-Mega, Charizard-Gmax, Charizard-Mega-X, Charizard-Mega-Y, Blastoise-Gmax, Blastoise-Mega, Butterfree-Gmax, Beedrill-Mega, Pidgeot-Mega, Rattata-Alola |
| `catch_rate_canonical_lookup_miss` | 1 | Catch lookup by exact runtime display name misses. | MissingNo. |
| `catch_rate_data_missing` | 1 | No catch-rate data was found through exact or normalized runtime lookup. | MissingNo. |
| `exp_ev_canonical_lookup_miss` | 380 | EXP/EV lookup by current runtime display name misses, even if normalized raw data may exist. | MissingNo., Venusaur-Gmax, Venusaur-Mega, Charizard-Gmax, Charizard-Mega-X, Charizard-Mega-Y, Blastoise-Gmax, Blastoise-Mega, Butterfree-Gmax, Beedrill-Mega, Pidgeot-Mega, Rattata-Alola |
| `exp_ev_data_missing` | 377 | No EXP/EV data was found under display, key, or normalized lookup candidates. | MissingNo., Venusaur-Gmax, Venusaur-Mega, Charizard-Gmax, Charizard-Mega-X, Charizard-Mega-Y, Blastoise-Gmax, Blastoise-Mega, Butterfree-Gmax, Beedrill-Mega, Pidgeot-Mega, Rattata-Alola |
| `evolution_target_not_resolved_by_current_lookup` | 52 | `pokemon.data.evolution` cannot resolve a listed target with its current name/case lookup. | Rattata-Alola, Pikachu, Sandshrew-Alola, Vulpix-Alola, Diglett-Alola, Meowth-Alola, Growlithe-Hisui, Geodude-Alola, Graveler-Alola, Ponyta-Galar, Slowpoke-Galar, Slowpoke-Galar |
| `evolution_trade_not_supported` | 30 | The generic evolution helper explicitly skips trade evolutions. | Poliwhirl, Kadabra, Machoke, Graveler, Graveler-Alola, Slowpoke, Haunter, Onix, Rhydon, Seadra, Scyther, Electabuzz |
| `evolution_levelFriendship_not_supported` | 19 | Friendship evolution requirements are not implemented. | Golbat, Meowth-Alola, Chansey, Eevee, Eevee, Pichu, Cleffa, Igglybuff, Togepi, Azurill, Budew, Buneary |
| `evolution_levelMove_not_supported` | 15 | Move-known evolution requirements are not implemented. | Lickitung, Tangela, Aipom, Yanma, Girafarig, Dunsparce, Dunsparce, Piloswine, Bonsly, Mime Jr., Mime Jr., Steenee |
| `evolution_levelHold_not_supported` | 4 | Held-item-on-level evolution requirements are not implemented. | Gligar, Sneasel, Sneasel-Hisui, Happiny |
| `evolution_levelExtra_not_supported` | 3 | Extra/contextual level evolution requirements are not implemented. | Eevee, Nosepass, Mantyke |
| `evolution_other_not_supported` | 17 | Species-specific custom evolution requirements are not implemented. | Primeape, Farfetch’d-Galar, Qwilfish-Hisui, Ursaring, Stantler, Basculin-White-Striped, Basculin-White-Striped, Yamask-Galar, Bisharp, Milcery, Kubfu, Kubfu |
| `evolution_level_extra_conditions_ignored` | 19 | The current level path would ignore additional condition fields. | Rattata-Alola, Cubone, Koffing, Tyrogue, Tyrogue, Tyrogue, Linoone-Galar, Pancham, Inkay, Tyrunt, Amaura, Sliggoo |
| `evolution_branching_selection_partial` | 37 | Multi-target evolution choices are only partly represented by level/item checks. | Pikachu, Gloom, Poliwhirl, Slowpoke, Slowpoke-Galar, Exeggcute, Cubone, Koffing, Scyther, Eevee, Quilava, Dunsparce |
| `evolution_useItem_missing_evoItem` | 1 | The target says use-item evolution but has no `evoItem` field. | Scyther |
| `alternate_form_selection_runtime_missing` | 117 | Form data exists, but there is no general player/runtime path to choose or derive this form. | Rattata-Alola, Raticate-Alola, Raticate-Alola-Totem, Pikachu-Alola, Pikachu-Cosplay, Pikachu-Hoenn, Pikachu-Kalos, Pikachu-Original, Pikachu-Partner, Pikachu-Sinnoh, Pikachu-Starter, Pikachu-Unova |
| `form_trigger_specific_runtime_not_fully_verified` | 103 | The form requires a species-specific battle trigger; generic `formeChange` exists, exhaustive trigger proof does not. | Venusaur-Gmax, Charizard-Gmax, Blastoise-Gmax, Butterfree-Gmax, Pikachu-Belle, Pikachu-Gmax, Pikachu-Libre, Pikachu-PhD, Pikachu-Pop-Star, Pikachu-Rock-Star, Meowth-Gmax, Machamp-Gmax |
| `gigantamax_runtime_selection_missing` | 68 | Gmax species and moves exist, but no Dynamax/Gigantamax transformation selection path was found. | Venusaur, Venusaur-Gmax, Charizard, Charizard-Gmax, Blastoise, Blastoise-Gmax, Butterfree, Butterfree-Gmax, Pikachu, Pikachu-Gmax, Meowth, Meowth-Gmax |

## Evolution Notes

The persistent evolution command path is `commands/player/cmd_learn_evolve.py -> pokemon.data.evolution.attempt_evolution`. That helper currently supports straightforward level/default evolution and use-item evolution with an `evoItem`; it explicitly skips trade evolution and does not implement friendship, move-known, held-item-on-level, regional/contextual, or custom `other` requirements.

The CSV `missing_categories` and `notes` columns contain the per-Pokemon evolution details, including all branch targets that the current helper cannot resolve because form target names like `Raichu-Alola` are listed canonically while `POKEDEX` is keyed by generated names like `Raichualola`. There are 34 otherwise level/item-shaped evolution links blocked by that current lookup behavior, and 52 current-lookup misses total once unsupported condition types are included.

## Form Notes

Battle-time `formeChange` exists and updates species, name, types, base stats, and primary ability. The battle engine also has representative paths for Mega Evolution, Red/Blue Orb primal forms, and held-item forced forms. Missing coverage is mostly in species-specific triggers and user-facing selection: alternate regional/cosmetic forms have data but no general selection flow, ability/weather/move-triggered battle forms are not exhaustively verified, and Gmax forms/moves exist without a Dynamax/Gigantamax transformation path.

## Catch And Reward Data Gaps

Catch-rate lookup now has generated display-name aliases plus normalized runtime fallback. Remaining catch-rate misses:

```text
MissingNo.
```

EXP/EV data is still missing for most alternate forms and `MissingNo.`; the exhaustive list is in the CSV under `exp_ev_data_missing`. Representative examples are in the missing-functionality table above.

## Validation

Commands run from `H:\PokemonFusionProject\fusion2`:

```powershell
H:\PokemonFusionProject\evenv\Scripts\python.exe -m pytest tests\test_catch_rate_lookup.py tests\test_item_capture.py -q
H:\PokemonFusionProject\evenv\Scripts\python.exe -m pytest tests\test_evolution.py pokemon\battle\tests\test_showdown_runtime_hooks.py -q
```

Results: catch/capture tests `11 passed`; evolution/form tests `48 passed`.
