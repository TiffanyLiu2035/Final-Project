#!/usr/bin/env python3
"""
Visualize last 6 experiment runs. Reads only experiment_report_seed*_*.json from logs.
Usage (project root): PYTHONPATH=. python scripts/plot_last_six_experiments.py
Output: PNGs under logs/figures_last6/
"""
from __future__ import annotations

import json
import re
from pathlib import Path


def main() -> None:
    project_root = Path(__file__).resolve().parent.parent
    logs_dir = project_root / "logs"
    out_dir = logs_dir / "figures_last6"
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1) Find latest 6 reports (by filename timestamp)
    pattern = re.compile(r"experiment_report_seed(\d+)_(\d{8}_\d{6})\.json")
    reports = []
    for p in logs_dir.glob("experiment_report_seed*_*.json"):
        m = pattern.match(p.name)
        if m:
            seed_str, ts = m.group(1), m.group(2)
            reports.append((p, int(seed_str), ts))
    reports.sort(key=lambda x: x[2], reverse=True)
    selected = reports[:6]
    if not selected:
        print("No experiment_report_seed*_*.json found, exit")
        return
    print(f"Using last {len(selected)} runs: {[p.name for p, _, _ in selected]}")

    # 2) Flatten to table: seed, group, mechanism, slift_weighted, ...
    rows = []
    for path, seed, _ in selected:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        by_group = (data.get("comparison_report") or {}).get("by_group") or {}
        for gkey, gdata in by_group.items():
            if not isinstance(gdata, dict):
                continue
            for mech in ("GSP", "Constrained"):
                m = gdata.get(mech)
                if not m:
                    continue
                share = (m.get("exposure_share_by_gender") or {})
                rows.append({
                    "seed": seed,
                    "group": int(gkey) if str(gkey).isdigit() else gkey,
                    "mechanism": mech,
                    "slift_weighted": float(m.get("slift_weighted", 0)),
                    "slift": float(m.get("slift", 0)),
                    "total_payment": float(m.get("total_payment", 0)),
                    "exposure_male": float(share.get("male", 0)),
                    "exposure_female": float(share.get("female", 0)),
                })

    # 3) Aggregate: mean and std per (group, mechanism) for error bars
    from collections import defaultdict
    agg = defaultdict(lambda: {"slift_weighted": [], "total_payment": [], "exposure_female": []})
    for r in rows:
        key = (r["group"], r["mechanism"])
        agg[key]["slift_weighted"].append(r["slift_weighted"])
        agg[key]["total_payment"].append(r["total_payment"])
        agg[key]["exposure_female"].append(r["exposure_female"])

    def mean_std(xs):
        if not xs:
            return 0.0, 0.0
        n = len(xs)
        m = sum(xs) / n
        v = sum((x - m) ** 2 for x in xs) / n
        return m, (v ** 0.5) if n > 1 else 0.0

    groups = sorted({k[0] for k in agg})
    x_labels = [f"Group{g}" for g in groups]
    x = list(range(len(groups)))
    width = 0.35

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib
        matplotlib.rcParams["font.sans-serif"] = ["Arial Unicode MS", "DejaVu Sans", "sans-serif"]
        matplotlib.rcParams["axes.unicode_minus"] = False
    except Exception as e:
        print("matplotlib not available:", e)
        return

    # Fig 1: slift_weighted by group, mechanism (bar + error bar)
    fig1, ax1 = plt.subplots(figsize=(8, 5))
    gsp_means = []
    gsp_stds = []
    con_means = []
    con_stds = []
    for g in groups:
        gsp_means.append(mean_std(agg[(g, "GSP")]["slift_weighted"])[0])
        gsp_stds.append(mean_std(agg[(g, "GSP")]["slift_weighted"])[1])
        con_means.append(mean_std(agg[(g, "Constrained")]["slift_weighted"])[0])
        con_stds.append(mean_std(agg[(g, "Constrained")]["slift_weighted"])[1])
    bars1 = ax1.bar([i - width / 2 for i in x], gsp_means, width, yerr=gsp_stds, label="GSP", capsize=3)
    bars2 = ax1.bar([i + width / 2 for i in x], con_means, width, yerr=con_stds, label="Constrained", capsize=3)
    ax1.set_ylabel("slift_weighted")
    ax1.set_xlabel("Group")
    ax1.set_xticks(x)
    ax1.set_xticklabels(x_labels)
    ax1.set_title("Slift weighted (last 6 runs, mean ± std)")
    ax1.legend()
    ax1.grid(axis="y", alpha=0.3)
    fig1.tight_layout()
    fig1.savefig(out_dir / "01_slift_weighted_by_group.png", dpi=150)
    plt.close(fig1)
    print("Saved:", out_dir / "01_slift_weighted_by_group.png")

    # Fig 2: Female exposure share by group, mechanism
    fig2, ax2 = plt.subplots(figsize=(8, 5))
    gsp_f = [mean_std(agg[(g, "GSP")]["exposure_female"])[0] for g in groups]
    con_f = [mean_std(agg[(g, "Constrained")]["exposure_female"])[0] for g in groups]
    ax2.bar([i - width / 2 for i in x], gsp_f, width, label="GSP (female share)")
    ax2.bar([i + width / 2 for i in x], con_f, width, label="Constrained (female share)")
    ax2.axhline(y=0.5, color="gray", linestyle="--", alpha=0.7, label="50%")
    ax2.set_ylabel("Female exposure share")
    ax2.set_xlabel("Group")
    ax2.set_xticks(x)
    ax2.set_xticklabels(x_labels)
    ax2.set_title("Female exposure share (last 6 runs, mean)")
    ax2.legend()
    ax2.grid(axis="y", alpha=0.3)
    fig2.tight_layout()
    fig2.savefig(out_dir / "02_exposure_female_share_by_group.png", dpi=150)
    plt.close(fig2)
    print("Saved:", out_dir / "02_exposure_female_share_by_group.png")

    # Fig 3: total_payment by group, mechanism (bar + error bar)
    fig3, ax3 = plt.subplots(figsize=(8, 5))
    gsp_pm = [mean_std(agg[(g, "GSP")]["total_payment"]) for g in groups]
    con_pm = [mean_std(agg[(g, "Constrained")]["total_payment"]) for g in groups]
    ax3.bar([i - width / 2 for i in x], [m for m, _ in gsp_pm], width, yerr=[s for _, s in gsp_pm], label="GSP", capsize=3)
    ax3.bar([i + width / 2 for i in x], [m for m, _ in con_pm], width, yerr=[s for _, s in con_pm], label="Constrained", capsize=3)
    ax3.set_ylabel("Total payment")
    ax3.set_xlabel("Group")
    ax3.set_xticks(x)
    ax3.set_xticklabels(x_labels)
    ax3.set_title("Total payment (last 6 runs, mean ± std)")
    ax3.legend()
    ax3.grid(axis="y", alpha=0.3)
    fig3.tight_layout()
    fig3.savefig(out_dir / "03_total_payment_by_group.png", dpi=150)
    plt.close(fig3)
    print("Saved:", out_dir / "03_total_payment_by_group.png")

    # Fig 4: Per-seed GSP vs Constrained — slift_weighted group average
    seed_avg = defaultdict(lambda: {"GSP": [], "Constrained": []})
    for r in rows:
        seed_avg[r["seed"]][r["mechanism"]].append(r["slift_weighted"])
    seeds = sorted(seed_avg.keys())
    gsp_avg = [sum(seed_avg[s]["GSP"]) / len(seed_avg[s]["GSP"]) if seed_avg[s]["GSP"] else 0 for s in seeds]
    con_avg = [sum(seed_avg[s]["Constrained"]) / len(seed_avg[s]["Constrained"]) if seed_avg[s]["Constrained"] else 0 for s in seeds]
    fig4, ax4 = plt.subplots(figsize=(7, 5))
    ax4.scatter(gsp_avg, con_avg, c=range(len(seeds)), cmap="viridis", s=80, alpha=0.8)
    for i, s in enumerate(seeds):
        ax4.annotate(f"seed{s}", (gsp_avg[i], con_avg[i]), xytext=(5, 5), textcoords="offset points", fontsize=8)
    lims = [min(gsp_avg + con_avg), max(gsp_avg + con_avg)]
    ax4.plot(lims, lims, "k--", alpha=0.5, label="y=x")
    ax4.set_xlabel("GSP (avg slift_weighted over groups)")
    ax4.set_ylabel("Constrained (avg slift_weighted over groups)")
    ax4.set_title("Per-seed: GSP vs Constrained (last 6 runs)")
    ax4.legend()
    ax4.grid(alpha=0.3)
    fig4.tight_layout()
    fig4.savefig(out_dir / "04_per_seed_gsp_vs_constrained.png", dpi=150)
    plt.close(fig4)
    print("Saved:", out_dir / "04_per_seed_gsp_vs_constrained.png")

    # Fig 5: one plot per seed, two lines (GSP, Constrained) by group, 6 plots total
    groups_ordered = sorted({r["group"] for r in rows})
    seeds_ordered = sorted({r["seed"] for r in rows})
    line_data = defaultdict(lambda: {g: None for g in groups_ordered})
    for r in rows:
        line_data[(r["seed"], r["mechanism"])][r["group"]] = r["slift_weighted"]
    x = list(range(len(groups_ordered)))
    for seed in seeds_ordered:
        fig5, ax5 = plt.subplots(figsize=(7, 5))
        for mech, linestyle, color in (("GSP", "-", "C0"), ("Constrained", "--", "C1")):
            ys = [line_data[(seed, mech)][g] for g in groups_ordered]
            if any(y is None for y in ys):
                continue
            ax5.plot(x, ys, marker="o", linestyle=linestyle, color=color, label=mech, linewidth=2, markersize=6)
        ax5.set_xticks(x)
        ax5.set_xticklabels([f"Group{g}" for g in groups_ordered])
        ax5.set_ylabel("slift_weighted")
        ax5.set_xlabel("Group")
        ax5.set_title(f"Seed {seed}: slift_weighted by group")
        ax5.legend(loc="best")
        ax5.grid(True, alpha=0.3)
        ax5.set_ylim(0, 1.0)
        fig5.tight_layout()
        fig5.savefig(out_dir / f"05_slift_by_group_seed{seed}.png", dpi=150)
        plt.close(fig5)
        print("Saved:", out_dir / f"05_slift_by_group_seed{seed}.png")

    print("Done. Figures in:", out_dir)


if __name__ == "__main__":
    main()
