#!/usr/bin/env python3
"""
Plot two combined figures (dual y-axis) from summary table means:
1. Total Payment (bar) + slift_weighted (line)
2. slift_weighted (bar) + dTV (line)
"""
import os
import sys
import argparse
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SCRIPT_DIR)
DEFAULT_CSV = os.path.join(ROOT, "logs", "formal_experiment", "formal_experiment_group_summary.csv")
DEFAULT_OUT = os.path.join(ROOT, "logs", "formal_experiment")
COLOR_GSP = "#e41a1c"
COLOR_CONSTRAINED = "#377eb8"
# Line colors (distinct from bars)
COLOR_LINE_GSP = "#2ca02c"      # green
COLOR_LINE_CONSTRAINED = "#ff7f0e"  # orange


def load_summary(csv_path: str):
    """Read summary table, return GSP/Constrained means and std per group."""
    df = pd.read_csv(csv_path)
    groups = sorted(df["Group"].unique())
    out = {}
    for g in groups:
        block = df[df["Group"] == g]
        gsp = block[block["Method"] == "GSP"].iloc[0]
        con = block[block["Method"] == "Constrained"].iloc[0]
        out[g] = {
            "slift_gsp_mean": gsp["slift_weighted_mean"],
            "slift_gsp_std": gsp["slift_weighted_std"],
            "slift_con_mean": con["slift_weighted_mean"],
            "slift_con_std": con["slift_weighted_std"],
            "pay_gsp_mean": gsp["total_payment_mean"],
            "pay_gsp_std": gsp["total_payment_std"],
            "pay_con_mean": con["total_payment_mean"],
            "pay_con_std": con["total_payment_std"],
            "dtv_mean": con["dTV_mean"] if pd.notna(con.get("dTV_mean")) else np.nan,
            "dtv_std": con["dTV_std"] if pd.notna(con.get("dTV_std")) else 0.0,
            "impression_ratio_mean": con["impression_ratio_mean"] if pd.notna(con.get("impression_ratio_mean")) else np.nan,
            "impression_ratio_std": con["impression_ratio_std"] if pd.notna(con.get("impression_ratio_std")) else 0.0,
        }
    return groups, out


def main():
    ap = argparse.ArgumentParser(description="Plot combined: (1) Total Payment + slift_weighted, (2) slift_weighted + dTV.")
    ap.add_argument("--input", default=DEFAULT_CSV, help="Group summary CSV")
    ap.add_argument("--output-dir", default=DEFAULT_OUT, help="Output directory")
    ap.add_argument("--dpi", type=int, default=300)
    args = ap.parse_args()
    os.chdir(ROOT)

    groups, data = load_summary(args.input)
    x = np.arange(len(groups))
    width = 0.35

    # ----- Fig 1a: GSP — Total Payment (bar) + slift_weighted (line) -----
    pay_gsp = [data[g]["pay_gsp_mean"] for g in groups]
    pay_con = [data[g]["pay_con_mean"] for g in groups]
    pay_gsp_std = [data[g]["pay_gsp_std"] for g in groups]
    pay_con_std = [data[g]["pay_con_std"] for g in groups]
    slift_gsp = [data[g]["slift_gsp_mean"] for g in groups]
    slift_con = [data[g]["slift_con_mean"] for g in groups]
    slift_gsp_std = [data[g]["slift_gsp_std"] for g in groups]
    slift_con_std = [data[g]["slift_con_std"] for g in groups]

    fig1a, ax1 = plt.subplots(figsize=(6.5, 4.5))
    ax1.bar(x, pay_gsp, width * 1.2, yerr=pay_gsp_std, capsize=3,
            label="Total payment", color=COLOR_GSP, edgecolor="black", linewidth=0.5)
    ax1.set_ylabel("Total payment (mean ± std)", fontsize=12)
    ax1.set_xlabel("Group", fontsize=12)
    ax1.set_xticks(x)
    ax1.set_xticklabels([f"Group {g}" for g in groups])
    ax1.legend(loc="upper left", fontsize=10)
    ax1.set_ylim(0, None)
    ax1.grid(axis="y", alpha=0.3)
    ax2 = ax1.twinx()
    ax2.plot(x, slift_gsp, "o-", color=COLOR_LINE_GSP, linewidth=2, markersize=8, label="slift_weighted")
    ax2.errorbar(x, slift_gsp, yerr=slift_gsp_std, fmt="none", color=COLOR_LINE_GSP, capsize=3)
    ax2.set_ylabel("slift_weighted (mean ± std)", fontsize=12)
    ax2.set_ylim(0, 1)
    ax2.legend(loc="upper right", fontsize=10)
    fig1a.suptitle("GSP", fontsize=13)
    fig1a.tight_layout()
    p1a = os.path.join(args.output_dir, "combined_total_payment_slift_GSP.png")
    fig1a.savefig(p1a, dpi=args.dpi, bbox_inches="tight")
    plt.close(fig1a)
    print(f"Saved: {p1a}")

    # ----- Fig 1b: Constrained — Total Payment (bar) + slift_weighted (line) -----
    fig1b, ax1 = plt.subplots(figsize=(6.5, 4.5))
    ax1.bar(x, pay_con, width * 1.2, yerr=pay_con_std, capsize=3,
            label="Total payment", color=COLOR_CONSTRAINED, edgecolor="black", linewidth=0.5)
    ax1.set_ylabel("Total payment (mean ± std)", fontsize=12)
    ax1.set_xlabel("Group", fontsize=12)
    ax1.set_xticks(x)
    ax1.set_xticklabels([f"Group {g}" for g in groups])
    ax1.legend(loc="upper left", fontsize=10)
    ax1.set_ylim(0, None)
    ax1.grid(axis="y", alpha=0.3)
    ax2 = ax1.twinx()
    ax2.plot(x, slift_con, "s--", color=COLOR_LINE_CONSTRAINED, linewidth=2, markersize=8, label="slift_weighted")
    ax2.errorbar(x, slift_con, yerr=slift_con_std, fmt="none", color=COLOR_LINE_CONSTRAINED, capsize=3)
    ax2.set_ylabel("slift_weighted (mean ± std)", fontsize=12)
    ax2.set_ylim(0, 1)
    ax2.legend(loc="upper right", fontsize=10)
    fig1b.suptitle("Constrained", fontsize=13)
    fig1b.tight_layout()
    p1b = os.path.join(args.output_dir, "combined_total_payment_slift_Constrained.png")
    fig1b.savefig(p1b, dpi=args.dpi, bbox_inches="tight")
    plt.close(fig1b)
    print(f"Saved: {p1b}")

    # ----- Fig 2a: GSP — dTV (bar) + slift_weighted (line) -----
    dtv_mean = [data[g]["dtv_mean"] for g in groups]
    dtv_std = [data[g]["dtv_std"] for g in groups]
    color_dtv = "#ff7f0e"  # orange

    fig2a, ax1 = plt.subplots(figsize=(6.5, 4.5))
    ax1.bar(x, dtv_mean, width * 1.2, yerr=dtv_std, capsize=3,
            label="dTV (Constrained vs GSP)", color=color_dtv, edgecolor="black", linewidth=0.5)
    ax1.set_ylabel("dTV (mean ± std)", fontsize=12)
    ax1.set_xlabel("Group", fontsize=12)
    ax1.set_xticks(x)
    ax1.set_xticklabels([f"Group {g}" for g in groups])
    ax1.legend(loc="upper right", fontsize=10)
    dtv_vals = np.array(dtv_mean)
    dtv_errs = np.array(dtv_std)
    d_min = max(0, float(np.nanmin(dtv_vals - dtv_errs)) - 0.05)
    d_max = min(1, float(np.nanmax(dtv_vals + dtv_errs)) + 0.12)
    if d_max - d_min < 0.2:
        d_max = d_min + 0.35
    ax1.set_ylim(d_min, d_max)
    ax1.grid(axis="y", alpha=0.3)
    ax2 = ax1.twinx()
    ax2.plot(x, slift_gsp, "o-", color=COLOR_LINE_GSP, linewidth=2, markersize=8, label="slift_weighted")
    ax2.errorbar(x, slift_gsp, yerr=slift_gsp_std, fmt="none", color=COLOR_LINE_GSP, capsize=3)
    ax2.set_ylabel("slift_weighted (mean ± std)", fontsize=12)
    ax2.set_ylim(0, 1)
    ax2.legend(loc="center right", fontsize=10)
    fig2a.suptitle("GSP", fontsize=13)
    fig2a.tight_layout()
    p2a = os.path.join(args.output_dir, "combined_slift_dTV_GSP.png")
    fig2a.savefig(p2a, dpi=args.dpi, bbox_inches="tight")
    plt.close(fig2a)
    print(f"Saved: {p2a}")

    # ----- Fig 2b: Constrained — dTV (bar) + slift_weighted (line) -----
    fig2b, ax1 = plt.subplots(figsize=(6.5, 4.5))
    ax1.bar(x, dtv_mean, width * 1.2, yerr=dtv_std, capsize=3,
            label="dTV (Constrained vs GSP)", color=color_dtv, edgecolor="black", linewidth=0.5)
    ax1.set_ylabel("dTV (mean ± std)", fontsize=12)
    ax1.set_xlabel("Group", fontsize=12)
    ax1.set_xticks(x)
    ax1.set_xticklabels([f"Group {g}" for g in groups])
    ax1.legend(loc="upper right", fontsize=10)
    ax1.set_ylim(d_min, d_max)
    ax1.grid(axis="y", alpha=0.3)
    ax2 = ax1.twinx()
    color_slift_con_dtv = "#2ca02c"  # green (vs orange dTV bar)
    ax2.plot(x, slift_con, "s--", color=color_slift_con_dtv, linewidth=2, markersize=8, label="slift_weighted")
    ax2.errorbar(x, slift_con, yerr=slift_con_std, fmt="none", color=color_slift_con_dtv, capsize=3)
    ax2.set_ylabel("slift_weighted (mean ± std)", fontsize=12)
    ax2.set_ylim(0, 1)
    ax2.legend(loc="center right", fontsize=10)
    fig2b.suptitle("Constrained", fontsize=13)
    fig2b.tight_layout()
    p2b = os.path.join(args.output_dir, "combined_slift_dTV_Constrained.png")
    fig2b.savefig(p2b, dpi=args.dpi, bbox_inches="tight")
    plt.close(fig2b)
    print(f"Saved: {p2b}")

    # ----- Fig 3: slift_weighted (bar) + impression_ratio (line) -----
    imp_mean = [data[g]["impression_ratio_mean"] for g in groups]
    imp_std = [data[g]["impression_ratio_std"] for g in groups]
    fig3, ax1 = plt.subplots(figsize=(6.5, 4.5))
    ax1.bar(x - width / 2, slift_gsp, width, yerr=slift_gsp_std, capsize=3,
            label="GSP (slift)", color=COLOR_GSP, edgecolor="black", linewidth=0.5)
    ax1.bar(x + width / 2, slift_con, width, yerr=slift_con_std, capsize=3,
            label="Constrained (slift)", color=COLOR_CONSTRAINED, edgecolor="black", linewidth=0.5)
    ax1.set_ylabel("slift_weighted (mean ± std)", fontsize=12)
    ax1.set_xlabel("Group", fontsize=12)
    ax1.set_xticks(x)
    ax1.set_xticklabels([f"Group {g}" for g in groups])
    ax1.legend(loc="upper right", fontsize=10)
    ax1.set_ylim(0, 1)
    ax1.grid(axis="y", alpha=0.3)
    ax2 = ax1.twinx()
    color_imp = "#2ca02c"  # green
    ax2.plot(x, imp_mean, "o-", color=color_imp, linewidth=2, markersize=10, label="impression_ratio (Constrained vs GSP)")
    ax2.errorbar(x, imp_mean, yerr=imp_std, fmt="none", color=color_imp, capsize=4)
    ax2.axhline(y=1.0, color="gray", linestyle="--", alpha=0.7)
    ax2.set_ylabel("impression_ratio (mean ± std)", fontsize=12)
    imp_vals = np.array(imp_mean)
    imp_errs = np.array(imp_std)
    i_min = max(0.85, float(np.nanmin(imp_vals - imp_errs)) - 0.02)
    i_max = min(1.15, float(np.nanmax(imp_vals + imp_errs)) + 0.03)
    ax2.set_ylim(i_min, i_max)
    ax2.legend(loc="center right", fontsize=10)
    fig3.tight_layout()
    p3 = os.path.join(args.output_dir, "combined_slift_impression_ratio.png")
    fig3.savefig(p3, dpi=args.dpi, bbox_inches="tight")
    plt.close(fig3)
    print(f"Saved: {p3}")


if __name__ == "__main__":
    main()
