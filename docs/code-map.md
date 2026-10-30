# Fusion2 code map

Use this map to locate the current implementation. Paths describe the existing
checkout; they are not a proposal to move runtime modules. For player and
builder instructions, start with the [feature guides](guides.md).

## Directory responsibilities

| Location | What to look for |
| --- | --- |
| [commands/player](../commands/player/) | Player command parsing and command entry points |
| [commands/admin](../commands/admin/) | Staff commands and world-building entry points |
| [commands/cmdsets](../commands/cmdsets/) | Command registration; assembled by [default_cmdsets.py](../commands/default_cmdsets.py) |
| [commands/debug](../commands/debug/), [dev](../commands/dev/), [wizards](../commands/wizards/) | Debug commands and editor/wizard entry points |
| [menus](../menus/) | Interactive in-game menus |
| [pokemon/battle](../pokemon/battle/) | Battle state, legal actions, engine, mechanics, and turn processing |
| [services/battle](../services/battle/) | Battle orchestration, instance state, commit and snapshot adapters |
| [pokemon/services](../pokemon/services/) | Gameplay workflows: ownership, trading, items, progression, gyms, and more |
| [pokemon/models](../pokemon/models/), [migrations](../pokemon/migrations/) | Django persistence models and schema history |
| [pokemon/adventures](../pokemon/adventures/), [spawns](../pokemon/spawns/) | Adventure sessions/progress and spawn selection/profile tooling |
| [pokemon/ui](../pokemon/ui/) | Battle and move rendering |
| [pokemon/helpers](../pokemon/helpers/), [pokemon/utils](../pokemon/utils/), [utils](../utils/) | Existing helper modules; see the boundaries below |
| [typeclasses](../typeclasses/), [pokemon/user.py](../pokemon/user.py) | Evennia game objects and the configured player character typeclass |
| [world](../world/) | World hooks, batch files, content definitions, item counters, and help entries |
| [web](../web/), [roomeditor](../roomeditor/) | Website/webclient and browser room editor |
| [bboard](../bboard/) | Bulletin board commands and persistence helpers |
| [server/conf](../server/conf/) | Server settings and startup/network configuration |
| [pokemon/data](../pokemon/data/), [pokemon/dex](../pokemon/dex/) | Generation data and species/move/item/ability registries |
| [tools](../tools/README.md) | [QA runners](../tools/qa/README.md), [audits](../tools/audits/README.md), data generation, and the mandatory gate |
| [tests](../tests/README.md), [pokemon/battle/tests](../pokemon/battle/tests/) | Application tests grouped by feature, stable integration runners, and battle-mechanics tests |

## Find a feature

These are starting points, not exhaustive dependency lists. Representative
tests show the relevant behavior; use a text search to find the rest.

### Battle commands, engine, and persistence

- Entry points: [attack](../commands/player/cmd_battle_attack.py),
  [items](../commands/player/cmd_battle_item.py),
  [switching](../commands/player/cmd_battle_switch.py),
  [PvP](../commands/player/cmd_pvp.py), [Multi lobby](../commands/player/cmd_pvp_multi.py).
- Mechanics: [engine](../pokemon/battle/engine.py),
  [turn processing](../pokemon/battle/turn.py),
  [legal actions](../pokemon/battle/legal_actions.py),
  [damage](../pokemon/battle/damage.py), [AI scoring](../pokemon/battle/ai_action_scoring.py).
- Lifecycle: [manager](../services/battle/manager.py),
  [instance and RNG state](../services/battle/instance.py),
  [commit adapter](../services/battle/commit_adapter.py),
  [battle persistence](../pokemon/battle/persistence.py),
  [reward receipts](../pokemon/services/battle_rewards.py).
- Tests: [semantic contracts](../tests/battle/test_battle_semantic_contracts.py),
  [rebuild](../tests/battle/test_battle_rebuild.py), [Multi](../tests/battle/test_multi_battle.py),
  and the [battle test directory](../pokemon/battle/tests/).
- Docs: [offline testing](offline-battle-testing.md), [recovery](battle-recovery.md),
  [AI legality](battle-ai-legality.md), [AI scoring](battle-ai-scoring.md).

### Battle presentation and accessibility

- Entry points: [battle style](../commands/player/cmd_battleuistyle.py),
  [UI mode](../commands/player/cmd_uimode.py),
  [choice prompts](../commands/player/battle_choice_prompts.py).
- Rendering: [compact cards](../pokemon/ui/compact_battle.py),
  [battle renderer](../pokemon/ui/battle_render.py),
  [move GUI](../pokemon/ui/move_gui.py), [turn messages](../pokemon/battle/messaging.py).
- Tests: [compact UI](../tests/battle/test_compact_battle_ui.py),
  [rendering](../tests/battle/test_compact_battle_render.py).
- Docs: [battle interface](battle-interface.md), [theme design](design/theme-foundations.md).

### Party, storage, ownership, and trainer Fusion

- Entry points: [party](../commands/player/cmd_party.py),
  [sheet](../commands/player/cmd_sheet.py), [storage](../commands/player/cmd_pokestore.py),
  [Fusion](../commands/player/cmd_fusion.py).
- Workflows: [placement](../pokemon/services/placement.py),
  [ownership](../pokemon/services/ownership.py),
  [Fusion transitions](../pokemon/services/fusion_transitions.py),
  [party view](../utils/party_view.py), [party helpers](../pokemon/helpers/party_helpers.py).
- Storage: [core Pokemon model](../pokemon/models/core.py),
  [storage models](../pokemon/models/storage.py), [ownership models](../pokemon/models/ownership.py).
- Tests: [party slots](../tests/ownership/test_party_slot_views.py),
  [storage flow](../tests/ownership/test_party_storage_flow.py),
  [ownership SQL cases](../tests/integration/ownership_cases.py).
- Docs: [placement](operations/pokemon-placement.md),
  [Fusion transitions](operations/fusion-transitions.md),
  [sheet visibility](operations/character-sheet-reads.md).

### Transfers, trading, marketplace, daycare, and breeding

- Commands: [account/trades](../commands/player/cmd_account.py),
  [market](../commands/player/cmd_market.py), [daycare](../commands/player/cmd_daycare.py),
  [breeding](../commands/player/cmd_breed.py).
- Services: [ownership](../pokemon/services/ownership.py),
  [trading](../pokemon/services/trading.py), [marketplace](../pokemon/services/marketplace.py),
  [daycare](../pokemon/services/daycare.py), [breeding](../pokemon/services/breeding.py).
- Models: [ownership](../pokemon/models/ownership.py), [market](../pokemon/models/market.py),
  [daycare](../pokemon/models/daycare.py), [breeding](../pokemon/models/breeding.py).
- Tests: [trade safety](../tests/ownership/test_trade_safety.py),
  [trade SQL cases](../tests/integration/trade_cases.py),
  [breeding rules](../tests/breeding/test_breeding_rules.py).
- Docs: [operations index](operations/README.md).

### Items, learning, training, and evolution

- Commands: [inventory/use](../commands/player/cmd_inventory.py),
  [berries](../commands/player/cmd_berry.py), [learning/evolution](../commands/player/cmd_learn_evolve.py),
  [training](../commands/player/cmd_train.py).
- Services: [field items](../pokemon/services/field_items.py),
  [finite supply](../pokemon/services/finite_item_supply.py),
  [move management](../pokemon/services/move_management.py),
  [training grounds](../pokemon/services/training_grounds.py),
  [evolution](../pokemon/services/evolution.py), [berry growing](../pokemon/services/berry_growing.py).
- Definitions: [item registry](../pokemon/dex/items/itemsdex.py),
  [evolution items](../pokemon/evolution_items.py), [world counters](../world/).
- Tests: [gameplay items](../tests/items/test_gameplay_items.py),
  [finite supply](../tests/items/test_finite_item_supply.py),
  [evolution](../tests/evolution/test_evolution.py), [berry growing](../tests/items/test_berry_growing.py).
- Docs: [item and progression guides](guides.md#items-acquisition-and-progression).

### Special battle forms and mechanics

- Commands: [Mega](../commands/player/cmd_battle_mega.py),
  [Tera](../commands/player/cmd_battle_tera.py), [Z-Moves](../commands/player/cmd_battle_zmove.py),
  [Ultra](../commands/player/cmd_battle_ultra.py), [Necrozma](../commands/player/cmd_necrozma.py).
- Battle logic: [Mega](../pokemon/battle/mega_evolution.py),
  [Terastallization](../pokemon/battle/terastallization.py),
  [Z-Moves](../pokemon/battle/z_moves.py), [Ultra Burst](../pokemon/battle/ultra_burst.py).
- Durable combination workflow: [Necrozma service](../pokemon/services/necrozma.py)
  and [models](../pokemon/models/necrozma.py).
- Tests: [Mega consumer guards](../pokemon/battle/tests/test_mega_consumer_guards.py),
  [Terastallization](../tests/battle/test_terastallization.py), [Necrozma SQL checks](../tests/battle/test_necrozma_database.py).
- Docs: [special mechanic guides](guides.md#special-battle-mechanics),
  [design contracts](design/README.md#special-battle-mechanics).

### Adventure, hunting, NPC trainers, and gyms

- Adventure: [commands](../pokemon/adventures/commands.py),
  [sessions](../pokemon/adventures/sessions.py), [progress](../pokemon/adventures/progress.py),
  [models](../pokemon/models/adventures.py), [hall batch](../world/adventure_hall.ev).
- Hunting: [command](../commands/player/cmd_hunt.py),
  [world hunt system](../world/hunt_system.py), [spawn selection](../pokemon/spawns/selection.py),
  [profile data](../pokemon/spawns/profile_data.py).
- Trainers/gyms: [challenge command](../commands/player/cmd_challenge.py),
  [gym command](../commands/player/cmd_gym.py),
  [trainer encounters](../pokemon/services/trainer_encounters.py),
  [gym content](../pokemon/services/gym_content.py), [gym models](../pokemon/models/gym.py),
  [authored gym content](../world/content/gyms/).
- Tests: [Adventure commands](../tests/adventure/test_adventure_commands.py),
  [hunting](../tests/spawns/test_hunt_system.py), [spawn selection](../tests/spawns/test_spawn_selection.py),
  [gym leaders](../tests/world/test_gym_leaders.py).
- Docs: [Adventure operations](adventure-operations.md),
  [NPC trainer setup](static-npc-trainer-battles.md), [gym operations](operations/gym-content.md).

### Accounts, communication, website, and room editor

- Commands: [chargen](../commands/player/cmd_chargen.py),
  [mail](../commands/player/cmd_mail.py), [profiles](../commands/player/cmd_profile.py),
  [support requests](../commands/player/cmd_request.py).
- Services/helpers: [onboarding](../pokemon/services/onboarding.py),
  [mail](../utils/character_mail.py), [profiles](../utils/character_profiles.py),
  [support requests](../utils/support_requests.py), [site status](../utils/site_status.py).
- Web: [URL routing](../web/urls.py), [website views](../web/website/views/),
  [templates](../web/templates/), [webclient](../web/webclient/),
  [room editor views](../roomeditor/views/).
- Tests: [mail](../tests/communication/test_character_mail.py), [profiles](../tests/accounts/test_character_profiles.py),
  [homepage](../tests/ui/test_homepage_webclient_preview.py), [room editor](../tests/ui/test_roomeditor_preview.py).
- Docs: [onboarding](operations/onboarding.md), [communications](operations/communications.md).

## Existing helper boundaries

Helper names overlap, so search for the caller before choosing an implementation:

- [pokemon/helpers/pokemon_helpers.py](../pokemon/helpers/pokemon_helpers.py)
  supplies stat calculations and Pokemon creation/refresh helpers.
- [pokemon/utils](../pokemon/utils/) contains small Pokemon-specific primitives,
  including the `PokemonLike` protocol, object resolution, boosts, and move learning.
- [utils](../utils/) also contains application workflows and views such as mail,
  party/inventory rendering, logging, and client encoding. It is broader than
  the name suggests.
- [services/battle](../services/battle/) and
  [pokemon/services](../pokemon/services/) both participate in battle workflows;
  the battle section above identifies their entry points.

These locations remain in use. Consolidation requires tracing imports and
behavior separately from this documentation pass.

## Search and verification

From the repository root:

```powershell
rg -n 'TradeOffers|PlacementService' commands pokemon tests
rg --files docs -g '*adventure*' -g '*trading*'
rg -n 'cmd_battle_attack|BattleManager' commands pokemon services tests
```

[pytest.ini](../pytest.ini) discovers both `tests` and `pokemon/battle/tests`.
The [mandatory runner](../tools/run_mandatory_tests.py) executes them in three
fresh-process orders. [Lifecycle CI](../.github/workflows/lifecycle-integrity.yml)
also invokes integration files by path. Use the
[testing index](testing/README.md) to distinguish test commands from dated proof.

Runtime module paths can also appear in
[server settings](../server/conf/settings.py), persisted Evennia typeclass
references, and migration history. Treat a future source move as a behavior
change requiring compatibility checks. Local caches and retained QA artifacts
are described in [workspace hygiene](workspace-hygiene.md).
