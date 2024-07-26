import os
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

# Function to isolate each dictionary entry
def isolate_entries(ts_content):
    entries = {}
    entry_pattern = re.compile(r'(\w+):\s*{', re.DOTALL)
    brace_counter = 0
    first_brace_found = False
    current_entry = None
    entry_start = 0

    for i, char in enumerate(ts_content):
        if char == '{':
            if not first_brace_found:
                first_brace_found = True
                continue
            if brace_counter == 0:
                entry_start = i
                match = entry_pattern.search(ts_content[i-30:i])  # Look 30 characters back to find the key
                if match:
                    current_entry = match.group(1)
                    print(f"Starting entry: {current_entry}")
            brace_counter += 1
        elif char == '}':
            brace_counter -= 1
            if brace_counter == -1 and current_entry:
                entry_end = i + 1
                entries[current_entry] = ts_content[entry_start:entry_end]
                print(f"Completed entry: {current_entry}")
                current_entry = None
                brace_counter = 0  # Reset counter for the next entry

    return entries

# Function to extract and replace item functions in TypeScript content
def extract_and_replace_item_functions(entries, functions):
    func_pattern = re.compile(r'(\w+):\s*\((.*?)\)\s*{(.*?)}', re.DOTALL)
    func_definitions = []
    class_definitions = {}
    updated_entries = {}

    print("Starting extraction process...")

    for entry_name, entry_content in entries.items():
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

        updated_entries[entry_name] = entry_content

    if not class_definitions:
        print("No functions were extracted.")

    for class_def in class_definitions.values():
        func_definitions.append(class_def)

    return updated_entries, func_definitions

# Define the input and output paths
input_file_path = "fusion2/helpers/scripts/input/items.ts"
output_py_file_path = "fusion2/helpers/scripts/output/items.py"
output_funcs_file_path = "fusion2/helpers/scripts/output/itemsFuncs.py"

# Ensure the output directory exists
os.makedirs(os.path.dirname(output_py_file_path), exist_ok=True)

# Load the content of the TypeScript file (items.ts)
print(f"Loading TypeScript file from {input_file_path}")
if not os.path.exists(input_file_path):
    print(f"Error: File {input_file_path} not found!")
else:
    with open(input_file_path, "r", encoding="utf-8") as file:
        ts_items_content = file.read()

    # Clean the TypeScript content
    ts_items_content = clean_ts_content(ts_items_content)

    # Isolate each dictionary entry
    entries = isolate_entries(ts_items_content)

    # Extract and replace item functions
    updated_entries, items_funcs = extract_and_replace_item_functions(entries, item_functions)

    # Reconstruct the Python dictionary content
    py_items_content = "items = {\n"
    for entry_name, entry_content in updated_entries.items():
        py_items_content += f'    "{entry_name}": {entry_content},\n'
    py_items_content += "}"

    # Save the Python dictionary to a file
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
