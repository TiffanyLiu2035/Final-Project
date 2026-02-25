#!/usr/bin/env python3
"""Export all key metrics from 6 seeds x 4 groups JSON reports to one CSV table."""
import os
import sys
import json
import glob
import argparse

import pandas as pd

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SCRIPT_DIR)
SEEDS = [2, 15, 33, 38, 69, 95]
GROUPS = [1, 2, 3, 4]
MECHS = ["GSP", "Constrained"]
DEFAULT_INPUT = os.path.join(ROOT, "logs", "formal_experiment")
DEFAULT_OUTPUT = os.path.join(ROOT, "logs", "formal_experiment")


def load_reports(input_dir: str):
    out = []
    for seed in SEEDS:
        pattern = os.path.join(input_dir, f"experiment_report_seed{seed}_*.json")
        files = glob.glob(pattern)
        if not files:
            continue
        path = max(files, key=os.path.getmtime)
        with open(path, "r", encoding="utf-8") as f:
            out.append((seed, json.load(f)))
    return out


def extract_all_metrics(reports):
    rows = []
    for seed, report in reports:
        cr = report.get("comparison_report") or {}
        bg = cr.get("by_group") or {}
        for g in GROUPS:
            grp = bg.get(str(g))
            if not grp:
                continue
            comp = grp.get("comparison") or {}
            row = {"seed": seed, "group": g}
            for mech in MECHS:
                m = grp.get(mech) or {}
                row[f"slift_weighted_{mech}"] = m.get("slift_weighted")
                row[f"total_payment_{mech}"] = m.get("total_payment")
                es = (m.get("exposure_share_by_gender") or {}).get("female")
                row[f"exposure_female_share_{mech}"] = es
            row["kappa"] = comp.get("kappa")
            row["dTV"] = comp.get("dTV")
            row["impression_ratio"] = comp.get("impression_ratio")
            rows.append(row)
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser(description="Export formal experiment key metrics to one table (CSV).")
    ap.add_argument("--input-dir", default=DEFAULT_INPUT, help="Directory with experiment_report_seed*.json")
    ap.add_argument("--output", default=None, help="Output CSV path (default: <output-dir>/formal_experiment_all_metrics.csv)")
    ap.add_argument("--output-dir", default=DEFAULT_OUTPUT, help="Output directory when --output not set")
    args = ap.parse_args()

    os.chdir(ROOT)
    sys.path.insert(0, ROOT)

    reports = load_reports(args.input_dir)
    if not reports:
        print("No reports found.", file=sys.stderr)
        sys.exit(1)

    df = extract_all_metrics(reports)
    # Column order: seed, group, then by metric
    col_order = [
        "seed", "group",
        "slift_weighted_GSP", "slift_weighted_Constrained",
        "total_payment_GSP", "total_payment_Constrained",
        "exposure_female_share_GSP", "exposure_female_share_Constrained",
        "kappa", "dTV", "impression_ratio",
    ]
    df = df[[c for c in col_order if c in df.columns]]

    out_path = args.output
    if not out_path:
        out_path = os.path.join(args.output_dir, "formal_experiment_all_metrics.csv")
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    df.to_csv(out_path, index=False, float_format="%.6f")
    print(f"Saved {len(df)} rows to {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
