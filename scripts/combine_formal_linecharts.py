#!/usr/bin/env python3
"""Combine 6 seeds' line charts into one 2x3 figure. Supports slift_weighted or impression_ratio. impression_ratio is redrawn from data with unified y-axis."""
import argparse
import os
import sys
import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.image as mpimg

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SCRIPT_DIR)
DEFAULT_DIR = os.path.join(ROOT, "logs", "formal_experiment")
SEEDS = [2, 15, 33, 38, 69, 95]
GROUPS = [1, 2, 3, 4]
FILE_PATTERNS = {
    "slift": "05_slift_by_group_seed{seed}.png",
    "impression_ratio": "08_impression_ratio_by_group_seed{seed}.png",
}
DEFAULT_OUTPUTS = {
    "slift": "slift_weighted_6seeds_2x3.png",
    "impression_ratio": "impression_ratio_6seeds_2x3.png",
}
# Unified y-axis for impression_ratio 2x3 subplots
IMPRESSION_RATIO_YLIM = (0.90, 1.12)


def plot_impression_ratio_2x3_from_data(csv_path: str, out_path: str, dpi: int, ylim=IMPRESSION_RATIO_YLIM):
    """Read impression_ratio from CSV, redraw in 2x3 subplots with unified y-axis."""
    df = pd.read_csv(csv_path)
    fig, axes = plt.subplots(2, 3, figsize=(16, 10))
    axes = axes.flatten()
    x = np.arange(len(GROUPS))
    for ax, seed in zip(axes, SEEDS):
        sub = df[(df["seed"] == seed)].sort_values("group")
        ir = sub["impression_ratio"].values
        if len(ir) != len(GROUPS):
            ir = [np.nan] * len(GROUPS)
        ax.plot(x, ir, "o-", color="C4", linewidth=2, markersize=6)
        ax.axhline(y=1.0, color="gray", linestyle="--", alpha=0.7)
        ax.set_xticks(x)
        ax.set_xticklabels([f"Group{g}" for g in GROUPS])
        ax.set_ylabel("impression_ratio")
        ax.set_xlabel("Group")
        ax.set_title(f"Seed {seed}: impression_ratio by group")
        ax.set_ylim(ylim)
        ax.grid(True, alpha=0.3)
    plt.tight_layout()
    fig.savefig(out_path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out_path}")


def main():
    ap = argparse.ArgumentParser(description="Combine 6 seeds' line charts into 2x3 figure.")
    ap.add_argument("--metric", default="slift", choices=list(FILE_PATTERNS), help="slift or impression_ratio")
    ap.add_argument("--input-dir", default=DEFAULT_DIR, help="Directory containing per-seed PNGs or all_metrics CSV")
    ap.add_argument("--output", default=None, help="Output path (default: <input-dir>/<metric>_6seeds_2x3.png)")
    ap.add_argument("--dpi", type=int, default=150)
    ap.add_argument("--csv", default=None, help="All-metrics CSV for impression_ratio (default: <input-dir>/formal_experiment_all_metrics.csv)")
    args = ap.parse_args()

    out = args.output or os.path.join(args.input_dir, DEFAULT_OUTPUTS[args.metric])

    if args.metric == "impression_ratio":
        csv_path = args.csv or os.path.join(args.input_dir, "formal_experiment_all_metrics.csv")
        if not os.path.isfile(csv_path):
            print(f"CSV not found: {csv_path}", file=sys.stderr)
            sys.exit(1)
        plot_impression_ratio_2x3_from_data(csv_path, out, args.dpi)
        return

    # slift: paste images
    pattern = FILE_PATTERNS[args.metric]
    paths = [os.path.join(args.input_dir, pattern.format(seed=s)) for s in SEEDS]
    missing = [p for p in paths if not os.path.isfile(p)]
    if missing:
        print("Missing files:", missing, file=sys.stderr)
        sys.exit(1)
    fig, axes = plt.subplots(2, 3, figsize=(16, 10))
    axes = axes.flatten()
    for ax, path in zip(axes, paths):
        img = mpimg.imread(path)
        ax.imshow(img)
        ax.axis("off")
    plt.tight_layout()
    fig.savefig(out, dpi=args.dpi, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out}")


if __name__ == "__main__":
    main()
