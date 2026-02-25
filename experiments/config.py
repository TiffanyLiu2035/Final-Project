"""
Experiment configuration parameters.
"""
import os
import random
from typing import Dict, List, Any

def _load_agent_tuning_overrides() -> Dict[str, Any]:
    """Load overrides from experiments/agent_tuning.yaml (optional). Returns empty dict if file missing or keys unset."""
    try:
        import yaml
    except ImportError:
        return {}
    config_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(config_dir, "agent_tuning.yaml")
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}

class ExperimentConfig:
    """Experiment configuration class."""

    # Agent config: nine data-driven agents, one per real advertiser
    ADVERTISER_IDS = [
        "1458", "2259", "2261",  # high budget
        "2821", "2997", "3358",  # medium budget
        "3386", "3427", "3476"   # low budget
    ]

    # Budget levels and ranges per advertiser (for budget diversity only; not tied to fairness metrics)
    # Order matches ADVERTISER_IDS: first 3 high, next 3 medium, last 3 low
    BUDGET_LEVELS = [
        "high", "high", "high",
        "medium", "medium", "medium",
        "low", "low", "low"
    ]
    BUDGET_RANGES_BY_LEVEL = {
        "high": (2000, 3000),
        "medium": (1000, 1500),
        "low": (500, 800),
    }
    # Profile distribution (same order as ADVERTISER_IDS; used for DataDriven bid factors)
    PROFILES = [
        "aggressive", "neutral", "aggressive",
        "neutral", "conservative", "neutral",
        "conservative", "neutral", "conservative",
    ]
    RANDOM_SEED = 42

    @classmethod
    def get_random_seed(cls) -> int:
        """Current experiment seed (from env EXPERIMENT_RANDOM_SEED if set). Use for ImpressionPool and any randomness."""
        return int(os.environ.get("EXPERIMENT_RANDOM_SEED", str(cls.RANDOM_SEED)))

    # Data root: prefer env IPINYOU_DATA_ROOT, else project DATA dir.
    # Experiments read impression pool from DATA_ROOT/impression_pool_original.log.txt; for DataDriven/LLM gender or CTR, advertiser subdirs (e.g. 1458/featindex.txt) must exist under DATA_ROOT.
    _project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DATA_ROOT = os.getenv("IPINYOU_DATA_ROOT", os.path.join(_project_root, "DATA"))
    
    # Experiment parameters
    TOTAL_ROUNDS = 1000
    ITEM_VALUE = 100
    CTR_RANGE = (0.05, 0.20)

    # LLM defaults
    LLM_MODEL = "gpt-4o-mini"
    LLM_TEMPERATURE = 0.2
    # LLM bidding agent strategy update
    UPDATE_INTERVAL = 50
    SLIFT_LOW_THRESHOLD = 0.95
    # Type 2 persona diversity (i % 3)
    ADAPTIVE_PERSONAS = [
        "Risk Preference: Aggressive. You prefer high bids to win more, accepting lower ROI.",
        "Risk Preference: Conservative. You are extremely cautious, strictly avoiding low ROI.",
        "Risk Preference: Balanced. You seek a stable balance between volume and efficiency.",
    ]
    # Type 3 persona diversity (i % 3)
    FAIRNESS_PERSONAS = [
        "Compliance Style: Radical. You prioritize fairness above all else, reacting strongly to any bias.",
        "Compliance Style: Pragmatic. You try to fix fairness issues gradually while protecting profit.",
        "Compliance Style: Strict. You follow the fairness threshold precisely.",
    ]

    # Constrained auction parameters (for Constrained mechanism)
    MAX_BID_RATIO = 0.5
    MIN_WIN_RATE = 0.1

    MODEL_ROOT = "models"
    
    @classmethod
    def _agent_tuning(cls) -> Dict[str, Any]:
        """Merge agent_tuning.yaml overrides with class defaults for tuning without code changes. File is read each time; edits take effect on next run."""
        o = _load_agent_tuning_overrides()
        return {
            "update_interval": o.get("update_interval", cls.UPDATE_INTERVAL),
            "slift_low_threshold": o.get("slift_low_threshold", cls.SLIFT_LOW_THRESHOLD),
            "adaptive_personas": o.get("adaptive_personas") or cls.ADAPTIVE_PERSONAS,
            "fairness_personas": o.get("fairness_personas") or cls.FAIRNESS_PERSONAS,
        }
    
    @classmethod
    def get_agent_configs(cls) -> List[Dict[str, Any]]:
        """Return configs for 9 data-driven agents, one per real advertiser."""
        configs = []
        random.seed(cls.get_random_seed())
        for idx in range(len(cls.ADVERTISER_IDS)):
            adv_id = cls.ADVERTISER_IDS[idx]
            budget_level = cls.BUDGET_LEVELS[idx]
            budget = random.uniform(*cls.BUDGET_RANGES_BY_LEVEL[budget_level])
            profile = cls.PROFILES[idx]
            configs.append({
                "name": f"adv_{adv_id}",
                "group": budget_level,
                "budget": budget,
                "strategy": f"data_driven_{adv_id}",
                "profile": profile,
                "adv_id": adv_id,
                "model_root": cls.MODEL_ROOT,
                "data_root": cls.DATA_ROOT,
                "budget_level": budget_level,
            })
        return configs

    @classmethod
    def get_group1_configs(cls) -> List[Dict[str, Any]]:
        """Group 1: DataDriven only (9 DataDrivenAgents)."""
        return cls.get_agent_configs()
    
    @classmethod
    def get_group2_configs(cls, update_interval: int = None) -> List[Dict[str, Any]]:
        """Group 2: 9 adaptive profit-seeking AI agents (Type 2)."""
        t = cls._agent_tuning()
        interval = update_interval if update_interval is not None else t["update_interval"]
        return cls.get_adaptive_profit_configs(update_interval=interval)
    
    @classmethod
    def get_group3_configs(cls, update_interval: int = None, slift_low_threshold: float = None) -> List[Dict[str, Any]]:
        """Group 3: 9 fairness-aware profit-seeking AI agents (Type 3)."""
        t = cls._agent_tuning()
        interval = update_interval if update_interval is not None else t["update_interval"]
        threshold = slift_low_threshold if slift_low_threshold is not None else t["slift_low_threshold"]
        return cls.get_fairness_aware_configs(update_interval=interval, slift_low_threshold=threshold)
    
    @classmethod
    def get_group4_configs(cls, update_interval: int = None, slift_low_threshold: float = None) -> List[Dict[str, Any]]:
        """Group 4: Mixed (3 data-driven + 3 adaptive profit + 3 fairness-aware)."""
        t = cls._agent_tuning()
        interval = update_interval if update_interval is not None else t["update_interval"]
        threshold = slift_low_threshold if slift_low_threshold is not None else t["slift_low_threshold"]
        return cls.get_mixed_three_types_configs(update_interval=interval, slift_low_threshold=threshold)
    
    @classmethod
    def get_adaptive_profit_configs(cls, update_interval: int = None) -> List[Dict[str, Any]]:
        """Nine adaptive profit-seeking agents (Type 2); personas assigned by i % 3."""
        t = cls._agent_tuning()
        interval = update_interval if update_interval is not None else t["update_interval"]
        personas = t["adaptive_personas"]
        configs = []
        random.seed(cls.get_random_seed())
        for idx in range(len(cls.ADVERTISER_IDS)):
            adv_id = cls.ADVERTISER_IDS[idx]
            budget_level = cls.BUDGET_LEVELS[idx]
            budget = random.uniform(*cls.BUDGET_RANGES_BY_LEVEL[budget_level])
            profile = cls.PROFILES[idx]
            configs.append({
                "name": f"adaptive_adv_{adv_id}",
                "group": budget_level,
                "budget": budget,
                "strategy": f"adaptive_profit_{adv_id}",
                "profile": profile,
                "adv_id": adv_id,
                "model_root": cls.MODEL_ROOT,
                "data_root": cls.DATA_ROOT,
                "budget_level": budget_level,
                "update_interval": interval,
                "system_prompt_suffix": personas[idx % 3],
            })
        return configs
    
    @classmethod
    def get_fairness_aware_configs(cls, update_interval: int = None, slift_low_threshold: float = None) -> List[Dict[str, Any]]:
        """Nine fairness-aware profit-seeking agents (Type 3); personas assigned by i % 3."""
        t = cls._agent_tuning()
        interval = update_interval if update_interval is not None else t["update_interval"]
        threshold = slift_low_threshold if slift_low_threshold is not None else t["slift_low_threshold"]
        personas = t["fairness_personas"]
        configs = []
        random.seed(cls.get_random_seed())
        for idx in range(len(cls.ADVERTISER_IDS)):
            adv_id = cls.ADVERTISER_IDS[idx]
            budget_level = cls.BUDGET_LEVELS[idx]
            budget = random.uniform(*cls.BUDGET_RANGES_BY_LEVEL[budget_level])
            profile = cls.PROFILES[idx]
            configs.append({
                "name": f"fairness_adv_{adv_id}",
                "group": budget_level,
                "budget": budget,
                "strategy": f"fairness_aware_{adv_id}",
                "profile": profile,
                "adv_id": adv_id,
                "model_root": cls.MODEL_ROOT,
                "data_root": cls.DATA_ROOT,
                "budget_level": budget_level,
                "update_interval": interval,
                "slift_low_threshold": threshold,
                "system_prompt_suffix": personas[idx % 3],
            })
        return configs
    
    @classmethod
    def get_mixed_three_types_configs(cls, update_interval: int = None, slift_low_threshold: float = None) -> List[Dict[str, Any]]:
        """Three data-driven + three adaptive profit + three fairness-aware (9 agents total)."""
        t = cls._agent_tuning()
        interval = update_interval if update_interval is not None else t["update_interval"]
        threshold = slift_low_threshold if slift_low_threshold is not None else t["slift_low_threshold"]
        adaptive_personas = t["adaptive_personas"]
        fairness_personas = t["fairness_personas"]
        configs = []
        random.seed(cls.get_random_seed())
        for group_idx in range(3):
            for slot in range(3):
                idx = group_idx * 3 + slot
                adv_id = cls.ADVERTISER_IDS[idx]
                budget_level = cls.BUDGET_LEVELS[idx]
                budget = random.uniform(*cls.BUDGET_RANGES_BY_LEVEL[budget_level])
                profile = cls.PROFILES[idx]
                if slot == 0:
                    configs.append({
                        "name": f"adv_{adv_id}",
                        "group": budget_level,
                        "budget": budget,
                        "strategy": f"data_driven_{adv_id}",
                        "profile": profile,
                        "adv_id": adv_id,
                        "model_root": cls.MODEL_ROOT,
                        "data_root": cls.DATA_ROOT,
                        "budget_level": budget_level,
                    })
                elif slot == 1:
                    configs.append({
                        "name": f"adaptive_adv_{adv_id}",
                        "group": budget_level,
                        "budget": budget,
                        "strategy": f"adaptive_profit_{adv_id}",
                        "profile": profile,
                        "adv_id": adv_id,
                        "model_root": cls.MODEL_ROOT,
                        "data_root": cls.DATA_ROOT,
                        "budget_level": budget_level,
                        "update_interval": interval,
                        "system_prompt_suffix": adaptive_personas[group_idx],
                    })
                else:
                    configs.append({
                        "name": f"fairness_adv_{adv_id}",
                        "group": budget_level,
                        "budget": budget,
                        "strategy": f"fairness_aware_{adv_id}",
                        "profile": profile,
                        "adv_id": adv_id,
                        "model_root": cls.MODEL_ROOT,
                        "data_root": cls.DATA_ROOT,
                        "budget_level": budget_level,
                        "update_interval": interval,
                        "slift_low_threshold": threshold,
                        "system_prompt_suffix": fairness_personas[group_idx],
                    })
        return configs
    
    @classmethod
    def get_experiment_group_configs(cls, group_num: int) -> List[Dict[str, Any]]:
        """Return configs for the given experiment group (1–4)."""
        if group_num == 1:
            return cls.get_group1_configs()
        elif group_num == 2:
            return cls.get_group2_configs()
        elif group_num == 3:
            return cls.get_group3_configs()
        elif group_num == 4:
            return cls.get_group4_configs()
        else:
            raise ValueError(f"Invalid group number: {group_num}. Must be 1-4.")
