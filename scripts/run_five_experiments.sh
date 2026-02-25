#!/bin/bash
# Run 5 experiments in a row, each with a random seed. Run from project root:
#   nohup ./scripts/run_five_experiments.sh >> logs/run_5_experiments.log 2>&1 &
# or: ./scripts/run_five_experiments.sh
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH=.
PYTHON=python3
if /usr/bin/python3 -c "from openai import OpenAI" 2>/dev/null; then
  PYTHON=/usr/bin/python3
fi
mkdir -p logs
for i in 1 2 3 4 5; do
  echo ""
  echo "========== Run $i/5 =========="
  $PYTHON scripts/run_one_seed.py
  echo "========== Run $i/5 done =========="
done
echo ""
echo "All 5 runs completed."
