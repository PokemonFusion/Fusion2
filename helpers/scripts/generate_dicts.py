import re
import json
import os

# Define the mappings for function files
function_files = {
    "pokedex": "fusion2/helpers/generated/pokefunc.py",
    "itemdex": "fusion2/helpers/generated/itemfunc.py",
    "abilitydex": "fusion2/helpers/generated/abilityfunc.py",
    "movedex": "fusion2/helpers/generated/funcmoves.py"
}

# Regex to find function definitions in TypeScript
function_regex = re.compile(r'(\w+)\s*:\s*function\s*\((.*?)\)\s*\{(.*?)\}', re.DOTALL)

# Helper function to find matching braces using a stack
def find_matching_brace(data, start_index):
    stack = []
    for index, char in enumerate(data[start_index:], start=start_index):
        if char == '{':
            stack.append(char)
        elif char == '}':
            if not stack:
                print(f"This should never happen, unbalanced braces detected. {index}")
                return -1  # This should never happen, indicates unbalanced braces
            stack.pop()
            if not stack:
                return index
    return -1

# Function to convert TypeScript dictionary to Python dictionary
def convert_ts_to_py(ts_file, dict_type):
    with open(ts_file, 'r') as f:
        ts_data = f.read()

    py_dict = {}
    classes = []

    def rename_key(key):
        key = re.sub(r'\W|^(?=\d)', '_', key)
        return key

    def extract_functions(entry_name, ts_data):
        matches = function_regex.findall(ts_data)
        function_map = {}
        class_methods = []
        for match in matches:
            func_name, args, body = match
            new_func_name = rename_key(func_name)
            full_func_name = f"{entry_name}.{new_func_name}"
            function_map[func_name] = full_func_name
            method_code = (
                f"    def {new_func_name}(self, **kwargs):\n"
                f"        '''\n"
                f"        Function originally from TypeScript for {entry_name}.\n"
                f"        '''\n"
                f"        # {body.strip().replace('\n', '\n        # ')}\n"
                f"        pass\n"
            )
            class_methods.append(method_code)
        return function_map, class_methods

    def transform_entry(entry_data):
        def process_nested_dicts(data):
            data = re.sub(r'(\w+):', r'"\1":', data)  # Add quotes around keys
            data = re.sub(r':\s*([^",\[\]\{\}\s]+)', r': "\1"', data)  # Add quotes around values
            data = re.sub(r':\s*true', r': true', data)  # Handle boolean values
            data = re.sub(r':\s*false', r': false', data)
            data = re.sub(r':\s*null', r': null', data)  # Handle null values
            return data

        entry_data = process_nested_dicts(entry_data)
        nested_dict_regex = re.compile(r'\{([^{}]*)\}')
        
        while nested_dict_regex.search(entry_data):
            entry_data = nested_dict_regex.sub(lambda m: f"{{{process_nested_dicts(m.group(1))}}}", entry_data)

        # Handle arrays by adding quotes around elements
        entry_data = re.sub(r'\[([^]]+)\]', lambda m: f"[{', '.join(f'\"{x.strip()}\"' if not (x.strip().startswith('"') and x.strip().endswith('"')) else x.strip() for x in m.group(1).split(','))}]", entry_data)
        return entry_data

    # Adjust regex to match the entire object, handling nested braces using a stack
    object_regex = re.compile(r'(\w+):\s*\{', re.DOTALL)
    entries = []
    for match in object_regex.finditer(ts_data):
        entry_name = match.group(1)
        start_index = match.end()
        end_index = find_matching_brace(ts_data, start_index)
        if end_index != -1:
            entry_data = ts_data[start_index:end_index + 1]
            entries.append((entry_name, entry_data))
        else:
            print(f"Error: No matching brace found for entry {entry_name}")

    if not entries:
        print("No entries found in the TypeScript data.")
    else:
        print(f"Found {len(entries)} entries.")

    for entry_name, entry_data in entries:
        print(f"Processing entry: {entry_name}")

        entry_name_py = rename_key(entry_name).capitalize()
        function_map, class_methods = extract_functions(entry_name_py, entry_data)

        # Replace function definitions with method calls in the entry data
        for ts_func, py_func in function_map.items():
            entry_data = entry_data.replace(f"{ts_func}: function", f'"{ts_func}": "{py_func}"')

        # Transform the entry data to valid JSON format
        entry_data = transform_entry(entry_data)

        # Print the modified entry data for debugging
        print(f"Debug: entry_data for {entry_name_py}: {entry_data}")

        # Convert the modified entry data to a Python dictionary
        try:
            entry_data_json = json.loads(f"{{{entry_data}}}")
            py_dict[entry_name_py] = entry_data_json
        except json.JSONDecodeError as e:
            print(f"JSONDecodeError: {e}")
            print(f"Problematic entry data: {entry_data}")
            raise e

        # Create the class for the entry
        class_code = f"class {entry_name_py}:\n"
        for method in class_methods:
            class_code += method + '\n'
        classes.append(class_code)

    return py_dict, classes

# Save the Python dictionary and classes to respective files
def save_py_dict(py_dict, py_file):
    with open(py_file, 'w') as f:
        f.write("py_dict = " + json.dumps(py_dict, indent=4))

def save_classes(classes, class_file):
    with open(class_file, 'w') as f:
        for class_code in classes:
            f.write(class_code + '\n\n')

# Main function to process TypeScript dictionaries
def process_ts_dictionary(ts_file, py_dict_file, dict_type):
    py_dict, classes = convert_ts_to_py(ts_file, dict_type)
    save_py_dict(py_dict, py_dict_file)
    save_classes(classes, function_files[dict_type])

    # Confirm file creation
    if os.path.exists(py_dict_file):
        print(f"{py_dict_file} created successfully.")
    else:
        print(f"Failed to create {py_dict_file}.")

    if os.path.exists(function_files[dict_type]):
        print(f"{function_files[dict_type]} created successfully.")
    else:
        print(f"Failed to create {function_files[dict_type]}.")

    # Append import statements in the generated dictionary file
    with open(py_dict_file, 'r+') as f:
        content = f.read()
        f.seek(0, 0)
        f.write(f"from {os.path.basename(function_files[dict_type]).replace('.py', '')} import *\n" + content)

