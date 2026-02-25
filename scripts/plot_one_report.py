#!/usr/bin/env python3
"""Plot slift_weighted vs group (GSP and Constrained) for a single experiment_report."""
import json
import sys
from pathlib import Path

def main():
    project_root = Path(__file__).resolve().parent.parent
    if len(sys.argv) < 2:
        report_path = project_root / "logs" / "experiment_report_seed2_20260219_144404.json"
    else:
        report_path = Path(sys.argv[1])
    if not report_path.is_file():
        print(f"File not found: {report_path}", file=sys.stderr)
        return 1
    with open(report_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    by_group = (data.get("comparison_report") or {}).get("by_group") or {}
    seed = data.get("random_seed", "?")
    groups_ordered = sorted((int(k) if str(k).isdigit() else k) for k in by_group.keys())
    gsp_ys = []
    con_ys = []
    for g in groups_ordered:
        gdata = by_group.get(str(g), {})
        gsp_ys.append(float((gdata.get("GSP") or {}).get("slift_weighted", 0)))
        con_ys.append(float((gdata.get("Constrained") or {}).get("slift_weighted", 0)))
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as e:
        print("matplotlib not available:", e, file=sys.stderr)
        return 1
    x = list(range(len(groups_ordered)))
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.plot(x, gsp_ys, marker="o", linestyle="-", color="C0", label="GSP", linewidth=2, markersize=6)
    ax.plot(x, con_ys, marker="o", linestyle="--", color="C1", label="Constrained", linewidth=2, markersize=6)
    ax.set_xticks(x)
    ax.set_xticklabels([f"Group{g}" for g in groups_ordered])
    ax.set_ylabel("slift_weighted")
    ax.set_xlabel("Group")
    ax.set_title(f"Seed {seed}: slift_weighted by group")
    ax.legend(loc="best")
    ax.grid(True, alpha=0.3)
    ax.set_ylim(0, 1.0)
    fig.tight_layout()
    out_dir = project_root / "logs" / "figures_last6"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"05_slift_by_group_seed{seed}.png"
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"Saved: {out_path}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
