To convert the TypeScript text data:

1. Place the `.ts` files in `tools/data_generation/text/ts/` (already provided).
2. Run the converter script:

   python tools/data_generation/text/ts_to_py.py

The script will create JSON versions in `tools/data_generation/text/json/` and
write Python dictionaries to `pokemon/data/text/`.
Each module in `pokemon/data/text/` defines a constant like
`ABILITIES_TEXT` or `MOVEDEX_TEXT` that contains the dictionary data.
