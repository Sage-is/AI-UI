#!/usr/bin/env bash

# Runtime dependency check.
# AI Engine packages (torch, sentence-transformers, etc.) are installed via the
# AI Engine wizard step, not at startup.

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd "$SCRIPT_DIR" || exit

echo ""
if python -c "import torch" 2>/dev/null; then
    echo "AI Engine ready"
else
    echo "AI Engine not installed. Use the setup wizard to install it."
fi
echo ""
