To convert the TypeScript learnset data:

1. Ensure `learnsets.ts` is located in `tools/data_generation/learnsets/ts/` (already provided).
2. Run the converter script:

   python tools/data_generation/learnsets/ts_to_py.py

The script will create a JSON version in `tools/data_generation/learnsets/json/` and
write a Python dictionary to `pokemon/data/learnsets/` as `learnsets.py`.
