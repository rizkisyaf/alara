#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# Navigate to the script's directory to ensure paths are correct
cd "$(dirname "$0")"

PYPROJECT_FILE="pyproject.toml"

# --- Recreate Virtual Environment --- #

# 1. Remove existing venv if it exists
echo "Removing old virtual environment (if any)..."
rm -rf venv

# 2. Create a new virtual environment
echo "Creating new virtual environment..."
python3 -m venv venv

# 3. Activate virtual environment (for consistency, though we use explicit paths)
# Not strictly needed now, but good practice
echo "Activating virtual environment..."
source venv/bin/activate

# 4. Install necessary build/upload tools into the NEW venv
echo "Installing build tools (build, twine, setuptools) into venv..."
./venv/bin/pip install --upgrade pip build twine "setuptools>=61.0"

# --- End Recreate Virtual Environment --- #

# 1. Uninstall existing package (ignore errors if not found)
echo "Uninstalling existing alara..."
./venv/bin/pip uninstall -y alara || echo "alara not found or already uninstalled."

# 2. Remove old distribution files
echo "Removing old dist directory..."
rm -rf dist

# --- Increment Version --- 
echo "Incrementing package version in $PYPROJECT_FILE..."
# Read current version
current_version=$(grep '^version = "' $PYPROJECT_FILE | awk -F '"' '{print $2}')
if [ -z "$current_version" ]; then
    echo "Error: Could not find current version in $PYPROJECT_FILE" >&2
    exit 1
fi
echo "Current version: $current_version"

# Increment patch version
new_version=$(echo $current_version | awk -F. '{printf("%d.%d.%d", $1, $2, $3+1)}')
echo "New version: $new_version"

# Update pyproject.toml (using sed -i for in-place edit)
# macOS requires '-i ""' for in-place editing without backup
if [[ "$OSTYPE" == "darwin"* ]]; then
  sed -i "" "s/^version = \".*\"/version = \"$new_version\"/" $PYPROJECT_FILE
else
  sed -i "s/^version = \".*\"/version = \"$new_version\"/" $PYPROJECT_FILE
fi
echo "Version updated in $PYPROJECT_FILE"
# --- End Increment Version --- 

# 3. Build the new package
echo "Building new package (version $new_version)..."
./venv/bin/python3 -m build

# 4. Upload to PyPI using Twine
echo "Uploading package using Twine..."
# Ensure you have twine installed (pip install twine)
# You might need to configure credentials for twine (e.g., ~/.pypirc or environment variables)
./venv/bin/python3 -m twine upload dist/*

# 5. Wait for PyPI to potentially update
echo "Waiting 5 seconds for PyPI index..."
sleep 5

# 6. Reinstall the package from PyPI
echo "Reinstalling alara version $new_version from PyPI..."
# Use --no-cache-dir to ensure the latest version is fetched
./venv/bin/pip install --no-cache-dir alara==$new_version

echo "Process complete." 