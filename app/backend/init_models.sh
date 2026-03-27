#!/usr/bin/env bash

# Runtime dependency check.
# ML packages (torch, sentence-transformers, etc.) are installed via the
# AI Engine wizard step, not at startup.

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd "$SCRIPT_DIR" || exit

echo "Checking runtime dependencies..."

if python -c "import torch" 2>/dev/null; then
    echo "ML packages available"
else
    echo "ML packages not installed. Use the AI Engine wizard step to install them."
fi

echo "Dependencies checked. Ready to start."
