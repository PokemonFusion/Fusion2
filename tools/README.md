# Tools

Utilities, data-generation scripts, test runners, and QA tooling.

[Documentation home](../docs/index.md) | [Code map](../docs/code-map.md) |
[Testing and evidence index](../docs/testing/README.md)

## Find a tool

| Task | Entry point |
| --- | --- |
| Run the canonical mandatory fresh-process gate | [run_mandatory_tests.py](run_mandatory_tests.py); see [offline testing](../docs/offline-battle-testing.md) |
| Audit item availability or reconcile support | [audit_item_availability.py](audit_item_availability.py), [reconcile_item_support.py](reconcile_item_support.py) |
| Find battle QA runner documentation | [Battle pilot guide](../docs/testing/live-battle-pilot.md), [live_battle_pilot.py](live_battle_pilot.py) |
| Find dex QA runner documentation | [Dex sweep guide](../docs/testing/live-dex-sweep.md), [live_dex_runner.py](live_dex_runner.py) |
| Find effect-probe tooling | [live_smoke_effects.py](live_smoke_effects.py) and its case/server modules |
| Inspect organization and CI assessment tooling | [org_score.py](org_score.py), [ci_assessor.py](ci_assessor.py) |
| Generate upstream data or scrape item information | The data-generation and item-scraper sections below |

Live QA tools can create fixtures or change game state. Read their documented
scope and prerequisites before running them. Keep scratch output and retained
observations in the locations described by [workspace hygiene](../docs/workspace-hygiene.md).

## data_generation

Scripts that convert upstream resources (mostly from TypeScript) into
JSON and Python modules. Outputs are written either to subdirectories of
this folder or into the project's `pokemon/data` and `pokemon/dex`
modules.

- `dex/ts_to_py.py` – converts dex data. Produces JSON under
  `tools/data_generation/dex/json/` and Python modules under
  `tools/data_generation/dex/py/` for use in `pokemon/dex`.
- `learnsets/ts_to_py.py` – processes `learnsets.ts`, generating JSON in
  `tools/data_generation/learnsets/json/` and
  `pokemon/data/learnsets/learnsets.py`.
- `text/ts_to_py.py` – converts text resources. Outputs JSON to
  `tools/data_generation/text/json/` and Python dictionaries to
  `pokemon/data/text/`.

## item_scrapers

Scripts for scraping and validating item information from Bulbapedia.

- `item_list_scraper.py` – scrapes item data and prints a JSON
  dictionary for inclusion in `pokemon/dex/items/itemsdex.py`.
- `pokeball_scraper.py` – scrapes Poké Ball information and prints a JSON
  dictionary for use in `pokemon/dex/items`.
- `compare_items.py` – compares scraped items with existing entries in
  `pokemon/dex/items/itemsdex.py`.
- `check_gain_info.py` – checks for missing experience/EV yield data
  using `pokemon.dex.pokedex` and `pokemon.dex.exp_ev_yields`.

The scrapers output data to the console; copy the results into the
appropriate modules under `pokemon/dex` or `pokemon/data` as needed.
