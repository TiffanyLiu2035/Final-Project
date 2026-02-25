#!/usr/bin/env python3
"""
Run one seed: set EXPERIMENT_RANDOM_SEED and run main.py.
Outputs: (1) logs/run_seed{N}_terminal.log  (2) logs/experiment_report_seed{N}_{timestamp}.json
Usage (project root): PYTHONPATH=. python scripts/run_one_seed.py [seed]
  run_one_seed.py      # random seed   run_one_seed.py 2   # seed 2
"""
import os
import random

try:
    from dotenv import load_dotenv
    _script_dir = os.path.dirname(os.path.abspath(__file__))
    _proj_root = os.path.dirname(_script_dir)
    load_dotenv(os.path.join(_proj_root, ".env"))
except ImportError:
    pass
import re
import sys
import shutil
import subprocess
from pathlib import Path
from typing import Optional

# Seed range 1--100
SEED_MIN, SEED_MAX = 1, 100
LOGS_DIR = "logs"
REPORT_PREFIX = "experiment_report_"
SEED_REPORT_PATTERN = re.compile(r"experiment_report_seed(\d+)_(\d{8}_\d{6})\.json")


def project_root() -> Path:
    root = Path(__file__).resolve().parent.parent
    return root


def logs_path() -> Path:
    return project_root() / LOGS_DIR


def _load_dotenv_into(env: dict, root: Path) -> None:
    """Load .env from project root into env for subprocess."""
    path = root / ".env"
    if not path.is_file():
        print("[run_one_seed] No .env found; subprocess will use current env")
        return
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                k, v = k.strip(), v.strip().strip('"').strip("'")
                if k:
                    env[k] = v
    if "OPENAI_API_KEY" in env and env["OPENAI_API_KEY"]:
        print("[run_one_seed] OPENAI_API_KEY loaded from .env (len %d)" % len(env["OPENAI_API_KEY"]))
    else:
        print("[run_one_seed] Warning: no valid OPENAI_API_KEY in .env; subprocess may use MOCK")


def choose_random_seed() -> int:
    """Pick a random seed (record printed seed for reproducibility)."""
    return random.randint(SEED_MIN, SEED_MAX)


def run_main(seed: int) -> int:
    """Set EXPERIMENT_RANDOM_SEED and run main.py; terminal output to logs/run_seed{N}_terminal.log."""
    root = project_root()
    logs = root / LOGS_DIR
    logs.mkdir(parents=True, exist_ok=True)
    terminal_log = logs / f"run_seed{seed}_terminal.log"
    print(f"Terminal output -> {terminal_log} (tail -f to watch)")
    env = os.environ.copy()
    _load_dotenv_into(env, root)
    env["EXPERIMENT_RANDOM_SEED"] = str(seed)
    cmd = [sys.executable, str(root / "main.py")]
    with open(terminal_log, "w", encoding="utf-8") as f:
        ret = subprocess.run(cmd, cwd=str(root), env=env, stdout=f, stderr=subprocess.STDOUT)
    print(f"  Terminal log saved: {terminal_log}")
    return ret.returncode


def latest_plain_report() -> Optional[Path]:
    """Return latest experiment_report_*.json in logs (excluding experiment_report_seed*_*.json)."""
    logs = logs_path()
    if not logs.is_dir():
        return None
    candidates = []
    for f in logs.glob("experiment_report_*.json"):
        if SEED_REPORT_PATTERN.match(f.name):
            continue
        # experiment_report_YYYYMMDD_HHMMSS.json
        candidates.append(f)
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def copy_to_seed_report(seed: int) -> Optional[Path]:
    """Copy latest experiment_report_*.json to experiment_report_seed{N}_*.json. Return dest path or None."""
    src = latest_plain_report()
    if src is None:
        return None
    base = src.name
    if not base.startswith(REPORT_PREFIX) or not base.endswith(".json"):
        return None
    middle = base[len(REPORT_PREFIX) : -len(".json")]
    dest_name = f"experiment_report_seed{seed}_{middle}.json"
    dest = src.parent / dest_name
    shutil.copy2(src, dest)
    return dest


def main() -> int:
    root = project_root()
    os.chdir(root)
    if len(sys.argv) >= 2 and sys.argv[1].strip().isdigit():
        seed = int(sys.argv[1].strip())
        if not (SEED_MIN <= seed <= SEED_MAX):
            print(f"Seed should be in [{SEED_MIN},{SEED_MAX}], using {seed}", file=sys.stderr)
    else:
        seed = choose_random_seed()
    print(f"Using seed: {seed}")

    terminal_log = logs_path() / f"run_seed{seed}_terminal.log"
    ret = run_main(seed)

    report_path = copy_to_seed_report(seed)
    if report_path is not None:
        print(f"  Report copied: {report_path}")
    print("")
    print("=" * 60)
    print("Outputs")
    print("=" * 60)
    print(f"  1) Terminal log: {terminal_log}")
    if report_path is not None:
        print(f"  2) Report:      {report_path}")
    else:
        print(f"  2) Report:      (none — check logs/ for experiment_report_*.json)")
    print("=" * 60)
    if ret != 0:
        print(f"main.py exit code: {ret}", file=sys.stderr)
    return ret


if __name__ == "__main__":
    sys.exit(main())
