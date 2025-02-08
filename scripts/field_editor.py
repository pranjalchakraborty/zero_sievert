import os
import json
import sys
from typing import Any, List, Tuple
import traceback

def update_field_in_json(data: Any, field: str, adder: int, multiplier: int, updates: List[Tuple[int, int]]) -> Any:
    """
    Recursively traverse the JSON data and update the specified field by multiplying its value.
    
    Args:
        data (Any): The JSON data (dict, list, etc.).
        field (str): The field name to update.
        multiplier (int): The multiplier to apply to the field's value.
        updates (List[Tuple[int, int]]): List to store original and new values.
    
    Returns:
        Any: The updated JSON data.
    """
    if isinstance(data, dict):
        for key, value in data.items():
            if key == field and isinstance(value, (int, float)):
                original_value = value
                data[key] = (value+adder) * multiplier
                updates.append((original_value, data[key]))
            else:
                data[key] = update_field_in_json(value, field, adder, multiplier, updates)
    elif isinstance(data, list):
        for index, item in enumerate(data):
            data[index] = update_field_in_json(item, field, adder, multiplier, updates)
    return data

def process_file(input_file_path: str, output_file_path: str, field: str, adder: int, multiplier: int):
    """
    Reads a JSON file, updates the specified field, and writes the updated JSON to the output path.
    
    Args:
        input_file_path (str): Path to the input JSON file.
        output_file_path (str): Path to save the updated JSON file.
        field (str): The field name to update.
        multiplier (int): The multiplier to apply to the field's value.
    """
    updates = []
    try:
        with open(input_file_path, 'r', encoding='utf-8') as infile:
            data = json.load(infile)
        
        updated_data = update_field_in_json(data, field, adder, multiplier, updates)
        
        with open(output_file_path, 'w', encoding='utf-8') as outfile:
            json.dump(updated_data, outfile, indent=4)
        
        print(f'Processing file: {input_file_path} -> {output_file_path}')
        if updates:
            updates_str = ', '.join([f'{orig} -> {new}' for orig, new in updates])
            print(f'Updated "{field}": {updates_str}')
        else:
            print(f'No "{field}" key found.')
        print('Done.')
    
    except json.JSONDecodeError as jde:
        print(f'JSON decode error in file {input_file_path}: {jde}')
    except Exception as e:
        print(f'Error processing file {input_file_path}: {e}')

def process_folder(input_folder: str, output_folder: str, field: str, adder: int, multiplier: int):
    """
    Processes all JSON files in the input folder, updates the specified field, and saves them to the output folder.
    
    Args:
        input_folder (str): Path to the input folder containing JSON files.
        output_folder (str): Path to the output folder to save updated JSON files.
        field (str): The field name to update.
        multiplier (int): The multiplier to apply to the field's value.
    """
    if not os.path.isdir(input_folder):
        print(f'The input path "{input_folder}" is not a valid directory.')
        return
    
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    # Iterate over all files in the input directory
    for filename in os.listdir(input_folder):
        input_file_path = os.path.join(input_folder, filename)
        
        # Process only files (skip directories)
        if not os.path.isfile(input_file_path):
            continue
        
        # Process only JSON files
        if not filename.lower().endswith('.json'):
            continue
        
        output_file_path = os.path.join(output_folder, filename)
        process_file(input_file_path, output_file_path, field, adder, multiplier)

def main():
    # Get the script name without the .py extension
    script_name = os.path.splitext(os.path.basename(__file__))[0]
    
    # Define the path to config.json relative to the script's location
    config_path = os.path.join('..', 'scripts_config.json')  # Adjust the path as needed
    
    # Check if config.json exists
    if not os.path.exists(config_path):
        print(f"Configuration file not found at {config_path}")
        sys.exit(1)
    
    # Load the JSON configuration
    with open(config_path, 'r') as config_file:
        config = json.load(config_file)
    
    # Retrieve the configuration for the current script
    script_config = config.get(script_name)
    if script_config is None:
        print(f"No configuration found for script: {script_name}")
        sys.exit(1)
    
    # Dynamically assign configuration parameters as variables
    for key, value in script_config.items():
        globals()[key] = value
    
    
    # Process the folder
    process_folder(input_folder, output_folder, field, adder, multiplier)

if __name__ == "__main__":
    try:
        main()
        print("Script finished successfully.")
    except Exception as e:
        error_message = traceback.format_exc()  # Capture full traceback
        print("An error occurred:\n", error_message)  # Print explicitly
    finally:
        input("\nPress Enter to exit...")
