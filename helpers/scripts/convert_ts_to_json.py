import re
import os

# Define the mappings for function files
ts_files = {
    "pokedex": "fusion2/helpers/scripts/input/pokedex.ts",
    "itemdex": "fusion2/helpers/scripts/input/items.ts",
    "abilitydex": "fusion2/helpers/scripts/input/abilities.ts",
    "movedex": "fusion2/helpers/scripts/input/moves.ts"
}

# Mapping of dictionary types to patterns that need to be removed
patterns_to_remove = {
    "pokedex": r"export const Pokedex: import\('../sim/dex-species'\)\.SpeciesDataTable = {",
    "movedex": r"// List of flags and their descriptions can be found in sim/dex-moves\.ts\n\nexport const Moves: import\('../sim/dex-moves'\)\.MoveDataTable = {",
    "itemdex": r"export const Items: import\('../sim/dex-items'\)\.ItemDataTable = {",
    "abilitydex": r"/\*.*?\*/\n\nexport const Abilities: import\('../sim/dex-abilities'\)\.AbilityDataTable = {",
}

# Helper function to convert TypeScript to JSON
def convert_ts_to_json(ts_file, json_file, dict_type):
    with open(ts_file, 'r') as f:
        ts_data = f.read()

    # Remove specific patterns
    ts_data = re.sub(patterns_to_remove[dict_type], "", ts_data, flags=re.DOTALL)

    # Replace TypeScript functions with string literals
    ts_data = re.sub(r'(\w+): function\s*\((.*?)\)\s*\{', r'"\1": "`function (\2) {', ts_data)
    ts_data = re.sub(r'\};', r'}`",', ts_data)
    ts_data = re.sub(r'\}$', r'}`', ts_data)

    # Add quotes around keys
    ts_data = re.sub(r'(\w+):', r'"\1":', ts_data)

    # Handle boolean and null values
    ts_data = re.sub(r':\s*true', r': true', ts_data)
    ts_data = re.sub(r':\s*false', r': false', ts_data)
    ts_data = re.sub(r':\s*null', r': null', ts_data)

    # Replace single quotes with double quotes except for 's
    ts_data = re.sub(r"([^a-zA-Z0-9])'(?!s)", r'\1"', ts_data)
    ts_data = re.sub(r"(?<!s)'([^a-zA-Z0-9])", r'"\1', ts_data)

    # Remove trailing commas
    ts_data = re.sub(r',\s*([\]}])', r'\1', ts_data)

    # Write the JSON data to file
    with open(json_file, 'w') as f:
        f.write("{\n")
        f.write(ts_data)
        f.write("\n}")

# Convert each TypeScript file to JSON
for dict_type, ts_file in ts_files.items():
    json_file = f"fusion2/helpers/scripts/input/{dict_type}.json"
    convert_ts_to_json(ts_file, json_file, dict_type)
    print(f"Converted {ts_file} to {json_file}")
