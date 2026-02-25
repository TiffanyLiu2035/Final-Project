#!/usr/bin/env python3
"""
Export three fairness metric tables from experiment_report_seed*.json.
Core: slift_weighted (exposure-weighted avg) for Table 1; kappa, dTV by group.
Output: three CSVs + logs/three_metrics_tables.md under logs/
"""
import os
import sys
import json
import glob

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(_root)
sys.path.insert(0, _root)

LOGS = os.path.join(_root, "logs")


def load_seed_reports():
    """Load all experiment_report_seed*.json from logs."""
    pattern = os.path.join(LOGS, "experiment_report_seed*.json")
    files = sorted(glob.glob(pattern))
    out = []
    for path in files:
        base = os.path.basename(path)
        try:
            seed_str = base.split("seed")[1].split("_")[0]
            seed_id = int(seed_str)
        except (IndexError, ValueError):
            seed_id = 0
        with open(path, "r", encoding="utf-8") as f:
            out.append((seed_id, json.load(f)))
    return out


def build_tables(reports):
    """Extract slift_weighted, kappa, dTV from by_group."""
    by_group_key = "comparison_report"
    by_group = "by_group"
    groups = ["1", "2", "3", "4"]
    mechanisms = ["GSP", "Constrained"]

    rows_slift = []
    rows_kappa = []
    rows_dtv = []

    for seed, report in reports:
        cr = report.get(by_group_key) or {}
        bg = cr.get(by_group) or {}
        for g in groups:
            grp = bg.get(g)
            if not grp:
                continue
            comp = grp.get("comparison") or {}
            row_s = {"seed": seed, "group": int(g)}
            row_k = {"seed": seed, "group": int(g)}
            row_d = {"seed": seed, "group": int(g)}
            for mech in mechanisms:
                m = grp.get(mech) or {}
                # Core: slift_weighted
                slift_w = m.get("slift_weighted")
                row_s[f"{mech}"] = round(slift_w, 4) if slift_w is not None else None
            row_k["kappa"] = round(comp.get("kappa"), 4) if comp.get("kappa") is not None else None
            row_d["dTV"] = round(comp.get("dTV"), 4) if comp.get("dTV") is not None else None
            rows_slift.append(row_s)
            rows_kappa.append(row_k)
            rows_dtv.append(row_d)

    return rows_slift, rows_kappa, rows_dtv


def to_csv(rows, headers, path):
    import csv
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=headers, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def pivot_by_seed_same_table(rows_slift, rows_kappa, rows_dtv):
    """
    One table per metric, seeds as columns. Table 1: rows=Group 1..4, cols=group, seed42_GSP, seed42_Constrained, ...
    Table 2: kappa per seed; Table 3: dTV per seed. Average when multiple reports per (group, seed).
    """
    from collections import defaultdict
    seeds = sorted(set(r["seed"] for r in rows_slift))
    groups = sorted(set(r["group"] for r in rows_slift))

    # Slift: (group, seed) -> list of {GSP, Constrained}, then average
    by_gs = defaultdict(lambda: {"GSP": [], "Constrained": []})
    for r in rows_slift:
        k = (r["group"], r["seed"])
        if r.get("GSP") is not None:
            by_gs[k]["GSP"].append(r["GSP"])
        if r.get("Constrained") is not None:
            by_gs[k]["Constrained"].append(r["Constrained"])
    table_s = []
    for g in groups:
        row = {"group": g}
        for s in seeds:
            v = by_gs.get((g, s), {"GSP": [], "Constrained": []})
            gsp_vals = v["GSP"]
            con_vals = v["Constrained"]
            row[f"seed{s}_GSP"] = round(sum(gsp_vals) / len(gsp_vals), 4) if gsp_vals else None
            row[f"seed{s}_Constrained"] = round(sum(con_vals) / len(con_vals), 4) if con_vals else None
        table_s.append(row)

    # Kappa / dTV: (group, seed) -> list of values, then average
    by_gk = defaultdict(list)
    by_gd = defaultdict(list)
    for r in rows_kappa:
        if r.get("kappa") is not None:
            by_gk[(r["group"], r["seed"])].append(r["kappa"])
    for r in rows_dtv:
        if r.get("dTV") is not None:
            by_gd[(r["group"], r["seed"])].append(r["dTV"])
    table_k = []
    table_d = []
    for g in groups:
        row_k = {"group": g}
        row_d = {"group": g}
        for s in seeds:
            k_vals = by_gk.get((g, s), [])
            d_vals = by_gd.get((g, s), [])
            row_k[f"seed{s}_κ"] = round(sum(k_vals) / len(k_vals), 4) if k_vals else None
            row_d[f"seed{s}_dTV"] = round(sum(d_vals) / len(d_vals), 4) if d_vals else None
        table_k.append(row_k)
        table_d.append(row_d)

    headers_s = ["group"] + [f"seed{s}_{m}" for s in seeds for m in ["GSP", "Constrained"]]
    headers_k = ["group"] + [f"seed{s}_κ" for s in seeds]
    headers_d = ["group"] + [f"seed{s}_dTV" for s in seeds]
    return table_s, table_k, table_d, headers_s, headers_k, headers_d, seeds


def main():
    reports = load_seed_reports()
    if not reports:
        print("No logs/experiment_report_seed*.json found")
        sys.exit(1)
    seeds = sorted(set(r[0] for r in reports))
    print(f"Loaded {len(reports)} seed reports: {seeds}")

    rows_slift, rows_kappa, rows_dtv = build_tables(reports)
    os.makedirs(LOGS, exist_ok=True)

    table_s, table_k, table_d, headers_s, headers_k, headers_d, seeds = pivot_by_seed_same_table(
        rows_slift, rows_kappa, rows_dtv
    )
    to_csv(table_s, headers_s, os.path.join(LOGS, "metrics_table1_slift_summary.csv"))
    to_csv(table_k, headers_k, os.path.join(LOGS, "metrics_table2_kappa_summary.csv"))
    to_csv(table_d, headers_d, os.path.join(LOGS, "metrics_table3_dTV_summary.csv"))

    md_path = os.path.join(LOGS, "three_metrics_tables.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# Three fairness metric tables\n\n")
        f.write("Source: experiment_report_seed*.json. One table per metric, seeds as columns. Core: slift_weighted.\n\n")
        f.write("## 1. Selection Lift — slift_weighted (core)\n\n")
        f.write("Rows = Group 1..4; columns = GSP / Constrained per seed.\n\n")
        f.write("| Group | " + " | ".join(f"seed{s}_GSP | seed{s}_Constrained" for s in seeds) + " |\n")
        f.write("|-------|" + "|".join(["-----|-------------"] * len(seeds)) + "|\n")
        for row in table_s:
            cells = [str(row["group"])]
            for s in seeds:
                a = row.get(f"seed{s}_GSP")
                b = row.get(f"seed{s}_Constrained")
                cells.append(str(round(a, 4)) if a is not None else "—")
                cells.append(str(round(b, 4)) if b is not None else "—")
            f.write("| " + " | ".join(cells) + " |\n")
        f.write("\n## 2. Revenue Ratio κ (kappa)\n\n")
        f.write("Rows = Group 1..4; columns = κ per seed.\n\n")
        f.write("| Group | " + " | ".join(f"seed{s}_κ" for s in seeds) + " |\n")
        f.write("|-------|" + "|".join(["---"] * len(seeds)) + "|\n")
        for row in table_k:
            cells = [str(row["group"])]
            for s in seeds:
                v = row.get(f"seed{s}_κ")
                cells.append(str(round(v, 4)) if v is not None else "—")
            f.write("| " + " | ".join(cells) + " |\n")
        f.write("\n## 3. Advertiser Displacement dTV\n\n")
        f.write("Rows = Group 1..4; columns = dTV per seed.\n\n")
        f.write("| Group | " + " | ".join(f"seed{s}_dTV" for s in seeds) + " |\n")
        f.write("|-------|" + "|".join(["-----"] * len(seeds)) + "|\n")
        for row in table_d:
            cells = [str(row["group"])]
            for s in seeds:
                v = row.get(f"seed{s}_dTV")
                cells.append(str(round(v, 4)) if v is not None else "—")
            f.write("| " + " | ".join(cells) + " |\n")
    print(f"Written: {md_path}")
    print("CSV: metrics_table1_slift_summary.csv, metrics_table2_kappa_summary.csv, metrics_table3_dTV_summary.csv (rows=Group, cols=seeds)")


if __name__ == "__main__":
    main()
