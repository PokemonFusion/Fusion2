import json
import os

# Define the mappings for function files
function_files = {
    "pokedex": "fusion2/helpers/generated/pokefunc.py",
    "itemdex": "fusion2/helpers/generated/itemfunc.py",
    "abilitydex": "fusion2/helpers/generated/abilityfunc.py",
    "movedex": "fusion2/helpers/generated/funcmoves.py"
}

# Function to extract functions from the dictionary
def extract_functions_from_dict(py_dict_file, dict_type):
    with open(py_dict_file, 'r') as f:
        py_dict_data = f.read()
    py_dict = eval(py_dict_data.replace("py_dict = ", ""))

    function_data = []
    def extract_functions(d, path=""):
        for k, v in d.items():
            if isinstance(v, dict):
                extract_functions(v, f"{path}{k}.")
            elif isinstance(v, str) and v.startswith("`function"):
                function_name = f"{path}{k}"
                function_code = v.strip('`')
                function_data.append((function_name, function_code))
                d[k] = function_name

    extract_functions(py_dict)

    # Save functions to a file
    with open(function_files[dict_type], 'w') as f:
        for function_name, function_code in function_data:
            f.write(f"def {function_name}(self, **kwargs):\n")
            f.write(f"    '''\n")
            f.write(f"    {function_code}\n")
            f.write(f"    '''\n")
            f.write(f"    pass\n\n")

    # Save the updated Python dictionary
    with open(py_dict_file, 'w') as f:
        f.write("py_dict = " + json.dumps(py_dict, indent=4))

    # Confirm file creation
    if os.path.exists(function_files[dict_type]):
        print(f"{function_files[dict_type]} created successfully.")
    else:
        print(f"Failed to create {function_files[dict_type]}.")

# Main function to process the dictionaries and extract functions
def main():
    py_dict_files = {
        "pokedex": "fusion2/helpers/generated/pokedex.py",
        "itemdex": "fusion2/helpers/generated/itemdex.py",
        "abilitydex": "fusion2/helpers/generated/abilitydex.py",
        "movedex": "fusion2/helpers/generated/movedex.py"
    }

    for dict_type, py_dict_file in py_dict_files.items():
        extract_functions_from_dict(py_dict_file, dict_type)

if __name__ == "__main__":
    main()
