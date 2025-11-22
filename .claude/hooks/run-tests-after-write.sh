#!/bin/bash

# Post-Write Hook: Run unit tests after Python files are written
# Executes: pytest -m unit -n auto --tb=line -rfs

# Get the file path from the hook input
file_path="$1"

# Check if the file is a Python file
if [[ "$file_path" == *.py ]]; then
  echo "🧪 Running unit tests after writing: $file_path"
  echo ""

  # Run unit tests with parallel execution
  pytest -m unit -n auto --tb=line -rfs

  exit_code=$?

  exit $exit_code
else
  # Not a Python file, skip
  exit 0
fi
