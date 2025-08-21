To convert the TypeScript data:

1. Place your `.ts` files in `helpers/scripts/ts/`.
2. Run the converter script:

   python helpers/scripts/ts_to_py.py

The script will generate JSON files in `helpers/scripts/json/` and Python
dictionaries in `helpers/scripts/py/`. Extracted function stubs are stored
under `helpers/scripts/py/functions/` grouped by dictionary type.
