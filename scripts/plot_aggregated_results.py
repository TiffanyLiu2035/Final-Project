#!/usr/bin/env python3
"""
Aggregate 6 seeds (2, 15, 33, 38, 69, 95) and plot 5 publication-quality grouped bar charts
with error bars: slift_weighted, total_payment, exposure_female_share, kappa, dTV.
Reads from experiment_report_seed*.json in logs/formal_experiment (or --input-dir).
"""
import os
import sys
import json
import argparse
import glob

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Seaborn Set1-like colors (no seaborn dependency)
COLOR_GSP = "#e41a1c"
COLOR_CONSTRAINED = "#377eb8"

SEEDS = [2, 15, 33, 38, 69, 95]
GROUPS = [1, 2, 3, 4]
MECHS = ["GSP", "Constrained"]
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SCRIPT_DIR)
DEFAULT_INPUT = os.path.join(ROOT, "logs", "formal_experiment")
DEFAULT_OUTPUT = os.path.join(ROOT, "logs", "formal_experiment")


def load_reports(input_dir: str):
    """Load experiment_report_seed*.json for SEEDS; return list of (seed, report)."""
    out = []
    for seed in SEEDS:
        pattern = os.path.join(input_dir, f"experiment_report_seed{seed}_*.json")
        files = glob.glob(pattern)
        if not files:
            print(f"Warning: no report for seed {seed} in {input_dir}", file=sys.stderr)
            continue
        # take latest if multiple
        path = max(files, key=os.path.getmtime)
        with open(path, "r", encoding="utf-8") as f:
            out.append((seed, json.load(f)))
    return out


def extract_metrics(reports):
    """From reports, build DataFrames: one row per (seed, group) with all metrics."""
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


def aggregate_by_group(df: pd.DataFrame):
    """For each group and each metric, compute mean and std across seeds."""
    agg = {}
    for g in GROUPS:
        sub = df[df["group"] == g]
        if sub.empty:
            continue
        agg[g] = {}
        for mech in MECHS:
            for name in ["slift_weighted", "total_payment", "exposure_female_share"]:
                col = f"{name}_{mech}"
                if col not in sub.columns:
                    continue
                vals = sub[col].dropna()
                agg[g][f"{name}_{mech}_mean"] = vals.mean()
                agg[g][f"{name}_{mech}_std"] = vals.std() if len(vals) > 1 else 0.0
        for name in ["kappa", "dTV", "impression_ratio"]:
            if name not in sub.columns:
                continue
            vals = sub[name].dropna()
            agg[g][f"{name}_mean"] = vals.mean()
            agg[g][f"{name}_std"] = vals.std() if len(vals) > 1 else 0.0
    return agg


def plot_grouped_bars(ax, groups, means_gsp, means_con, stds_gsp, stds_con,
                      ylabel, title, ylim=None, ref_line=None):
    """Grouped bar chart: GSP vs Constrained per group, with error bars."""
    x = np.arange(len(groups))
    w = 0.35
    ax.bar(x - w / 2, means_gsp, w, yerr=stds_gsp, capsize=4,
           label="GSP", color=COLOR_GSP, edgecolor="black", linewidth=0.5)
    ax.bar(x + w / 2, means_con, w, yerr=stds_con, capsize=4,
           label="Constrained", color=COLOR_CONSTRAINED, edgecolor="black", linewidth=0.5)
    if ref_line is not None:
        ax.axhline(y=ref_line, color="gray", linestyle="--", linewidth=1, label=f"Target (y={ref_line})")
    ax.set_ylabel(ylabel, fontsize=11)
    ax.set_title(title, fontsize=12)
    ax.set_xticks(x)
    ax.set_xticklabels([f"Group {g}" for g in groups])
    ax.legend(loc="best", fontsize=9)
    if ylim is not None:
        ax.set_ylim(ylim)
    ax.set_axisbelow(True)
    ax.grid(axis="y", alpha=0.3)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


def plot_single_bars(ax, groups, means, stds, ylabel, title, ylim=None, ref_line=None):
    """Single bar series (e.g. kappa, dTV) per group with error bars."""
    x = np.arange(len(groups))
    w = 0.5
    ax.bar(x, means, w, yerr=stds, capsize=4, color=COLOR_CONSTRAINED,
           edgecolor="black", linewidth=0.5)
    if ref_line is not None:
        ax.axhline(y=ref_line, color="gray", linestyle="--", linewidth=1, label=f"Target (y={ref_line})")
    ax.set_ylabel(ylabel, fontsize=11)
    ax.set_title(title, fontsize=12)
    ax.set_xticks(x)
    ax.set_xticklabels([f"Group {g}" for g in groups])
    if ref_line is not None:
        ax.legend(loc="best", fontsize=9)
    if ylim is not None:
        ax.set_ylim(ylim)
    ax.set_axisbelow(True)
    ax.grid(axis="y", alpha=0.3)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


def main():
    ap = argparse.ArgumentParser(description="Plot aggregated metrics (6 seeds) with error bars.")
    ap.add_argument("--input-dir", default=DEFAULT_INPUT, help="Directory containing experiment_report_seed*.json")
    ap.add_argument("--output-dir", default=DEFAULT_OUTPUT, help="Directory to save figures")
    ap.add_argument("--dpi", type=int, default=300, help="Figure DPI")
    args = ap.parse_args()

    print("Loading reports...", flush=True)
    os.chdir(ROOT)
    sys.path.insert(0, ROOT)

    reports = load_reports(args.input_dir)
    if len(reports) < 2:
        print("Need at least 2 seed reports.", file=sys.stderr)
        sys.exit(1)
    print(f"Loaded {len(reports)} reports for seeds: {[s for s, _ in reports]}")

    df = extract_metrics(reports)
    agg = aggregate_by_group(df)

    groups = [g for g in GROUPS if g in agg]
    if not groups:
        print("No group data.", file=sys.stderr)
        sys.exit(1)

    try:
        plt.style.use("seaborn-v0_8-whitegrid")
    except OSError:
        plt.style.use("ggplot")
    os.makedirs(args.output_dir, exist_ok=True)

    # Chart 1: slift_weighted (Y 0~1)
    fig1, ax1 = plt.subplots(figsize=(5.5, 4))
    means_gsp = [agg[g]["slift_weighted_GSP_mean"] for g in groups]
    means_con = [agg[g]["slift_weighted_Constrained_mean"] for g in groups]
    stds_gsp = [agg[g]["slift_weighted_GSP_std"] for g in groups]
    stds_con = [agg[g]["slift_weighted_Constrained_std"] for g in groups]
    plot_grouped_bars(ax1, groups, means_gsp, means_con, stds_gsp, stds_con,
                     "slift_weighted", "Selection Lift (weighted, 6 seeds)", ylim=(0, 1))
    fig1.tight_layout()
    fig1.savefig(os.path.join(args.output_dir, "aggregated_slift_weighted.png"), dpi=args.dpi, bbox_inches="tight")
    plt.close(fig1)
    print(f"Saved aggregated_slift_weighted.png")

    # Chart 2: total_payment (Y auto)
    fig2, ax2 = plt.subplots(figsize=(5.5, 4))
    means_gsp = [agg[g]["total_payment_GSP_mean"] for g in groups]
    means_con = [agg[g]["total_payment_Constrained_mean"] for g in groups]
    stds_gsp = [agg[g]["total_payment_GSP_std"] for g in groups]
    stds_con = [agg[g]["total_payment_Constrained_std"] for g in groups]
    plot_grouped_bars(ax2, groups, means_gsp, means_con, stds_gsp, stds_con,
                     "Total payment", "Total payment (6 seeds)")
    fig2.tight_layout()
    fig2.savefig(os.path.join(args.output_dir, "aggregated_total_payment.png"), dpi=args.dpi, bbox_inches="tight")
    plt.close(fig2)
    print(f"Saved aggregated_total_payment.png")

    # Chart 3: exposure_female_share (Y 0~1, ref y=0.5)
    fig3, ax3 = plt.subplots(figsize=(5.5, 4))
    means_gsp = [agg[g]["exposure_female_share_GSP_mean"] for g in groups]
    means_con = [agg[g]["exposure_female_share_Constrained_mean"] for g in groups]
    stds_gsp = [agg[g]["exposure_female_share_GSP_std"] for g in groups]
    stds_con = [agg[g]["exposure_female_share_Constrained_std"] for g in groups]
    plot_grouped_bars(ax3, groups, means_gsp, means_con, stds_gsp, stds_con,
                     "Female exposure share", "Female exposure share (6 seeds)", ylim=(0, 1), ref_line=0.5)
    fig3.tight_layout()
    fig3.savefig(os.path.join(args.output_dir, "aggregated_exposure_female_share.png"), dpi=args.dpi, bbox_inches="tight")
    plt.close(fig3)
    print(f"Saved aggregated_exposure_female_share.png")

    # Chart 4: kappa (Constrained only = comparison value), ref y=1.0
    fig4, ax4 = plt.subplots(figsize=(5.5, 4))
    means = [agg[g]["kappa_mean"] for g in groups]
    stds = [agg[g]["kappa_std"] for g in groups]
    plot_single_bars(ax4, groups, means, stds, "κ (revenue ratio)", "κ (Constrained vs GSP, 6 seeds)", ref_line=1.0)
    fig4.tight_layout()
    fig4.savefig(os.path.join(args.output_dir, "aggregated_kappa.png"), dpi=args.dpi, bbox_inches="tight")
    plt.close(fig4)
    print(f"Saved aggregated_kappa.png")

    # Chart 5: dTV (Constrained only), Y 0~1
    fig5, ax5 = plt.subplots(figsize=(5.5, 4))
    means = [agg[g]["dTV_mean"] for g in groups]
    stds = [agg[g]["dTV_std"] for g in groups]
    plot_single_bars(ax5, groups, means, stds, "dTV", "dTV (Constrained vs GSP, 6 seeds)", ylim=(0, 1))
    fig5.tight_layout()
    fig5.savefig(os.path.join(args.output_dir, "aggregated_dTV.png"), dpi=args.dpi, bbox_inches="tight")
    plt.close(fig5)
    print(f"Saved aggregated_dTV.png")

    # Chart 6: impression_ratio (Constrained vs GSP), ref y=1.0
    fig6, ax6 = plt.subplots(figsize=(5.5, 4))
    means = [agg[g]["impression_ratio_mean"] for g in groups]
    stds = [agg[g]["impression_ratio_std"] for g in groups]
    plot_single_bars(ax6, groups, means, stds, "impression_ratio", "Impression ratio (Constrained vs GSP, 6 seeds)", ref_line=1.0)
    ax6.set_ylim(0.85, 1.15)
    fig6.tight_layout()
    fig6.savefig(os.path.join(args.output_dir, "aggregated_impression_ratio.png"), dpi=args.dpi, bbox_inches="tight")
    plt.close(fig6)
    print(f"Saved aggregated_impression_ratio.png")

    print("Done. All 6 figures saved to", args.output_dir)


if __name__ == "__main__":
    main()
