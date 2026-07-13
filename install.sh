#!/bin/bash
set -e

echo "Starting setup for Multi-LLM Agent..."

# 1. Setup Pi extensions
mkdir -p .pi/extensions

# Assuming you have the source file for the extension
EXTENSION_SRC=".pi/extensions/call_junior_llm_extension.ts"
EXTENSION_DEST=".pi/extensions/call_junior_llm_extension.ts"

if [ -f "$EXTENSION_SRC" ]; then
   echo "Extension already in place."
else
   echo "Error: Extension file not found at $EXTENSION_SRC. Please ensure it exists."
   exit 1
fi

# 2. Python dependencies
echo "Installing Python dependencies..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    echo "Warning: requirements.txt not found, skipping Python dependencies."
fi

echo "Setup complete!"
echo "Now restart Pi or run '/reload' in the Pi terminal to load the new extension."
