To convert the TypeScript learnset data:

1. Ensure `learnsets.ts` is located in `helpers/scripts/learnsets/ts/` (already provided).
2. Run the converter script:

   python helpers/scripts/learnsets/ts_to_py.py

The script will create a JSON version in `helpers/scripts/learnsets/json/` and
write a Python dictionary to `pokemon/data/learnsets/` as `learnsets.py`.
