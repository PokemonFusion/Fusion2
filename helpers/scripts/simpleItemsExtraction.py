import re

# Define the item functions to be extracted
item_functions = [
    "onSetAbility",
    "onTakeItem",
    "onBasePower",
    "onAfterBoost",
    "onUpdate",
    "onTryEatItem",
    "onEat"
]

# Function to clean the TypeScript content
def clean_ts_content(ts_content):
    # Remove export statements and other problematic lines
    ts_content = re.sub(r'export\s+const\s+\w+\s*:\s*import\([^\)]+\)\.\w+\s*=\s*{', '{', ts_content)
    return ts_content

# Function to extract and replace item functions in TypeScript content
def extract_and_replace_item_functions(ts_content, functions):
    # Clean the TypeScript content
    ts_content = clean_ts_content(ts_content)

    func_pattern = re.compile(r'(\w+):\s*\((.*?)\)\s*{(.*?)}', re.DOTALL)
    func_definitions = []
    class_definitions = {}
    updated_entries = {}

    print("Starting extraction process...")
    print(f"Content length: {len(ts_content)}")

    # Print the first 1000 characters for debugging
    print(f"First 1000 characters:\n{ts_content[:1000]}\n")

    entry_name = "abilityshield"
    entry_content = ts_content

    for match in func_pattern.finditer(entry_content):
        func_name, func_args, func_body = match.groups()
        print(f"Match found in {entry_name}: {match.group(0)}")

        if func_name in functions:
            print(f"Extracting function: {func_name}")

            # Create a Python function definition within a class
            class_def = class_definitions.get(entry_name, f'class {entry_name.capitalize()}:\n')
            func_def = f'    def {func_name}(self, **kwargs):\n'
            func_body_lines = func_body.strip().split('\n')
            func_def += f'        """\n        Original arguments: {func_args}\n'
            for line in func_body_lines:
                func_def += f'        {line.strip()}\n'
            func_def += '        """\n        pass\n'
            class_def += func_def
            class_definitions[entry_name] = class_def

            entry_content = entry_content.replace(match.group(0), f'"{func_name}": {entry_name.capitalize()}().{func_name},')

    if not class_definitions:
        print("No functions were extracted.")

    for class_def in class_definitions.values():
        func_definitions.append(class_def)

    updated_entries[entry_name] = entry_content

    return updated_entries, func_definitions

# Sample TypeScript content
ts_content = """
abilityshield: {
    name: "Ability Shield",
    spritenum: 746,
    fling: {
        basePower: 30,
    },
    ignoreKlutz: true,
    // Neutralizing Gas protection implemented in Pokemon.ignoringAbility() within sim/pokemon.ts
    // and in Neutralizing Gas itself within data/abilities.ts
    onSetAbility(ability, target, source, effect) {
        if (effect && effect.effectType === 'Ability' && effect.name !== 'Trace') {
            this.add('-ability', source, effect);
        }
        this.add('-block', target, 'item: Ability Shield');
        return null;
    },
    // Mold Breaker protection implemented in Battle.suppressingAbility() within sim/battle.ts
    num: 1881,
    gen: 9,
},
"""

# Extract and replace item functions
updated_entries, items_funcs = extract_and_replace_item_functions(ts_content, item_functions)

# Reconstruct the Python dictionary content
py_items_content = "items = {\n"
for entry_name, entry_content in updated_entries.items():
    py_items_content += f'    "{entry_name}": {entry_content},\n'
py_items_content += "}"

# Save the Python dictionary to a file
output_py_file_path = "items.py"
output_funcs_file_path = "itemsFuncs.py"

with open(output_py_file_path, "w", encoding="utf-8") as py_file:
    py_file.write(py_items_content)
    print(f"Saved items.py to {output_py_file_path}")

# Save the functions to a separate file
with open(output_funcs_file_path, "w", encoding="utf-8") as funcs_file:
    if items_funcs:
        for func in items_funcs:
            funcs_file.write(func + "\n")
        print(f"Saved itemsFuncs.py to {output_funcs_file_path}")
    else:
        print(f"No functions were written to {output_funcs_file_path}")

print(f"Script completed.")
