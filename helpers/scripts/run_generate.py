# fusion2/helpers/scripts/run_generate.py

from generate_dicts import process_ts_dictionary
import os

def main():
    # Specify the paths to your TypeScript files and the corresponding output files
    ts_files = {
        "pokedex": "fusion2/helpers/scripts/input/pokedex.ts",
        "itemdex": "fusion2/helpers/scripts/input/items.ts",
        "abilitydex": "fusion2/helpers/scripts/input/abilities.ts",
        "movedex": "fusion2/helpers/scripts/input/moves.ts"
    }

    for dict_type, ts_file in ts_files.items():
        if not os.path.isfile(ts_file):
            print(f"Error: {ts_file} not found.")
            continue
        
        output_file = f"fusion2/helpers/generated/{dict_type}.py"
        process_ts_dictionary(ts_file, output_file, dict_type)

if __name__ == "__main__":
    main()
