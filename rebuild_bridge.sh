#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# Navigate to the script's directory to ensure paths are correct
cd "$(dirname "$0")"

PYPROJECT_FILE="pyproject.toml"

# Activate virtual environment if it exists (adjust path if needed)
if [ -d "venv" ]; then
  echo "Activating virtual environment..."
  source venv/bin/activate
else
  echo "Warning: No virtual environment found/activated."
fi

# 1. Uninstall existing package (ignore errors if not found)
echo "Uninstalling existing traderfit-bridge..."
pip uninstall -y traderfit-bridge || echo "traderfit-bridge not found or already uninstalled."

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
python -m build

# 4. Upload to PyPI using Twine
echo "Uploading package using Twine..."
# Ensure you have twine installed (pip install twine)
# You might need to configure credentials for twine (e.g., ~/.pypirc or environment variables)
python -m twine upload dist/*

# 5. Wait for PyPI to potentially update
echo "Waiting 5 seconds for PyPI index..."
sleep 5

# 6. Reinstall the package from PyPI
echo "Reinstalling traderfit-bridge version $new_version from PyPI..."
# Use --no-cache-dir to ensure the latest version is fetched
pip install --no-cache-dir traderfit-bridge==$new_version

echo "Process complete." 