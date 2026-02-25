"""
Agent creation factory for experiment groups (DataDriven, AdaptiveProfit, FairnessAware).
"""
from typing import List, Dict, Any
import os
from agents.data_driven_agent import DataDrivenAgent
from agents.llm_bidding_agent import AdaptiveProfitAgent, FairnessAwareAgent
from experiments.config import ExperimentConfig


class AgentFactory:
    """Factory that builds agents from experiment configs."""

    @staticmethod
    def create_agents(configs: List[Dict[str, Any]]) -> List[Any]:
        agents = []
        for config in configs:
            agent = AgentFactory._create_single_agent(config)
            agents.append(agent)
        return agents

    @staticmethod
    def _create_single_agent(config: Dict[str, Any]) -> Any:
        name = config["name"]
        budget = config["budget"]
        strategy = config["strategy"]
        profile = config["profile"]

        if strategy.startswith("data_driven_"):
            adv_id = config.get("adv_id") or (name.split("_")[-1] if "_" in name else None)
            model_dir_root = config.get("model_root", "models")
            model_dir = os.path.join(model_dir_root, adv_id)
            data_root = config.get("data_root")
            agent = DataDrivenAgent(
                name=name,
                budget=budget,
                model_dir=model_dir,
                profile=profile,
                item_value=ExperimentConfig.ITEM_VALUE,
                adv_id=adv_id,
                data_root=data_root,
                budget_level=config.get("budget_level", "medium")
            )
        elif strategy.startswith("adaptive_profit_"):
            adv_id = config.get("adv_id") or strategy.replace("adaptive_profit_", "").strip() or name.split("_")[-1]
            model_dir_root = config.get("model_root", "models")
            model_dir = os.path.join(model_dir_root, adv_id)
            data_root = config.get("data_root", ExperimentConfig.DATA_ROOT)
            update_interval = config.get("update_interval", 50)
            agent = AdaptiveProfitAgent(
                name=name,
                budget=budget,
                model_dir=model_dir,
                profile=profile,
                item_value=ExperimentConfig.ITEM_VALUE,
                adv_id=adv_id,
                data_root=data_root,
                budget_level=config.get("budget_level", "medium"),
                update_interval=update_interval,
                system_prompt_suffix=config.get("system_prompt_suffix", ""),
                llm_client=config.get("llm_client"),
            )
        elif strategy.startswith("fairness_aware_"):
            adv_id = config.get("adv_id") or strategy.replace("fairness_aware_", "").strip() or name.split("_")[-1]
            model_dir_root = config.get("model_root", "models")
            model_dir = os.path.join(model_dir_root, adv_id)
            data_root = config.get("data_root", ExperimentConfig.DATA_ROOT)
            update_interval = config.get("update_interval", 50)
            agent = FairnessAwareAgent(
                name=name,
                budget=budget,
                model_dir=model_dir,
                profile=profile,
                item_value=ExperimentConfig.ITEM_VALUE,
                adv_id=adv_id,
                data_root=data_root,
                budget_level=config.get("budget_level", "medium"),
                update_interval=update_interval,
                system_prompt_suffix=config.get("system_prompt_suffix", ""),
                llm_client=config.get("llm_client"),
                slift_target=config.get("slift_target", 1.0),
                slift_low_threshold=config.get("slift_low_threshold", 0.95),
            )
        else:
            raise ValueError(f"Unknown strategy: {strategy}")

        setattr(agent, "group", config.get("group", "unknown"))
        setattr(agent, "adv_id", config.get("adv_id"))
        setattr(agent, "budget_level", config.get("budget_level", "medium"))
        return agent
    
    @staticmethod
    def create_experiment_agents() -> List[Any]:
        """Create agents for the default data-driven group (Group 1)."""
        configs = ExperimentConfig.get_agent_configs()
        return AgentFactory.create_agents(configs)
