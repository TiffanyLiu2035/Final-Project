#!/usr/bin/env python3
"""Plot all main metrics from a single experiment_report: slift_weighted, kappa, dTV, impression_ratio, total_payment, exposure_female_share."""
import json
import sys
from pathlib import Path

def load_report(report_path):
    with open(report_path, "r", encoding="utf-8") as f:
        return json.load(f)

def get_by_group(data):
    return (data.get("comparison_report") or {}).get("by_group") or {}

def plot_one_report(report_path: Path, out_dir: Path) -> int:
    if not report_path.is_file():
        print(f"File not found: {report_path}", file=sys.stderr)
        return 1
    data = load_report(report_path)
    by_group = get_by_group(data)
    seed = data.get("random_seed", "?")
    groups_ordered = sorted((int(k) if str(k).isdigit() else k) for k in by_group.keys() if str(k).isdigit())
    if not groups_ordered:
        print("No valid by_group data", file=sys.stderr)
        return 1
    x = list(range(len(groups_ordered)))
    x_labels = [f"Group{g}" for g in groups_ordered]

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as e:
        print("matplotlib not available:", e, file=sys.stderr)
        return 1

    out_dir.mkdir(parents=True, exist_ok=True)
    saved = []

    # 1) slift_weighted — two lines GSP, Constrained
    gsp_ys = []
    con_ys = []
    for g in groups_ordered:
        gdata = by_group.get(str(g), {})
        gsp_ys.append(float((gdata.get("GSP") or {}).get("slift_weighted", 0)))
        con_ys.append(float((gdata.get("Constrained") or {}).get("slift_weighted", 0)))
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.plot(x, gsp_ys, marker="o", linestyle="-", color="C0", label="GSP", linewidth=2, markersize=6)
    ax.plot(x, con_ys, marker="o", linestyle="--", color="C1", label="Constrained", linewidth=2, markersize=6)
    ax.set_xticks(x)
    ax.set_xticklabels(x_labels, fontsize=12)
    ax.set_ylabel("slift_weighted", fontsize=13)
    ax.set_xlabel("Group", fontsize=13)
    ax.set_title(f"Seed {seed}: slift_weighted by group", fontsize=13)
    ax.legend(loc="best", fontsize=12)
    ax.tick_params(axis="both", labelsize=11)
    ax.grid(True, alpha=0.3)
    ax.set_ylim(0, 1.0)
    fig.tight_layout()
    p = out_dir / f"05_slift_by_group_seed{seed}.png"
    fig.savefig(p, dpi=150)
    plt.close(fig)
    saved.append(p)

    # 2) kappa — one line (one value per group, GSP vs Constrained)
    kappa_ys = []
    for g in groups_ordered:
        comp = (by_group.get(str(g), {}) or {}).get("comparison") or {}
        kappa_ys.append(float(comp.get("kappa", 0)))
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.plot(x, kappa_ys, marker="o", linestyle="-", color="C2", linewidth=2, markersize=6)
    ax.axhline(y=1.0, color="gray", linestyle="--", alpha=0.7)
    ax.set_xticks(x)
    ax.set_xticklabels(x_labels)
    ax.set_ylabel("kappa (rev_Constrained / rev_GSP)")
    ax.set_xlabel("Group")
    ax.set_title(f"Seed {seed}: kappa by group")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    p = out_dir / f"06_kappa_by_group_seed{seed}.png"
    fig.savefig(p, dpi=150)
    plt.close(fig)
    saved.append(p)

    # 3) dTV — one line
    dTV_ys = []
    for g in groups_ordered:
        comp = (by_group.get(str(g), {}) or {}).get("comparison") or {}
        dTV_ys.append(float(comp.get("dTV", 0)))
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.plot(x, dTV_ys, marker="o", linestyle="-", color="C3", linewidth=2, markersize=6)
    ax.set_xticks(x)
    ax.set_xticklabels(x_labels)
    ax.set_ylabel("dTV (advertiser displacement)")
    ax.set_xlabel("Group")
    ax.set_title(f"Seed {seed}: dTV by group")
    ax.set_ylim(0, 1.0)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    p = out_dir / f"07_dTV_by_group_seed{seed}.png"
    fig.savefig(p, dpi=150)
    plt.close(fig)
    saved.append(p)

    # 4) impression_ratio — one line
    ir_ys = []
    for g in groups_ordered:
        comp = (by_group.get(str(g), {}) or {}).get("comparison") or {}
        ir_ys.append(float(comp.get("impression_ratio", 0)))
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.plot(x, ir_ys, marker="o", linestyle="-", color="C4", linewidth=2, markersize=6)
    ax.axhline(y=1.0, color="gray", linestyle="--", alpha=0.7)
    ax.set_xticks(x)
    ax.set_xticklabels(x_labels)
    ax.set_ylabel("impression_ratio")
    ax.set_xlabel("Group")
    ax.set_title(f"Seed {seed}: impression_ratio by group")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    p = out_dir / f"08_impression_ratio_by_group_seed{seed}.png"
    fig.savefig(p, dpi=150)
    plt.close(fig)
    saved.append(p)

    # 5) total_payment — two lines GSP, Constrained
    gsp_p = []
    con_p = []
    for g in groups_ordered:
        gdata = by_group.get(str(g), {})
        gsp_p.append(float((gdata.get("GSP") or {}).get("total_payment", 0)))
        con_p.append(float((gdata.get("Constrained") or {}).get("total_payment", 0)))
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.plot(x, gsp_p, marker="o", linestyle="-", color="C0", label="GSP", linewidth=2, markersize=6)
    ax.plot(x, con_p, marker="o", linestyle="--", color="C1", label="Constrained", linewidth=2, markersize=6)
    ax.set_xticks(x)
    ax.set_xticklabels(x_labels)
    ax.set_ylabel("total_payment")
    ax.set_xlabel("Group")
    ax.set_title(f"Seed {seed}: total_payment by group")
    ax.legend(loc="best")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    p = out_dir / f"09_total_payment_by_group_seed{seed}.png"
    fig.savefig(p, dpi=150)
    plt.close(fig)
    saved.append(p)

    # 6) exposure_female_share — two lines GSP, Constrained
    gsp_f = []
    con_f = []
    for g in groups_ordered:
        gdata = by_group.get(str(g), {})
        share_g = (gdata.get("GSP") or {}).get("exposure_share_by_gender") or {}
        share_c = (gdata.get("Constrained") or {}).get("exposure_share_by_gender") or {}
        gsp_f.append(float(share_g.get("female", 0)))
        con_f.append(float(share_c.get("female", 0)))
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.plot(x, gsp_f, marker="o", linestyle="-", color="C0", label="GSP", linewidth=2, markersize=6)
    ax.plot(x, con_f, marker="o", linestyle="--", color="C1", label="Constrained", linewidth=2, markersize=6)
    ax.axhline(y=0.5, color="gray", linestyle="--", alpha=0.7)
    ax.set_xticks(x)
    ax.set_xticklabels(x_labels)
    ax.set_ylabel("exposure_female_share")
    ax.set_xlabel("Group")
    ax.set_title(f"Seed {seed}: exposure_female_share by group")
    ax.set_ylim(0, 1.0)
    ax.legend(loc="best")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    p = out_dir / f"10_exposure_female_share_by_group_seed{seed}.png"
    fig.savefig(p, dpi=150)
    plt.close(fig)
    saved.append(p)

    for p in saved:
        print(f"Saved: {p}")
    return 0

def main():
    project_root = Path(__file__).resolve().parent.parent
    if len(sys.argv) < 2:
        report_path = project_root / "logs" / "formal_experiment" / "experiment_report_seed2_20260219_144404.json"
        out_dir = project_root / "logs" / "formal_experiment"
    else:
        report_path = Path(sys.argv[1])
        out_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else report_path.parent
    return plot_one_report(report_path, out_dir)

if __name__ == "__main__":
    sys.exit(main())
