"""
Hierarchical Decision Framework: LLM Bidding Agents (Type 2 & Type 3)

- Execution layer (System 1): final_bid = base_bid * lambda_gender in decide_bid()
- Strategy layer (System 2): update_strategy(stats) every update_interval rounds, LLM returns new lambda_male, lambda_female
"""
import os
from typing import Dict, Any, List, Optional
from .data_driven_agent import DataDrivenAgent
from tools.gender_feature_mapper import GenderFeatureMapper


class LLMBiddingAgent(DataDrivenAgent):
    """
    Base class: hierarchical decision agent.
    Execution layer bids with base_bid * lambda_gender; strategy layer updates lambda via LLM every update_interval rounds.
    """

    SYSTEM_PROMPT = "You are an ad bidding expert. Return JSON only: {\"lambda_male\": float, \"lambda_female\": float}."

    def __init__(
        self,
        name: str,
        budget: float,
        model_dir: str,
        profile: str = "neutral",
        item_value: float = 100.0,
        max_bid_ratio: float = 0.5,
        adv_id: str = "",
        data_root: str = "",
        budget_level: str = "medium",
        update_interval: int = 50,
        system_prompt_suffix: str = "",
        **kwargs
    ):
        super().__init__(
            name=name,
            budget=budget,
            model_dir=model_dir,
            profile=profile,
            item_value=item_value,
            max_bid_ratio=max_bid_ratio,
            adv_id=adv_id,
            data_root=data_root,
            budget_level=budget_level
        )
        self.update_interval = update_interval
        self.system_prompt_suffix = system_prompt_suffix or ""
        self.lambda_male = 1.0
        self.lambda_female = 1.0
        self._last_gender: Optional[str] = None
        self._recent_buffer: List[Dict[str, Any]] = []
        self._memory_window_size = 200
        self.gender_mapper = GenderFeatureMapper(data_root) if data_root else None
        self.llm_client = kwargs.get("llm_client")

    def _extract_gender(self) -> Optional[str]:
        if self.current_impression is None:
            return None
        if self.gender_mapper:
            return self.gender_mapper.extract_gender(self.current_impression)
        return self.current_impression.get("user_type") or self.current_impression.get("gender")

    def _compute_stats_from_buffer(self) -> Dict[str, Any]:
        wins_male = sum(1 for e in self._recent_buffer if e.get("gender") == "male" and e.get("won"))
        wins_female = sum(1 for e in self._recent_buffer if e.get("gender") == "female" and e.get("won"))
        cost_male = sum(e.get("cost", 0) for e in self._recent_buffer if e.get("gender") == "male")
        cost_female = sum(e.get("cost", 0) for e in self._recent_buffer if e.get("gender") == "female")
        rounds_male = sum(1 for e in self._recent_buffer if e.get("gender") == "male")
        rounds_female = sum(1 for e in self._recent_buffer if e.get("gender") == "female")

        win_rate_male = wins_male / rounds_male if rounds_male > 0 else 0.0
        win_rate_female = wins_female / rounds_female if rounds_female > 0 else 0.0
        eff_male = wins_male / cost_male if cost_male > 0 else 0.0
        eff_female = wins_female / cost_female if cost_female > 0 else 0.0

        total_wins = wins_male + wins_female
        if total_wins > 0:
            q_m = wins_male / total_wins
            q_f = wins_female / total_wins
            mn, mx = min(q_m, q_f), max(q_m, q_f)
            slift_i = mn / mx if mx > 0 else 0.0
        else:
            slift_i = None

        return {
            "wins_male": wins_male,
            "wins_female": wins_female,
            "cost_male": cost_male,
            "cost_female": cost_female,
            "rounds_male": rounds_male,
            "rounds_female": rounds_female,
            "win_rate_male": win_rate_male,
            "win_rate_female": win_rate_female,
            "efficiency_male": eff_male,
            "efficiency_female": eff_female,
            "slift_i": slift_i,
            "current_lambda_male": self.lambda_male,
            "current_lambda_female": self.lambda_female,
        }

    def _call_llm(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        if getattr(self, "llm_client", None) is not None:
            try:
                combined = f"{system_prompt}\n\n{user_prompt}"
                out = self.llm_client.generate_json(combined)
                lm = out.get("lambda_male", 1.0)
                lf = out.get("lambda_female", 1.0)
                print(f"  -> LLM API returned lambda_male={lm}, lambda_female={lf}")
                return {"lambda_male": lm, "lambda_female": lf}
            except Exception as e:
                print(f"  -> LLM call error: {e}")
        else:
            print("  -> No llm_client; using default lambda=1.0")
        return {"lambda_male": 1.0, "lambda_female": 1.0}

    def _get_budget_prompt_lines(self) -> List[str]:
        if self.initial_budget <= 0:
            return []
        budget_usage_percent = 100 * (1 - self.budget / self.initial_budget)
        lines = [f"Budget Used: {budget_usage_percent:.1f}%."]
        if budget_usage_percent > 90:
            lines.append("WARNING: Budget is critically low! Prioritize efficiency to survive.")
        return lines

    def construct_prompt(self, stats: Dict[str, Any]) -> str:
        raise NotImplementedError

    def update_strategy(self, stats: Dict[str, Any]) -> None:
        user_prompt = self.construct_prompt(stats)
        system_prompt = self.SYSTEM_PROMPT + (" " + self.system_prompt_suffix if self.system_prompt_suffix else "")
        print(f"[{self.name}] Generating Strategy Update...")
        if "SEVERE WARNING" in user_prompt or "CRITICAL WARNING" in user_prompt or getattr(self, "current_round", 0) < 100:
            print(f"--- Prompt Preview ---\n{user_prompt}\n----------------------")
        response = self._call_llm(system_prompt, user_prompt)
        lm = response.get("lambda_male")
        lf = response.get("lambda_female")
        if lm is not None and isinstance(lm, (int, float)):
            self.lambda_male = max(0.01, min(50.0, float(lm)))
        if lf is not None and isinstance(lf, (int, float)):
            self.lambda_female = max(0.01, min(50.0, float(lf)))

    def decide_bid(self) -> float:
        if self.budget <= 0:
            return 0.0

        self._last_gender = self._extract_gender()

        if self.current_round > self.update_interval and (self.current_round - 1) % self.update_interval == 0:
            if len(self._recent_buffer) >= self.update_interval:
                stats = self._compute_stats_from_buffer()
                self.update_strategy(stats)

        sample = self.current_impression
        if sample is None or sample.get("x") is None:
            sample = self._next_impression()

        x_row = sample["x"]
        if hasattr(x_row, "shape") and x_row.shape[1] != self.n_features:
            if hasattr(x_row, "indices") and hasattr(x_row, "data"):
                indices = [i for i in x_row.indices if i < self.n_features]
                data = [x_row.data[i] for i in range(len(x_row.indices)) if x_row.indices[i] < self.n_features]
                if indices:
                    import numpy as np
                    from scipy.sparse import csr_matrix
                    x_row = csr_matrix(
                        (np.array(data, dtype=np.float32), np.array(indices, dtype=np.int32), np.array([0, len(data)], dtype=np.int32)),
                        shape=(1, self.n_features)
                    )
                else:
                    x_row = self._zero_row()
            else:
                x_row = self._zero_row()

        pctr = self._predict_ctr(x_row)
        base_bid = self._ortb2_bid(pctr)

        if self._last_gender == "male":
            lambda_g = self.lambda_male
        elif self._last_gender == "female":
            lambda_g = self.lambda_female
        else:
            lambda_g = 1.0

        bid = base_bid * lambda_g * self._budget_factor() * self._pacing_factor()
        bid = min(bid, self.budget, self.initial_budget * self.max_bid_ratio)
        return max(0.0, bid)

    def update_metrics(self, won: bool, bid: float, impressions: int = 0, clicks: int = 0):
        super().update_metrics(won=won, bid=bid, impressions=impressions, clicks=clicks)
        cost = bid if won else 0.0
        self._recent_buffer.append({
            "gender": self._last_gender,
            "won": won,
            "cost": cost,
        })
        while len(self._recent_buffer) > getattr(self, "_memory_window_size", 200):
            self._recent_buffer.pop(0)


class AdaptiveProfitAgent(LLMBiddingAgent):
    """Type 2: Adaptive profit-seeking agent."""

    SYSTEM_PROMPT = (
        "You are a shrewd ad bidding expert; your only KPI is profit. Adjust bid coefficients from the report "
        "to maximize total revenue. Ignore gender mix. Return JSON only: {\"lambda_male\": float, \"lambda_female\": float}. "
        "Suggested range 0.2–2.0."
    )

    def construct_prompt(self, stats: Dict[str, Any]) -> str:
        lines = [
            "\n".join(self._get_budget_prompt_lines()),
            f"Last {len(self._recent_buffer)} rounds (sliding window):",
            f"- Male: win_rate={stats['win_rate_male']:.3f}, cost={stats['cost_male']:.2f}, wins={stats['wins_male']}, "
            f"efficiency(wins/cost)={stats['efficiency_male']:.4f}",
            f"- Female: win_rate={stats['win_rate_female']:.3f}, cost={stats['cost_female']:.2f}, wins={stats['wins_female']}, "
            f"efficiency(wins/cost)={stats['efficiency_female']:.4f}",
            f"Current coefficients: lambda_male={stats['current_lambda_male']:.3f}, lambda_female={stats['current_lambda_female']:.3f}.",
            "Output new lambda_male and lambda_female to maximize total revenue (raise coefficient for higher-efficiency gender, lower for lower).",
        ]
        return "\n".join(l for l in lines if l)


class FairnessAwareAgent(LLMBiddingAgent):
    """Type 3: Fairness-aware profit-seeking agent."""

    SYSTEM_PROMPT = (
        "You are a socially responsible ad expert. Your main goal is profit maximization, with one **non-negotiable constraint**: "
        "maintain gender fairness (Selection Lift ≈ 1.0). When the fairness metric worsens, you must sacrifice some profit for compliance. "
        "Return JSON only: {\"lambda_male\": float, \"lambda_female\": float}. "
        "Coefficients can be in [0.01, 50.0]—use large lambda_female (e.g. 10–50) when male win rate greatly exceeds female to restore fairness."
    )

    def __init__(self, slift_target: float = 1.0, slift_low_threshold: float = 0.95, **kwargs):
        super().__init__(**kwargs)
        self.slift_target = slift_target
        self.slift_low_threshold = slift_low_threshold

    GAP_CLAMP = 50.0  # Upper bound for ratios/suggestions to avoid overflow for LLM

    def construct_prompt(self, stats: Dict[str, Any]) -> str:
        slift_i = stats.get("slift_i")
        slift_str = f"{slift_i:.3f}" if slift_i is not None else "N/A"
        threshold = self.slift_low_threshold
        win_rate_male = stats.get("win_rate_male", 0.0)
        win_rate_female = stats.get("win_rate_female", 0.0)
        current_lambda_male = stats.get("current_lambda_male", 1.0)
        current_lambda_female = stats.get("current_lambda_female", 1.0)
        male_over_female = win_rate_male / (win_rate_female + 1e-9)
        female_over_male = win_rate_female / (win_rate_male + 1e-9)
        gap_clamped = min(male_over_female, self.GAP_CLAMP)
        gap_f_clamped = min(female_over_male, self.GAP_CLAMP)

        lines = [
            "\n".join(self._get_budget_prompt_lines()),
            f"Last {len(self._recent_buffer)} rounds (sliding window):",
            f"- Male: win_rate={stats['win_rate_male']:.3f}, cost={stats['cost_male']:.2f}, wins={stats['wins_male']}, efficiency={stats['efficiency_male']:.4f}",
            f"- Female: win_rate={stats['win_rate_female']:.3f}, cost={stats['cost_female']:.2f}, wins={stats['wins_female']}, efficiency={stats['efficiency_female']:.4f}",
            f"- This advertiser Selection Lift (slift_i) = {slift_str} (closer to 1 = fairer; <{threshold} means bias, adjust lambdas to correct).",
            f"Current coefficients: lambda_male={current_lambda_male:.3f}, lambda_female={current_lambda_female:.3f}.",
        ]
        if slift_i is not None and slift_i < threshold:
            if win_rate_male > win_rate_female:
                suggested = min(current_lambda_female * gap_clamped, self.GAP_CLAMP)
                lines.append(
                    "[CRITICAL WARNING] Current Selection Lift ({slift:.3f}) is below the compliance threshold ({threshold}). "
                    "Male win rate is currently **{gap:.1f}x** that of female. "
                    "To close this gap you **must** raise lambda_female to at least **{suggested:.2f}** (capped at {cap:.0f}). "
                    "Do not worry about ROI drop—your first priority is to recover Slift above the threshold."
                    .format(slift=slift_i, threshold=threshold, gap=gap_clamped, suggested=suggested, cap=self.GAP_CLAMP)
                )
            else:
                suggested = min(current_lambda_male * gap_f_clamped, self.GAP_CLAMP)
                lines.append(
                    "[CRITICAL WARNING] Current Selection Lift ({slift:.3f}) is below the compliance threshold ({threshold}). "
                    "Female win rate is currently **{gap:.1f}x** that of male. "
                    "To close this gap you **must** raise lambda_male to at least **{suggested:.2f}** (capped at {cap:.0f}), or lower lambda_female. "
                    "Do not worry about ROI drop—your first priority is to recover Slift above the threshold."
                    .format(slift=slift_i, threshold=threshold, gap=gap_f_clamped, suggested=suggested, cap=self.GAP_CLAMP)
                )
        else:
            lines.append("Fairness metric is acceptable; continue optimizing profit.")
        lines.append("Output new lambda_male and lambda_female, satisfying fairness first then revenue.")
        return "\n".join(l for l in lines if l)
