"""
Recompute metrics from saved round history. No need to re-run auctions if metric rules change.
"""
import os
import sys
import argparse
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.save_round_history import load_round_history, compute_metrics_from_saved_history
from metrics.gender_fairness_metrics import GenderFairnessMetrics
from experiments.config import ExperimentConfig


def recompute_metrics_from_file(
    baseline_file: str,
    fair_file: str,
    data_root: str = None
):
    """Recompute metrics from saved baseline and fair round history. Args: baseline_file, fair_file, data_root (default ExperimentConfig.DATA_ROOT)."""
    data_root = data_root or ExperimentConfig.DATA_ROOT

    print("="*70)
    print("Recomputing metrics from saved round history")
    print("="*70)
    print()

    print("Loading round history...")
    baseline_history, baseline_metadata = load_round_history(baseline_file)
    fair_history, fair_metadata = load_round_history(fair_file)
    print()

    gender_metrics = GenderFairnessMetrics(data_root=data_root)

    print("Computing Baseline metrics...")
    baseline_metrics = gender_metrics.compute(baseline_history)

    print("Computing Fair Mechanism metrics...")
    fair_metrics = gender_metrics.compute(fair_history)

    print("Computing comparison (kappa and dTV)...")
    comparison_metrics = gender_metrics.compute_with_baseline(
        fair_history,
        baseline_history,
        strict_check=True
    )
    
    print("\n" + "="*70)
    print("Recomputed metrics")
    print("="*70)

    print("\n[Baseline (GSP)]")
    print(f"  slift: {baseline_metrics['slift']:.4f}")
    print(f"  total_payment: {baseline_metrics['total_payment']:.2f}")
    print(f"  valid_rounds: {baseline_metrics['valid_rounds']}")
    print(f"  skipped_rounds: {baseline_metrics['skipped_rounds']}")
    
    print("\n[Fair Mechanism (ConstrainedAuction)]")
    print(f"  slift: {fair_metrics['slift']:.4f}")
    print(f"  total_payment: {fair_metrics['total_payment']:.2f}")
    print(f"  valid_rounds: {fair_metrics['valid_rounds']}")
    print(f"  skipped_rounds: {fair_metrics['skipped_rounds']}")
    
    print("\n[Comparison]")
    if comparison_metrics['kappa'] is not None:
        print(f"  κ (Revenue Ratio): {comparison_metrics['kappa']:.4f}")
    else:
        print(f"  κ (Revenue Ratio): None")
    if comparison_metrics['dTV'] is not None:
        print(f"  dTV (Advertiser Displacement): {comparison_metrics['dTV']:.4f}")
    else:
        print(f"  dTV (Advertiser Displacement): None")
    
    print("\n[Per-advertiser (Fair Mechanism)]")
    for adv_name, stats in sorted(comparison_metrics['per_advertiser'].items()):
        if stats['E_i,total'] > 0:
            print(f"  {adv_name}:")
            print(f"    E_i,m={stats['E_i,m']}, E_i,f={stats['E_i,f']}")
            print(f"    q_i,m={stats['q_i,m']:.3f}, slift_i={stats['slift_i']:.3f}")
    
    return {
        "baseline_metrics": baseline_metrics,
        "fair_metrics": fair_metrics,
        "comparison_metrics": comparison_metrics,
        "baseline_metadata": baseline_metadata,
        "fair_metadata": fair_metadata
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Recompute metrics from saved round history")
    parser.add_argument("baseline_file", help="Baseline round history JSON path")
    parser.add_argument("fair_file", help="Fair round history JSON path")
    parser.add_argument("--data_root", default=None, help="Data root (default: ExperimentConfig.DATA_ROOT)")

    args = parser.parse_args()

    results = recompute_metrics_from_file(
        args.baseline_file,
        args.fair_file,
        data_root=args.data_root
    )

    print("\n" + "="*70)
    print("Recompute done.")
    print("="*70)

