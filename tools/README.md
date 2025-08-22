# Tools

Utilities and data-generation scripts used to build game data.

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
