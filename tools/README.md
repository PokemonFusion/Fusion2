# Tools

[Documentation home](../docs/index.md) | [Code map](../docs/code-map.md) |
[Application tests](../tests/README.md) | [Testing and evidence](../docs/testing/README.md)

## Find a tool

| Location | Purpose |
| --- | --- |
| [run_mandatory_tests.py](run_mandatory_tests.py) | Stable entry point for the canonical fresh-process test gate |
| [qa](qa/README.md) | Controlled battle/dex player QA, effect probes, case catalogs, server observers, coverage reports |
| [audits](audits/README.md) | Item availability/support reconciliation, CI inspection, organization reporting |
| [data_generation](data_generation/) | Upstream conversion and game-data generation |
| [item_scrapers](item_scrapers/) | Item scraping and comparison tools |

The former flat live-QA scripts are now under `tools/qa/`; the four audit
scripts are under `tools/audits/`. The mandatory gate retains its established
`python -B tools/run_mandatory_tests.py` command. The existing generation and
scraper folders retain their paths.

QA preparation and player runs can create fixtures or change game state. Read
the linked guide and prerequisites before executing them. See
[workspace hygiene](../docs/workspace-hygiene.md) for scratch and retained output.

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
