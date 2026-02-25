"""
Experiment runner: 4 groups x 2 mechanisms, fairness metrics.
"""
import json
import os
import time
from datetime import datetime
from typing import List, Dict, Any
from experiments.agent_factory import AgentFactory
from experiments.config import ExperimentConfig
from mechanisms.gsp_mechanism import GSPMechanism
from mechanisms.constrained_auction import ConstrainedAuctionMechanism
from metrics.gender_fairness_metrics import GenderFairnessMetrics
from engine.simulation import SimulationEngine
from tools.impression_pool import ImpressionPool

def _ensure_env_loaded():
    """Ensure .env is loaded so OPENAI_API_KEY is set (required for real LLM API). Always overwrite from file."""
    _root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    _path = os.path.join(_root, ".env")
    if not os.path.isfile(_path):
        return
    with open(_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                k, v = k.strip(), v.strip().strip('"').strip("'")
                if k:
                    os.environ[k] = v

_ensure_env_loaded()

class ExperimentRunner:
    """Runs 4 groups x 2 mechanisms and produces fairness comparison report."""

    def __init__(self):
        _ensure_env_loaded()
        # Read API key from .env and pass to LLMClient (prefer cwd, same as run_one_seed subprocess)
        api_key_from_file = None
        for _root in [os.getcwd(), os.path.dirname(os.path.dirname(os.path.abspath(__file__)))]:
            _path = os.path.join(_root, ".env")
            if not os.path.isfile(_path):
                continue
            with open(_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("#") or "=" not in line:
                        continue
                    if line.startswith("OPENAI_API_KEY="):
                        _, v = line.split("=", 1)
                        v = v.strip().strip('"').strip("'")
                        if v:
                            api_key_from_file = v
                        break
            if api_key_from_file:
                break
        print("[ExperimentRunner] api_key from .env file:", "YES (len=%d)" % len(api_key_from_file) if api_key_from_file else "NO")
        data_root = ExperimentConfig.DATA_ROOT
        from tools.llm_client import LLMClient
        self._llm_client = LLMClient(
            model=ExperimentConfig.LLM_MODEL,
            temperature=ExperimentConfig.LLM_TEMPERATURE,
            api_key=api_key_from_file
        )
        if self._llm_client.use_mock:
            key_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
            print("[ExperimentRunner] LLM is in MOCK mode (no API calls). Ensure OPENAI_API_KEY is in project root .env file:", key_path)
        else:
            k = os.getenv("OPENAI_API_KEY", "")
            print("[ExperimentRunner] LLM API enabled. OPENAI_API_KEY set:", (k[:12] + "..." if len(k) > 12 else "yes"))
        self.mechanism_factories = {
            "GSP": lambda: GSPMechanism(data_root=data_root),
            "Constrained": lambda: ConstrainedAuctionMechanism(data_root=data_root)
        }
        self.results = {}
        self.run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.random_seed = ExperimentConfig.get_random_seed()
        os.makedirs("logs", exist_ok=True)
        print(f"[Seed: {self.random_seed}] Experiment random seed (for log/report traceability)")
        print("Creating unified impression pool...")
        self.impression_pool = ImpressionPool(
            data_root=ExperimentConfig.DATA_ROOT,
            random_seed=ExperimentConfig.get_random_seed()
        )
        print(f"  Impression pool ready: {len(self.impression_pool)} impressions\n")
        
    def run_single_experiment(self, mechanism_name: str,
                              mechanism,
                              agents: List[Any], 
                              total_rounds: int = None) -> Dict[str, Any]:
        """Run a single experiment (one group, one mechanism)."""
        total_rounds = total_rounds or ExperimentConfig.TOTAL_ROUNDS

        print(f"\n{'='*50}")
        print(f"Running experiment: {mechanism_name}")
        print(f"{'='*50}")

        engine = SimulationEngine(
            agents, total_rounds, verbose=False, impression_pool=self.impression_pool,
            random_seed=self.random_seed
        )
        engine.platform = mechanism
        start_time = time.time()
        round_history = engine.run()
        end_time = time.time()

        result = {
            "mechanism": mechanism_name,
            "duration": end_time - start_time,
            "total_rounds": total_rounds,
            "agent_count": len(agents),
            "mechanism_info": mechanism.get_mechanism_info()
        }
        
        gender_metrics = GenderFairnessMetrics(data_root=ExperimentConfig.DATA_ROOT)
        result["fairness_metrics"] = gender_metrics.compute(round_history)
        result["round_history"] = round_history
        self._save_round_history(mechanism_name, result)
        
        return result
    
    def run_all_experiments(self) -> Dict[str, Any]:
        """Run all experiments: 4 groups x 2 mechanisms = 8 runs (audience gender fairness metrics)."""
        print("="*70)
        print("Starting AI Agent Impact on Fairness Mechanisms Experiment")
        print("="*70)
        print("\nDesign: 4 groups x 2 mechanisms = 8 experiment combinations")
        print("Mechanisms: GSP (baseline), Constrained (audience gender constraint)")
        print("Group 1: DataDriven only (9)")
        print("Group 2: 9 AdaptiveProfitAgent")
        print("Group 3: 9 FairnessAwareAgent")
        print("Group 4: Mixed 3+3+3 (DataDriven + Adaptive + Fairness)")
        print()

        self.results = {}

        for group_num in range(1, 5):
            print(f"\n{'#'*70}")
            print(f"Experiment group {group_num}")
            print(f"{'#'*70}")

            configs = ExperimentConfig.get_experiment_group_configs(group_num)
            if group_num >= 2:
                for c in configs:
                    if (c.get("strategy") or "").startswith("adaptive_profit_") or (c.get("strategy") or "").startswith("fairness_aware_"):
                        c["llm_client"] = self._llm_client
            agents = AgentFactory.create_agents(configs)

            agent_types = {}
            for agent in agents:
                agent_type = type(agent).__name__
                agent_types[agent_type] = agent_types.get(agent_type, 0) + 1
            print(f"Agent composition: {agent_types}")

            for mechanism_name, factory in self.mechanism_factories.items():
                agents = AgentFactory.create_agents(configs)
                mechanism = factory()
                experiment_key = f"Group{group_num}_{mechanism_name}"
                print(f"\nRunning: {experiment_key}")
                
                result = self.run_single_experiment(mechanism_name, mechanism, agents)
                result["group_num"] = group_num
                result["agent_composition"] = agent_types
                self.results[experiment_key] = result
        
        comparison_report = self._generate_comparison_report()
        summary = self._generate_summary()
        report_path = os.path.join("logs", f"experiment_report_{self.run_timestamp}.json")
        try:
            with open(report_path, "w", encoding="utf-8") as f:
                json.dump({
                    "run_timestamp": self.run_timestamp,
                    "random_seed": self.random_seed,
                    "summary": summary,
                    "comparison_report": comparison_report,
                    "experiment_keys": list(self.results.keys()),
                }, f, indent=2, ensure_ascii=False)
            print(f"\n  Report saved: {report_path}")
        except Exception as e:
            print(f"\n  Failed to save report: {e}")
        return {
            "experiment_results": self.results,
            "comparison_report": comparison_report,
            "summary": summary
        }
    
    def _save_round_history(self, mechanism_name: str, result: Dict[str, Any]):
        history = result.get("round_history", [])
        fairness = result.get("fairness_metrics", {})
        group_num = result.get("group_num", 0)
        agent_composition = result.get("agent_composition", {})
        
        serializable_history = []
        for record in history:
            serializable_history.append({
                "round": record.get("round"),
                "winner": record.get("winner"),
                "payment": record.get("payment"),
                "bids": [
                    {"agent": name, "bid": float(bid)}
                    for name, bid in record.get("bids", [])
                ],
                "agent_stats": {
                    name: {
                        "bid": float(stats.get("bid", 0)),
                        "won": bool(stats.get("won", False)),
                        "budget": float(stats.get("budget", 0))
                    } for name, stats in record.get("agent_stats", {}).items()
                }
            })
        payload = {
            "random_seed": self.random_seed,
            "group_num": group_num,
            "mechanism": mechanism_name,
            "agent_composition": agent_composition,
            "fairness_metrics": fairness,
            "round_history": serializable_history
        }
        path = os.path.join("logs", f"fairness_{self.run_timestamp}_seed{self.random_seed}_Group{group_num}_{mechanism_name}.json")
        with open(path, "w") as f:
            json.dump(payload, f, indent=2)
    
    def _generate_comparison_report(self) -> Dict[str, Any]:
        """Build comparison report: by group and by mechanism."""
        report = {
            "by_group": {},
            "by_mechanism": {},
            "ai_impact_analysis": {},
            "recommendations": []
        }

        for exp_key, result in self.results.items():
            group_num = result.get("group_num", 0)
            mechanism_name = result["mechanism"]
            
            if group_num not in report["by_group"]:
                report["by_group"][group_num] = {}
            
            fairness = result["fairness_metrics"]
            report["by_group"][group_num][mechanism_name] = {
                "slift": fairness.get("slift"),
                "slift_weighted": fairness.get("slift_weighted"),
                "total_payment": fairness.get("total_payment"),
                "valid_rounds": fairness.get("valid_rounds"),
                "exposure_by_gender": fairness.get("exposure_by_gender"),
                "exposure_share_by_gender": fairness.get("exposure_share_by_gender"),
                "per_advertiser": fairness.get("per_advertiser"),
                "agent_composition": result.get("agent_composition", {})
            }
        
        # Per-group GSP vs Constrained: kappa, dTV, impression_ratio
        gender_metrics = GenderFairnessMetrics(data_root=ExperimentConfig.DATA_ROOT)
        for group_num in range(1, 5):
            gsp_key = f"Group{group_num}_GSP"
            c_key = f"Group{group_num}_Constrained"
            if gsp_key not in self.results or c_key not in self.results:
                continue
            try:
                comp = gender_metrics.compute_with_baseline(
                    self.results[c_key]["round_history"],
                    self.results[gsp_key]["round_history"]
                )
                if "comparison" not in report["by_group"][group_num]:
                    report["by_group"][group_num]["comparison"] = {}
                report["by_group"][group_num]["comparison"] = {
                    "kappa": comp.get("kappa"),
                    "dTV": comp.get("dTV"),
                    "impression_ratio": comp.get("impression_ratio"),
                }
            except Exception as e:
                report["by_group"][group_num]["comparison"] = {"error": str(e)}
        
        mechanisms = ["GSP", "Constrained"]
        for mechanism_name in mechanisms:
            report["by_mechanism"][mechanism_name] = {}
            for group_num in range(1, 5):
                exp_key = f"Group{group_num}_{mechanism_name}"
                if exp_key in self.results:
                    result = self.results[exp_key]
                    fairness = result["fairness_metrics"]
                    report["by_mechanism"][mechanism_name][f"Group{group_num}"] = {
                        "slift": fairness.get("slift"),
                        "slift_weighted": fairness.get("slift_weighted"),
                        "total_payment": fairness.get("total_payment"),
                        "valid_rounds": fairness.get("valid_rounds"),
                        "agent_composition": result.get("agent_composition", {})
                    }
        
        # AI impact analysis (core metric: slift_weighted)
        for mechanism_name in mechanisms:
            report["ai_impact_analysis"][mechanism_name] = {}
            group1_key = f"Group1_{mechanism_name}"
            group4_key = f"Group4_{mechanism_name}"
            
            if group1_key in self.results and group4_key in self.results:
                g1_val = self.results[group1_key]["fairness_metrics"].get("slift_weighted")
                g4_val = self.results[group4_key]["fairness_metrics"].get("slift_weighted")
                g1 = g1_val if g1_val is not None else 0.0
                g4 = g4_val if g4_val is not None else 0.0
                report["ai_impact_analysis"][mechanism_name] = {
                    "pure_datadriven_slift": g1,
                    "pure_ai_slift": g4,
                    "slift_change": g4 - g1,
                    "mechanism_robustness": "effective" if abs(g4 - g1) < 0.2 else "needs_attention"
                }
            if mechanism_name == "Constrained":
                comp1 = report["by_group"].get(1, {}).get("comparison", {})
                if "error" not in comp1:
                    report["ai_impact_analysis"].setdefault("baseline_vs_constrained", {})["kappa"] = comp1.get("kappa")
                    report["ai_impact_analysis"].setdefault("baseline_vs_constrained", {})["dTV"] = comp1.get("dTV")
                    report["ai_impact_analysis"].setdefault("baseline_vs_constrained", {})["impression_ratio"] = comp1.get("impression_ratio")
        
        recommendations = []
        for mechanism_name, analysis in report["ai_impact_analysis"].items():
            if mechanism_name == "baseline_vs_constrained":
                continue
            robustness = analysis.get("mechanism_robustness", "unknown")
            change = analysis.get("slift_change", 0)
            if robustness == "effective":
                recommendations.append(f"{mechanism_name} remains effective with AI agents (slift_weighted change: {change:+.3f})")
            else:
                recommendations.append(f"{mechanism_name} needs attention with AI agents (slift_weighted change: {change:+.3f})")
        
        report["recommendations"] = recommendations
        
        return report
    
    def _generate_summary(self) -> Dict[str, Any]:
        """Generate experiment summary."""
        total_agents = sum(result["agent_count"] for result in self.results.values())
        total_rounds = sum(result["total_rounds"] for result in self.results.values())
        total_duration = sum(result["duration"] for result in self.results.values())
        
        return {
            "total_experiments": len(self.results),
            "total_agents": total_agents,
            "total_rounds": total_rounds,
            "total_duration": total_duration,
            "mechanisms_tested": list(self.results.keys())
        }

def main():
    """Entry point."""
    runner = ExperimentRunner()
    results = runner.run_all_experiments()

    print("\n" + "="*70)
    print("Experiment Summary")
    print("="*70)

    comparison = results["comparison_report"]
    print("\n[By group] Core metric: slift_weighted; per group GSP vs Constrained; last line: kappa, dTV, impression_ratio")
    for group_num in sorted(comparison["by_group"].keys()):
        grp = comparison["by_group"][group_num]
        print(f"\nGroup {group_num}:")
        for mechanism, metrics in grp.items():
            if mechanism == "comparison":
                if metrics.get("error"):
                    print(f"  Comparison (GSP vs Constrained): failed — {metrics['error']}")
                else:
                    k, d, ir = metrics.get("kappa"), metrics.get("dTV"), metrics.get("impression_ratio")
                    k_str = f"{k:.4f}" if k is not None else "N/A"
                    d_str = f"{d:.4f}" if d is not None else "N/A"
                    ir_str = f"{ir:.4f}" if ir is not None else "N/A"
                    print(f"  Comparison (GSP vs Constrained): kappa = {k_str}, dTV = {d_str}, impression_ratio = {ir_str} (Leveling Down)")
                continue
            slift_w = metrics.get("slift_weighted")
            slift = metrics.get("slift")
            vr = metrics.get("valid_rounds")
            tp = metrics.get("total_payment")
            exp = metrics.get("exposure_by_gender") or {}
            slift_w_str = f"{slift_w:.4f}" if slift_w is not None else "—"
            slift_str = f"{slift:.4f}" if slift is not None else "—"
            vr_str = str(vr) if vr is not None else "—"
            tp_str = f"{tp:.2f}" if tp is not None else "—"
            exp_str = str(exp) if exp else "—"
            print(f"  {mechanism} fairness: slift_weighted={slift_w_str}, slift={slift_str}, valid_rounds={vr_str}, total_payment={tp_str}, exposure_by_gender={exp_str}, agents={metrics.get('agent_composition', {})}")

    print("\n[By mechanism] Core metric: slift_weighted")
    for mechanism, groups in comparison["by_mechanism"].items():
        print(f"\n{mechanism} across groups:")
        for group_key, metrics in sorted(groups.items()):
            slift_w = metrics.get("slift_weighted")
            slift_str = f"{slift_w:.4f}" if slift_w is not None else "N/A"
            print(f"  {group_key}: slift_weighted = {slift_str}")

    print("\n[AI impact analysis]")
    for mechanism, analysis in comparison["ai_impact_analysis"].items():
        if mechanism == "baseline_vs_constrained":
            k, d, ir = analysis.get("kappa"), analysis.get("dTV"), analysis.get("impression_ratio")
            print(f"\nBaseline vs Constrained (Group 1): kappa = {k}, dTV = {d}, impression_ratio = {ir}")
            continue
        print(f"\n{mechanism}:")
        print(f"  Pure DataDriven slift_weighted: {analysis.get('pure_datadriven_slift')}")
        print(f"  Pure AI slift_weighted: {analysis.get('pure_ai_slift')}")
        print(f"  slift_weighted change: {analysis.get('slift_change', 0):+.3f}")
        print(f"  Mechanism robustness: {analysis.get('mechanism_robustness')}")

    print("\n[Recommendations]")
    for rec in comparison["recommendations"]:
        print(f"  • {rec}")

    print(f"\nTotal: {len(results['experiment_results'])} experiments completed")

if __name__ == "__main__":
    main()


