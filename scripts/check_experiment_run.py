#!/usr/bin/env python3
"""
Quick self-check: can the full experiment pipeline run?
- Load env, create runner, create agents for all 4 groups, run 2 rounds per experiment (no full 1000).
"""
import os
import sys

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(_root)
sys.path.insert(0, _root)

_env = os.path.join(_root, ".env")
if os.path.isfile(_env):
    with open(_env, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                k, v = k.strip(), v.strip().strip('"').strip("'")
                if k and v:
                    os.environ[k] = v

from experiments.config import ExperimentConfig
from experiments.agent_factory import AgentFactory
from experiments.experiment_runner import ExperimentRunner
from mechanisms.gsp_mechanism import GSPMechanism
from engine.simulation import SimulationEngine
from tools.impression_pool import ImpressionPool


def main():
    print("1. Config...")
    assert ExperimentConfig.DATA_ROOT
    assert os.path.isdir(ExperimentConfig.DATA_ROOT)
    pool_path = os.path.join(ExperimentConfig.DATA_ROOT, "impression_pool_original.log.txt")
    assert os.path.isfile(pool_path), f"Missing {pool_path}"
    print("   OK: DATA_ROOT and impression pool exist.")

    print("2. Create runner (LLMClient init)...")
    runner = ExperimentRunner()
    print("   OK: ExperimentRunner created.")

    print("3. Create agents for each group...")
    for group_num in range(1, 5):
        configs = ExperimentConfig.get_experiment_group_configs(group_num)
        if group_num >= 2:
            for c in configs:
                if (c.get("strategy") or "").startswith("adaptive_profit_") or (c.get("strategy") or "").startswith("fairness_aware_"):
                    c["llm_client"] = runner._llm_client
        agents = AgentFactory.create_agents(configs)
        assert len(agents) == 9
        print(f"   Group {group_num}: {len(agents)} agents OK.")

    print("4. Run 2 rounds (Group1 GSP only)...")
    configs = ExperimentConfig.get_experiment_group_configs(1)
    agents = AgentFactory.create_agents(configs)
    pool = ImpressionPool(data_root=ExperimentConfig.DATA_ROOT, random_seed=ExperimentConfig.get_random_seed())
    mech = GSPMechanism(data_root=ExperimentConfig.DATA_ROOT)
    engine = SimulationEngine(agents, 2, verbose=False, impression_pool=pool)
    engine.platform = mech
    history = engine.run()
    assert len(history) == 2
    print("   OK: 2 rounds completed.")

    print("\nSelf-check passed: experiment can run end-to-end.")


if __name__ == "__main__":
    main()
