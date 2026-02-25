#!/usr/bin/env python3
"""
Summarize 6 seeds by group: mean and std; two rows per group (GSP, Constrained); 3 decimal places.
"""
import os
import sys
import argparse

import pandas as pd

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SCRIPT_DIR)
DEFAULT_CSV = os.path.join(ROOT, "logs", "formal_experiment", "formal_experiment_all_metrics.csv")
DEFAULT_OUT = os.path.join(ROOT, "logs", "formal_experiment", "formal_experiment_group_summary.csv")


def main():
    ap = argparse.ArgumentParser(description="Export group summary: mean ± std (3 decimals), 2 rows per group (GSP, Constrained).")
    ap.add_argument("--input", default=DEFAULT_CSV, help="Input CSV from export_formal_experiment_table.py")
    ap.add_argument("--output", default=DEFAULT_OUT, help="Output CSV path")
    args = ap.parse_args()

    os.chdir(ROOT)
    df = pd.read_csv(args.input)

    metrics_per_mech = [
        ("slift_weighted", "slift_weighted"),
        ("total_payment", "total_payment"),
        ("exposure_female_share", "exposure_female_share"),
    ]
    comparison_metrics = ["kappa", "dTV", "impression_ratio"]

    rows = []
    for group in sorted(df["group"].unique()):
        sub = df[df["group"] == group]
        # Comparison metrics (one per group, same for both rows)
        comp_means = {m: round(sub[m].mean(), 3) for m in comparison_metrics if m in sub.columns}
        comp_stds = {m: round(sub[m].std(), 3) if sub[m].notna().sum() > 1 else 0.0 for m in comparison_metrics if m in sub.columns}

        for method in ["GSP", "Constrained"]:
            row = {"Group": group, "Method": method}
            for label, prefix in metrics_per_mech:
                col = f"{prefix}_{method}"
                if col not in sub.columns:
                    continue
                mu = round(sub[col].mean(), 3)
                sigma = round(sub[col].std(), 3) if sub[col].notna().sum() > 1 else 0.0
                row[f"{label}_mean"] = mu
                row[f"{label}_std"] = sigma
            # kappa, dTV, impression_ratio: fill only on Constrained row; leave GSP row empty
            for m in comparison_metrics:
                if m in comp_means and method == "Constrained":
                    row[f"{m}_mean"] = comp_means[m]
                    row[f"{m}_std"] = comp_stds[m]
                else:
                    row[f"{m}_mean"] = None
                    row[f"{m}_std"] = None
            rows.append(row)

    out_df = pd.DataFrame(rows)
    out_df.to_csv(args.output, index=False, float_format="%.3f")
    print(f"Saved to {args.output}")

    # Also write Markdown table to same dir
    md_path = args.output.replace(".csv", ".md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("| Group | Method | slift_weighted | total_payment | exposure_female_share | kappa | dTV | impression_ratio |\n")
        f.write("|-------|--------|----------------|---------------|------------------------|-------|-----|------------------|\n")
        for _, r in out_df.iterrows():
            slift = f"{r['slift_weighted_mean']:.3f}±{r['slift_weighted_std']:.3f}"
            pay = f"{r['total_payment_mean']:.3f}±{r['total_payment_std']:.3f}"
            exp = f"{r['exposure_female_share_mean']:.3f}±{r['exposure_female_share_std']:.3f}"
            kappa = f"{r['kappa_mean']:.3f}±{r['kappa_std']:.3f}" if pd.notna(r.get("kappa_mean")) else "—"
            dtv = f"{r['dTV_mean']:.3f}±{r['dTV_std']:.3f}" if pd.notna(r.get("dTV_mean")) else "—"
            imp = f"{r['impression_ratio_mean']:.3f}±{r['impression_ratio_std']:.3f}" if pd.notna(r.get("impression_ratio_mean")) else "—"
            f.write(f"| {int(r['Group'])} | {r['Method']} | {slift} | {pay} | {exp} | {kappa} | {dtv} | {imp} |\n")
    print(f"Saved to {md_path}")

    # LaTeX three-line table; group number with multirow
    tex_path = args.output.replace(".csv", ".tex")
    with open(tex_path, "w", encoding="utf-8") as f:
        f.write("% Preamble: \\usepackage{booktabs, multirow}\n")
        f.write("\\begin{table}[htbp]\n")
        f.write("\\centering\n")
        f.write("\\caption{Formal experiment: mean $\\pm$ std over 6 seeds, by group and mechanism.}\n")
        f.write("\\label{tab:formal-group-summary}\n")
        f.write("\\begin{tabular}{clccccc}\n")
        f.write("\\toprule\n")
        f.write("Group & Method & slift (w) & $\\kappa$ & dTV & total pay & impr ratio \\\\\n")
        f.write("\\midrule\n")
        for group in sorted(out_df["Group"].unique()):
            block = out_df[out_df["Group"] == group]
            for i, (_, r) in enumerate(block.iterrows()):
                slift = f"{r['slift_weighted_mean']:.3f} $\\pm$ {r['slift_weighted_std']:.3f}"
                pay = f"{r['total_payment_mean']:.3f} $\\pm$ {r['total_payment_std']:.3f}"
                kappa = f"{r['kappa_mean']:.3f} $\\pm$ {r['kappa_std']:.3f}" if pd.notna(r.get("kappa_mean")) else "---"
                dtv = f"{r['dTV_mean']:.3f} $\\pm$ {r['dTV_std']:.3f}" if pd.notna(r.get("dTV_mean")) else "---"
                imp = f"{r['impression_ratio_mean']:.3f} $\\pm$ {r['impression_ratio_std']:.3f}" if pd.notna(r.get("impression_ratio_mean")) else "---"
                if i == 0:
                    f.write(f"\\multirow{{2}}{{*}}{{{int(r['Group'])}}} & {r['Method']} & {slift} & {kappa} & {dtv} & {pay} & {imp} \\\\\n")
                else:
                    f.write(f" & {r['Method']} & {slift} & {kappa} & {dtv} & {pay} & {imp} \\\\\n")
        f.write("\\bottomrule\n")
        f.write("\\end{tabular}\n")
        f.write("\\end{table}\n")
    print(f"Saved to {tex_path}")


if __name__ == "__main__":
    main()
