To convert the TypeScript data:

1. Place your `.ts` files in `tools/data_generation/dex/ts/`.
2. Run the converter script:

   python tools/data_generation/dex/ts_to_py.py

The script will generate JSON files in `tools/data_generation/dex/json/` and Python
dictionaries in `tools/data_generation/dex/py/`. Extracted function stubs are stored
under `tools/data_generation/dex/py/functions/` grouped by dictionary type.
