"""
Run Gender-based Fairness experiment: GSP vs ConstrainedAuction.

Runs two mechanisms on 9 trained data-driven agents and computes three core metrics:
1. Selection Lift (slift)
2. Revenue ratio κ (kappa)
3. Advertiser displacement dTV
"""
import os
import time
from experiments.agent_factory import AgentFactory
from experiments.config import ExperimentConfig
from mechanisms.gsp_mechanism import GSPMechanism
from mechanisms.constrained_auction import ConstrainedAuctionMechanism
from metrics.gender_fairness_metrics import GenderFairnessMetrics
from engine.simulation import SimulationEngine
from tools.impression_pool import ImpressionPool


def run_gender_fairness_experiment(
    fairness_strength: float = 0.2,
    penalty_scale: float = 1.0,
    total_rounds: int = None
):
    """
    Run GSP and ConstrainedAuction experiments and compute gender-based fairness metrics.

    Args:
        fairness_strength: Fairness strength parameter ℓ ∈ [0, 0.5]
        penalty_scale: Penalty scale parameter λ (default 1.0)
        total_rounds: Total number of rounds (default from ExperimentConfig)
    
    Returns:
        Dictionary containing results for both mechanisms
    """
    total_rounds = total_rounds or ExperimentConfig.TOTAL_ROUNDS
    
    print("="*70)
    print("Gender-based Fairness Experiment")
    print("="*70)
    print()
    print("Experiment config:")
    print("  - Agent type: 9 DataDrivenAgent")
    print("  - Total rounds:", total_rounds)
    print("  - Mechanisms: GSP (baseline), ConstrainedAuction (fair)")
    print("  - Fairness params: ℓ={}, λ={}".format(fairness_strength, penalty_scale))
    print()

    # Get group 1 config (9 DataDriven agents)
    configs = ExperimentConfig.get_group1_configs()

    # Create unified impression pool (read from merged test.log.txt)
    print("Creating unified impression pool...")
    print("  Reading from merged test.log.txt; each agent converts via its featindex")
    print("  Using all impressions (including unknown gender), closer to real RTB")
    impression_pool = ImpressionPool(
        data_root=ExperimentConfig.DATA_ROOT,
        random_seed=ExperimentConfig.RANDOM_SEED
    )
    print(f"  Impression pool ready: {len(impression_pool)} impressions")
    print("  Note: unknown-gender impressions are skipped by the mechanism (return None)")
    print()

    results = {}

    # ========== Run Baseline (GSP) ==========
    print("="*70)
    print("Running Baseline: GSP")
    print("="*70)
    
    baseline_agents = AgentFactory.create_agents(configs)
    baseline_mechanism = GSPMechanism(
        reserve_price=0.0,
        data_root=ExperimentConfig.DATA_ROOT
    )
    
    baseline_engine = SimulationEngine(
        baseline_agents, 
        total_rounds, 
        verbose=False, 
        impression_pool=impression_pool
    )
    baseline_engine.platform = baseline_mechanism
    
    start_time = time.time()
    baseline_round_history = baseline_engine.run()
    baseline_duration = time.time() - start_time
    
    print(f"  Baseline done in {baseline_duration:.2f}s")
    print(f"  Total rounds: {len(baseline_round_history)}")
    print(f"  Valid rounds: {sum(1 for r in baseline_round_history if not r.get('skipped', False))}")
    print()

    # ========== Run Fair Mechanism (ConstrainedAuction) ==========
    print("="*70)
    print("Running Fair Mechanism: ConstrainedAuction")
    print("="*70)

    # Reset impression pool index so fair mechanism uses the same impression sequence
    impression_pool.current_idx = 0
    
    fair_agents = AgentFactory.create_agents(configs)
    fair_mechanism = ConstrainedAuctionMechanism(
        reserve_price=0.0,
        fairness_strength=fairness_strength,
        penalty_scale=penalty_scale,
        data_root=ExperimentConfig.DATA_ROOT
    )
    
    fair_engine = SimulationEngine(
        fair_agents,
        total_rounds,
        verbose=False,
        impression_pool=impression_pool
    )
    fair_engine.platform = fair_mechanism
    
    start_time = time.time()
    fair_round_history = fair_engine.run()
    fair_duration = time.time() - start_time
    
    print(f"  Fair mechanism done in {fair_duration:.2f}s")
    print(f"  Total rounds: {len(fair_round_history)}")
    print(f"  Valid rounds: {sum(1 for r in fair_round_history if not r.get('skipped', False))}")
    print()

    # ========== Bidding done; compute metrics ==========
    print("="*70)
    print("Computing Gender-based Fairness Metrics")
    print("="*70)

    gender_metrics = GenderFairnessMetrics(data_root=ExperimentConfig.DATA_ROOT)

    print("\nComputing Baseline (GSP) metrics...")
    baseline_metrics = gender_metrics.compute(baseline_round_history)

    print("Computing Fair Mechanism (ConstrainedAuction) metrics...")
    fair_metrics = gender_metrics.compute(fair_round_history)

    print("Computing comparison metrics (κ and dTV)...")
    comparison_metrics = gender_metrics.compute_with_baseline(
        fair_round_history,
        baseline_round_history,
        strict_check=True
    )
    
    # ========== Show results ==========
    print("\n" + "="*70)
    print("Experiment Results")
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
    
    print("\n[Comparison metrics]")
    if comparison_metrics['kappa'] is not None:
        print(f"  κ (Revenue Ratio): {comparison_metrics['kappa']:.4f}")
    else:
        print(f"  κ (Revenue Ratio): None (requires valid rounds)")
    if comparison_metrics['dTV'] is not None:
        print(f"  dTV (Advertiser Displacement): {comparison_metrics['dTV']:.4f}")
    else:
        print(f"  dTV (Advertiser Displacement): None (requires valid rounds)")

    print("\n[Per-advertiser stats (Fair Mechanism)]")
    for adv_name, stats in sorted(comparison_metrics['per_advertiser'].items()):
        if stats['E_i,total'] > 0:
            print(f"  {adv_name}:")
            print(f"    E_i,m={stats['E_i,m']}, E_i,f={stats['E_i,f']}")
            print(f"    q_i,m={stats['q_i,m']:.3f}, slift_i={stats['slift_i']:.3f}")
    
    # Save round history for later metric recomputation
    from tools.save_round_history import save_round_history
    from datetime import datetime

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    os.makedirs("logs", exist_ok=True)

    # Save baseline round history
    baseline_file = f"logs/gender_fairness_baseline_{timestamp}.json"
    save_round_history(
        baseline_round_history,
        baseline_file,
        metadata={
            "mechanism": "GSP",
            "duration": baseline_duration,
            "total_rounds": total_rounds,
            "fairness_strength": None,
            "penalty_scale": None
        }
    )
    
    # Save fair mechanism round history
    fair_file = f"logs/gender_fairness_fair_{timestamp}.json"
    save_round_history(
        fair_round_history,
        fair_file,
        metadata={
            "mechanism": "ConstrainedAuction",
            "duration": fair_duration,
            "total_rounds": total_rounds,
            "fairness_strength": fairness_strength,
            "penalty_scale": penalty_scale
        }
    )
    
    print(f"\n  Round history saved:")
    print(f"   Baseline: {baseline_file}")
    print(f"   Fair: {fair_file}")
    print(f"   You can recompute metrics from these files if metric rules change.")

    # Store results
    results = {
        "baseline": {
            "mechanism": "GSP",
            "duration": baseline_duration,
            "round_history": baseline_round_history,
            "metrics": baseline_metrics,
            "saved_file": baseline_file
        },
        "fair": {
            "mechanism": "ConstrainedAuction",
            "duration": fair_duration,
            "round_history": fair_round_history,
            "metrics": fair_metrics,
            "fairness_strength": fairness_strength,
            "penalty_scale": penalty_scale,
            "saved_file": fair_file
        },
        "comparison": {
            "kappa": comparison_metrics['kappa'],
            "dTV": comparison_metrics['dTV'],
            "slift_baseline": baseline_metrics['slift'],
            "slift_fair": fair_metrics['slift']
        }
    }
    
    return results


if __name__ == "__main__":
    # Run experiment (1000 rounds is enough with gender-filtered pool)
    results = run_gender_fairness_experiment(
        fairness_strength=0.2,
        penalty_scale=1.0,
        total_rounds=1000
    )

    print("\n" + "="*70)
    print("Experiment complete.")
    print("="*70)

