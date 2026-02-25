#!/bin/bash
# Run one seed (random each time). From project root: ./scripts/run_one_seed.sh
# Prefer Python with openai (otherwise MOCK)
cd "$(dirname "$0")/.."
if /usr/bin/python3 -c "from openai import OpenAI" 2>/dev/null; then
  PYTHONPATH=. /usr/bin/python3 scripts/run_one_seed.py
else
  PYTHONPATH=. python3 scripts/run_one_seed.py
fi
