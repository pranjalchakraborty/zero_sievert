#!/bin/bash

CONFIG_FILE="package_config.json"

# Ensure jq is installed
if ! command -v jq &> /dev/null
then
    echo "jq could not be found. Please install jq to proceed."
    exit 1
fi

# Ensure PyInstaller is installed
if ! command -v pyinstaller &> /dev/null
then
    echo "PyInstaller could not be found. Please install it using 'pip install pyinstaller'."
    exit 1
fi

# -------- PyInstaller Build Section --------

echo "Starting PyInstaller build process..."

# Read and iterate over each script to build
jq -c '.pyinstaller.scripts_to_build[]' "$CONFIG_FILE" | while read -r script; do
    source=$(echo "$script" | jq -r '.source' | tr -d '\r')
    output=$(echo "$script" | jq -r '.output_executable' | tr -d '\r')
    output_dir=$(dirname "$output")
    executable_name=$(basename "$output")

    # Check if source file exists
    if [ ! -f "$source" ]; then
        echo "Source file $source does not exist. Skipping."
        continue
    fi

    # Create output directory if it doesn't exist
    mkdir -p "$output_dir"

    # Run PyInstaller
    echo "Building $source -> $output_dir/$executable_name"
    pyinstaller --onefile --clean --noconfirm "$source" --dist "$output_dir" --name "$executable_name"

    if [ $? -ne 0 ]; then
        echo "Failed to build $source"
        exit 1
    fi
done

echo "PyInstaller build process completed successfully."

# -------- Setup Section --------

echo "Starting setup process..."

# Read setup configuration
TARGET_FOLDER=$(jq -r '.setup.target_folder' "$CONFIG_FILE")
FILES_TO_COPY=$(jq -c '.setup.files_to_copy[]' "$CONFIG_FILE")

# Delete existing contents
if [ -d "$TARGET_FOLDER" ]; then
    echo "Deleting existing contents in $TARGET_FOLDER"
    rm -rf "${TARGET_FOLDER:?}/"*
else
    echo "Creating target folder $TARGET_FOLDER"
    mkdir -p "$TARGET_FOLDER"
fi

# Create subfolders
echo "Creating subfolders..."
jq -r '.setup.subfolders[]' "$CONFIG_FILE" | while IFS= read -r folder; do
    folder="$(echo "$folder" | tr -d '\r')"
    mkdir -p "$TARGET_FOLDER/$folder"
    echo "Created $TARGET_FOLDER/$folder"
done

# Copy files
echo "Copying files..."
echo "$FILES_TO_COPY" | while read -r file; do
    src=$(echo "$file" | jq -r '.source')
    dest=$(echo "$file" | jq -r '.destination')

    if [ ! -f "$src" ]; then
        echo "Source file $src does not exist. Skipping."
        continue
    fi

    cp "$src" "$dest"
    echo "Copied $src to $dest"
done

echo "Setup process completed successfully."
echo "All operations finished."
