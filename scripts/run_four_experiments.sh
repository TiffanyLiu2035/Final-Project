#!/bin/bash
# Run 4 experiments (each with random seed). Run from project root:
#   nohup ./scripts/run_four_experiments.sh > logs/run_4_experiments.log 2>&1 &
# or: ./scripts/run_four_experiments.sh
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH=.
PYTHON=python3
if /usr/bin/python3 -c "from openai import OpenAI" 2>/dev/null; then
  PYTHON=/usr/bin/python3
fi
mkdir -p logs
for i in 1 2 3 4; do
  echo ""
  echo "========== Run $i/4 =========="
  $PYTHON scripts/run_one_seed.py
  echo "========== Run $i/4 done =========="
done
echo ""
echo "All 4 runs completed."
