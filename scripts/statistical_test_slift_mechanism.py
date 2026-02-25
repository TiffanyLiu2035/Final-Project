#!/usr/bin/env python3
"""
Mechanism efficacy test: for each group, paired data from 6 seeds;
test whether Constrained vs GSP slift_weighted differs significantly (Paired T-Test).
Goal: test if Constrained significantly changes slift_weighted; expect Group 2 Constrained > GSP.
"""
import os
import sys
import argparse
import numpy as np
import pandas as pd
from scipy import stats

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SCRIPT_DIR)
DEFAULT_CSV = os.path.join(ROOT, "logs", "formal_experiment", "formal_experiment_all_metrics.csv")
DEFAULT_OUT = os.path.join(ROOT, "logs", "formal_experiment", "statistical_test_slift_mechanism.md")
DEFAULT_TEX = os.path.join(ROOT, "logs", "formal_experiment", "statistical_test_slift_mechanism.tex")


def main():
    ap = argparse.ArgumentParser(description="Paired t-test: GSP vs Constrained slift_weighted per group (6 seeds).")
    ap.add_argument("--input", default=DEFAULT_CSV, help="All-metrics CSV (6 seeds × 4 groups)")
    ap.add_argument("--output", default=DEFAULT_OUT, help="Output Markdown report path")
    ap.add_argument("--tex", default=None, help="Output LaTeX table path (default: same dir as --output, .tex)")
    ap.add_argument("--alpha", type=float, default=0.05, help="Significance level")
    args = ap.parse_args()
    os.chdir(ROOT)

    df = pd.read_csv(args.input)
    groups = sorted(df["group"].unique())
    alpha = args.alpha

    rows = []
    for g in groups:
        sub = df[df["group"] == g].sort_values("seed")
        gsp = sub["slift_weighted_GSP"].values
        con = sub["slift_weighted_Constrained"].values
        n = len(gsp)
        if n < 2:
            rows.append({
                "group": g,
                "n": n,
                "mean_GSP": np.nan,
                "mean_Constrained": np.nan,
                "mean_diff": np.nan,
                "std_diff": np.nan,
                "t": np.nan,
                "p_two_tailed": np.nan,
                "p_one_tailed": np.nan,
                "significant": "",
                "conclusion": "Insufficient data",
            })
            continue
        diff = con - gsp
        mean_gsp = gsp.mean()
        mean_con = con.mean()
        mean_diff = diff.mean()
        std_diff = diff.std(ddof=1)
        t_stat, p_two = stats.ttest_rel(con, gsp)
        # One-tailed: H1 Constrained > GSP -> p_one = p_two/2 if t>0 else 1-p_two/2
        p_one = p_two / 2 if t_stat >= 0 else 1 - p_two / 2
        sig = "Yes" if p_one < alpha else "No"
        conclusion = (
            "Constrained significantly higher than GSP (p < 0.05)."
            if p_one < alpha and mean_diff > 0
            else "No significant difference or Constrained not higher."
        )
        rows.append({
            "group": g,
            "n": n,
            "mean_GSP": mean_gsp,
            "mean_Constrained": mean_con,
            "mean_diff": mean_diff,
            "std_diff": std_diff,
            "t": t_stat,
            "p_two_tailed": p_two,
            "p_one_tailed": p_one,
            "significant": sig,
            "conclusion": conclusion,
        })

    # Console table
    print("=" * 80)
    print("Mechanism Efficacy: Paired T-Test (GSP vs Constrained, slift_weighted)")
    print("Per group, n = 6 seeds. H1 (one-tailed): Constrained > GSP. alpha =", alpha)
    print("=" * 80)
    for r in rows:
        print(f"  Group {r['group']}:  mean_GSP = {r['mean_GSP']:.4f},  mean_Constrained = {r['mean_Constrained']:.4f},  "
              f"diff = {r['mean_diff']:.4f},  t = {r['t']:.4f},  p (one-tailed) = {r['p_one_tailed']:.4f}  ->  {r['significant']}  |  {r['conclusion']}")
    print("=" * 80)

    # Markdown report (only selected columns)
    out_dir = os.path.dirname(args.output) or "."
    os.makedirs(out_dir, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write("# Mechanism Efficacy: Paired T-Test (slift_weighted)\n\n")
        f.write("| Group | Mean (GSP) | Mean (Constrained) | Mean Diff ($\\Delta$) | t-statistic | p-value (one-tailed) |\n")
        f.write("|-------|------------|---------------------|----------------------|-------------|------------------------|\n")
        for r in rows:
            f.write(f"| {r['group']} | {r['mean_GSP']:.4f} | {r['mean_Constrained']:.4f} | {r['mean_diff']:.4f} | {r['t']:.4f} | {r['p_one_tailed']:.4f} |\n")
    print(f"Report saved: {args.output}")

    # LaTeX three-line table
    tex_path = args.tex
    if tex_path is None:
        tex_path = os.path.join(out_dir, "statistical_test_slift_mechanism.tex")
    with open(tex_path, "w", encoding="utf-8") as f:
        f.write("% Preamble: \\usepackage{booktabs}\n")
        f.write("\\begin{table}[htbp]\n")
        f.write("\\centering\n")
        f.write("\\caption{Mechanism efficacy: paired $t$-test (GSP vs Constrained, slift\\_weighted). One-tailed $H_1$: Constrained $>$ GSP; $n = 6$ seeds per group.}\n")
        f.write("\\label{tab:paired-ttest-slift}\n")
        f.write("\\begin{tabular}{cccccc}\n")
        f.write("\\toprule\n")
        f.write("Group & Mean (GSP) & Mean (Constrained) & Mean Diff ($\\Delta$) & $t$-statistic & $p$-value (one-tailed) \\\\\n")
        f.write("\\midrule\n")
        for r in rows:
            f.write(f"{int(r['group'])} & {r['mean_GSP']:.4f} & {r['mean_Constrained']:.4f} & {r['mean_diff']:.4f} & {r['t']:.4f} & {r['p_one_tailed']:.4f} \\\\\n")
        f.write("\\bottomrule\n")
        f.write("\\end{tabular}\n")
        f.write("\\end{table}\n")
    print(f"LaTeX table saved: {tex_path}")


if __name__ == "__main__":
    main()
