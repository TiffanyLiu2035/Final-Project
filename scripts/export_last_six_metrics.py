#!/usr/bin/env python3
"""
Summarize key metrics from the last 6 experiments into one file (e.g. for Gemini).
Reads only experiment_report_seed*_*.json from logs. Output: logs/summary_last6_metrics.md
"""
from __future__ import annotations

import json
import re
from pathlib import Path


def main() -> None:
    project_root = Path(__file__).resolve().parent.parent
    logs_dir = project_root / "logs"
    pattern = re.compile(r"experiment_report_seed(\d+)_(\d{8}_\d{6})\.json")
    reports = []
    for p in logs_dir.glob("experiment_report_seed*_*.json"):
        m = pattern.match(p.name)
        if m:
            reports.append((p, int(m.group(1)), m.group(2)))
    reports.sort(key=lambda x: x[2], reverse=True)
    selected = reports[:6]
    if not selected:
        print("No experiment_report_seed*_*.json found")
        return

    # Parse each report: by_group GSP/Constrained + comparison (kappa, dTV, impression_ratio)
    rows_metric = []   # seed, group, mechanism, slift_weighted, slift, total_payment, exposure_female_share
    rows_compare = []  # seed, group, kappa, dTV, impression_ratio
    for path, seed, _ in selected:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        by_group = (data.get("comparison_report") or {}).get("by_group") or {}
        for gkey, gdata in by_group.items():
            if not isinstance(gdata, dict):
                continue
            g = int(gkey) if str(gkey).isdigit() else gkey
            comp = gdata.get("comparison") or {}
            for mech in ("GSP", "Constrained"):
                m = gdata.get(mech)
                if not m:
                    continue
                share = (m.get("exposure_share_by_gender") or {})
                rows_metric.append({
                    "seed": seed,
                    "group": g,
                    "mechanism": mech,
                    "slift_weighted": round(float(m.get("slift_weighted", 0)), 6),
                    "slift": round(float(m.get("slift", 0)), 6),
                    "total_payment": round(float(m.get("total_payment", 0)), 2),
                    "exposure_female_share": round(float(share.get("female", 0)), 4),
                    "exposure_male_share": round(float(share.get("male", 0)), 4),
                })
            if comp:
                rows_compare.append({
                    "seed": seed,
                    "group": g,
                    "kappa": round(float(comp.get("kappa", 0)), 4),
                    "dTV": round(float(comp.get("dTV", 0)), 4),
                    "impression_ratio": round(float(comp.get("impression_ratio", 0)), 4),
                })

    out_path = logs_dir / "summary_last6_metrics.md"
    lines = [
        "# Last 6 experiments — key metrics summary",
        "",
        "## Scope",
        "Latest 6 runs (newest first):",
        "",
    ]
    for p, seed, ts in selected:
        lines.append(f"- seed **{seed}** — `{p.name}`")
    lines.extend([
        "",
        "## Metric definitions (brief)",
        "- **slift_weighted**: Core fairness metric, exposure-weighted Selection Lift; closer to 1 = fairer.",
        "- **slift**: System worst-case slift (min over advertisers), [0,1].",
        "- **total_payment**: Total platform payment under that mechanism.",
        "- **exposure_female_share**: Female exposure share.",
        "- **kappa**: Revenue Ratio = rev_Constrained / rev_GSP; >1 means fair mechanism yields more.",
        "- **dTV**: Advertiser displacement (TV distance), [0,1].",
        "- **impression_ratio**: valid_rounds_Constrained / valid_rounds_GSP; <1 = Leveling Down.",
        "",
        "---",
        "",
        "## Table 1: (seed, group, mechanism) core metrics",
        "",
        "| seed | group | mechanism | slift_weighted | slift | total_payment | exposure_female_share | exposure_male_share |",
        "|------|-------|-----------|----------------|-------|---------------|------------------------|---------------------|",
    ])
    for r in rows_metric:
        lines.append(
            f"| {r['seed']} | {r['group']} | {r['mechanism']} | {r['slift_weighted']} | {r['slift']} | {r['total_payment']} | {r['exposure_female_share']} | {r['exposure_male_share']} |"
        )
    lines.extend([
        "",
        "## Table 2: (seed, group) GSP vs Constrained",
        "",
        "| seed | group | kappa | dTV | impression_ratio |",
        "|------|-------|-------|-----|------------------|",
    ])
    for r in rows_compare:
        lines.append(f"| {r['seed']} | {r['group']} | {r['kappa']} | {r['dTV']} | {r['impression_ratio']} |")
    lines.append("")
    lines.append("---")
    lines.append("Groups: 1=DataDriven only, 2=AdaptiveProfitAgent, 3=FairnessAwareAgent, 4=mixed 3+3+3.")
    lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Written: {out_path}")


if __name__ == "__main__":
    main()
