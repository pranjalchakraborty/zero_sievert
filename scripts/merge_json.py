#!/usr/bin/env python3
import os
import json5 as json
import shutil
from pathlib import Path
import sys
import traceback

def load_json(file_path):
    """Safely load JSON from a file, returning None on error."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Could not load {file_path}: {e}")
        return None

def save_json(data, file_path):
    """Save Python object as JSON with indentation."""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False, quote_keys=True)
    except Exception as e:
        print(f"Could not save {file_path}: {e}")

def merge_string_arrays(parent_list, delta_list, strategy):
    """Merge two lists of strings according to the specified strategy."""
    if strategy == "ignore":
        return parent_list
    elif strategy == "merge":
        # Merge uniquely
        return list(set(parent_list + delta_list))
    elif strategy == "replace":
        # Replace entirely
        return delta_list
    # Fallback
    return parent_list

def merge_object_arrays(parent_list, delta_list, new_id_strategy):
    """
    Merge arrays of objects based on 'item' as an identifier.
    - "merge": If delta has an object with an 'item' that doesn't exist in parent, add it.
               If it exists, merge the object.
    - "only":  Only add new objects (by ID); existing objects remain untouched.
    - "only_ask": Same as "only" but prompt the user for each new object.
    """
    parent_dict = {}
    delta_dict = {}

    for obj in parent_list:
        if isinstance(obj, dict) and "item" in obj:
            parent_dict[obj["item"]] = obj

    for obj in delta_list:
        if isinstance(obj, dict) and "item" in obj:
            delta_dict[obj["item"]] = obj

    for key, val in delta_dict.items():
        if key in parent_dict:
            if new_id_strategy == "merge":
                parent_dict[key] = merge_json(parent_dict[key], val,
                                              array_merge_strategy="merge",
                                              new_id_strategy=new_id_strategy,
                                              excluded_fields=[])
            # For "only" and "only_ask", do not modify existing IDs.
        else:
            if new_id_strategy == "merge":
                parent_dict[key] = val
            elif new_id_strategy == "only":
                parent_dict[key] = val
            elif new_id_strategy == "only_ask":
                answer = input(f"New ID '{key}' encountered. Add it? [y/n]: ")
                if answer.lower().startswith('y'):
                    parent_dict[key] = val

    return list(parent_dict.values())

def merge_json(parent, delta,
               array_merge_strategy="merge",
               new_id_strategy="merge",
               excluded_fields=None):
    """
    Recursively merge 'delta' into 'parent'.
      - array_merge_strategy in {ignore, merge, replace}
      - new_id_strategy in {ignore, merge, only, only_ask}
      - excluded_fields is a list of field names to skip entirely
    """
    if excluded_fields is None:
        excluded_fields = []

    if isinstance(parent, dict) and isinstance(delta, dict):
        for key, value in delta.items():
            # Skip excluded fields
            if key in excluded_fields:
                continue

            # Special handling for ID container under key "data"
            if key == "data" and isinstance(value, dict):
                # If parent doesn't have "data" or it's not a dict, simply add it.
                if key not in parent or not isinstance(parent.get(key), dict):
                    if new_id_strategy == "only_ask":
                        # For each new ID in "data", ask user individually.
                        new_data = {}
                        for subkey, subvalue in value.items():
                            if subkey in excluded_fields:
                                continue
                            answer = input(f"New ID '{subkey}' encountered in 'data'. Add it? [y/n]: ")
                            if answer.lower().startswith('y'):
                                new_data[subkey] = subvalue
                        parent[key] = new_data
                    elif new_id_strategy in ("merge", "only"):
                        # Add entire "data" as new.
                        new_data = { sk: sv for sk, sv in value.items() if sk not in excluded_fields }
                        parent[key] = new_data
                    # For "ignore", do nothing.
                    continue
                else:
                    # Both parent and delta have "data" as dict.
                    for subkey, subvalue in value.items():
                        if subkey in excluded_fields:
                            continue
                        if subkey not in parent[key]:
                            if new_id_strategy == "only_ask":
                                answer = input(f"New ID '{subkey}' encountered in 'data'. Add it? [y/n]: ")
                                if answer.lower().startswith('y'):
                                    parent[key][subkey] = subvalue
                            elif new_id_strategy in ("merge", "only"):
                                parent[key][subkey] = subvalue
                            # For "ignore", do nothing.
                        else:
                            if new_id_strategy == "merge":
                                parent[key][subkey] = merge_json(parent[key][subkey], subvalue,
                                                                  array_merge_strategy=array_merge_strategy,
                                                                  new_id_strategy=new_id_strategy,
                                                                  excluded_fields=excluded_fields)
                            # For "only" and "only_ask", do not modify existing IDs.
                    continue

            if key not in parent:
                if new_id_strategy == "only_ask":
                    answer = input(f"New key '{key}' encountered. Add it? [y/n]: ")
                    if answer.lower().startswith('y'):
                        parent[key] = value
                elif new_id_strategy in ("merge", "only"):
                    parent[key] = value
                # For "ignore", do nothing.
                continue

            # For keys that exist in both parent and delta (and are not the special "data" case)
            if isinstance(value, dict) and isinstance(parent.get(key), dict):
                parent[key] = merge_json(parent[key], value,
                                         array_merge_strategy=array_merge_strategy,
                                         new_id_strategy=new_id_strategy,
                                         excluded_fields=excluded_fields)
            elif isinstance(value, list) and isinstance(parent.get(key), list):
                if len(value) > 0 and all(isinstance(item, dict) for item in value):
                    parent[key] = merge_object_arrays(parent.get(key, []), value, new_id_strategy)
                elif len(value) > 0 and all(isinstance(item, str) for item in value):
                    parent[key] = merge_string_arrays(parent.get(key, []), value, array_merge_strategy)
                else:
                    parent[key] = value
            else:
                parent[key] = value
    return parent

def process_folders(folder_1, folder_2, folder_3,
                    excluded_files=None,
                    array_merge_strategy="merge",
                    new_id_strategy="merge",
                    excluded_fields=None):
    """
    Recursively walk 'folder_1' (parent JSONs) and 'folder_2' (delta JSONs),
    merge them, and output into 'folder_3'.
    """
    if excluded_files is None:
        excluded_files = []
    if excluded_fields is None:
        excluded_fields = []

    folder_1_path = Path(folder_1)
    folder_2_path = Path(folder_2)
    folder_3_path = Path(folder_3)

    folder_3_path.mkdir(parents=True, exist_ok=True)

    # Traverse folder_1
    for root, _, files in os.walk(folder_1_path):
        # Calculate relative path to replicate structure in folder_3
        relative = Path(root).relative_to(folder_1_path)
        target_dir = folder_3_path / relative
        target_dir.mkdir(parents=True, exist_ok=True)

        for file_name in files:
            if file_name in excluded_files:
                continue

            source_1 = folder_1_path / relative / file_name
            source_2 = folder_2_path / relative / file_name
            dest_3 = target_dir / file_name

            # Only merge if JSON
            if source_1.suffix.lower() == ".json":
                parent_data = load_json(source_1)
                delta_data = load_json(source_2) if source_2.exists() else None

                if parent_data is None:
                    shutil.copy(source_1, dest_3)
                    continue

                if delta_data is not None:
                    merged = merge_json(
                        parent_data,
                        delta_data,
                        array_merge_strategy=array_merge_strategy,
                        new_id_strategy=new_id_strategy,
                        excluded_fields=excluded_fields
                    )
                    save_json(merged, dest_3)
                else:
                    save_json(parent_data, dest_3)
            else:
                if source_1.is_file():
                    shutil.copy2(source_1, dest_3)

def main():
    # Example usage:
    # python merge_script.py

    # Get the script name without the .py extension
    script_name = os.path.splitext(os.path.basename(__file__))[0]

    # Define the path to config.json relative to the script's location
    config_path = os.path.join('..', 'scripts_config.json')  # Adjust the path as needed

    if not os.path.exists(config_path):
        print(f"Configuration file not found at {config_path}")
        sys.exit(1)

    with open(config_path, 'r', encoding='utf-8') as config_file:
        config = json.load(config_file)

    script_config = config.get(script_name)
    if script_config is None:
        print(f"No configuration found for script: {script_name}")
        sys.exit(1)

    for key, value in script_config.items():
        globals()[key] = value

    process_folders(
        input_folder,
        change_folder,
        output_folder,
        excluded_files=None,
        array_merge_strategy=array_merge_strategy,
        new_id_strategy=new_id_strategy,
        excluded_fields=excluded_fields
    )
    print("Done merging.")

if __name__ == "__main__":
    try:
        main()
        print("Script finished successfully.")
    except Exception as e:
        error_message = traceback.format_exc()
        print("An error occurred:\n", error_message)
    finally:
        input("\nPress Enter to exit...")
