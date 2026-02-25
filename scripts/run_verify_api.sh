#!/bin/bash
# Install openai (from requirements.txt) and run API key verification.
# Run from project root: bash scripts/run_verify_api.sh

set -e
cd "$(dirname "$0")/.."
echo "Installing openai (pip install openai)..."
pip install openai -q
echo "Running verify_openai_api.py..."
PYTHONPATH=. python scripts/verify_openai_api.py
