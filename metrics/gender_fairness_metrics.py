"""
Gender-based Fairness Metrics for RTB Auction Experiments.

Implements the three core metrics from the paper:
1. Selection Lift (slift) - worst-case fairness
   In m=2 setting (male/female), slift = min_i min(q_i,m, q_i,f) / max(q_i,m, q_i,f)
   which is equivalent to the paper definition: min_{i,j} q_{ij} / (1 - q_{ij})
2. Revenue ratio κ (kappa) - rev_fair / rev_base
3. Advertiser displacement dTV - total variation distance

Fairness dimension: impression user gender (male/female), not agent budget group.
"""
from collections import defaultdict
from typing import Dict, List, Any, Optional, Tuple
import warnings


class GenderFairnessMetrics:
    """
    Gender-based fairness metrics calculator.
    
    Computes fairness metrics based on impression user gender (male/female),
    not agent budget groups. This aligns with the paper's fairness dimension.
    """
    
    def __init__(
        self,
        data_root: Optional[str] = None,
        min_impressions_threshold: int = 10
    ):
        """
        Args:
            data_root: Data root for GenderFeatureMapper (required for raw-format impressions).
            min_impressions_threshold: Min exposures per advertiser to include in system slift;
                only advertisers with E_i,total >= this are counted. 0 = no threshold.
        """
        self.data_root = data_root
        self.min_impressions_threshold = max(0, int(min_impressions_threshold))
        if data_root is None:
            import warnings
            warnings.warn("data_root not provided. Gender extraction may not work for original format impressions.")
    
    def compute(
        self, 
        round_history: List[Dict[str, Any]],
        extract_gender_fn: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Compute gender-based fairness metrics.
        
        Args:
            round_history: List of round records, each containing:
                - "round": round number
                - "winner": winner agent name (or None if skipped)
                - "payment": payment amount (or None if skipped)
                - "impression": impression dict with gender info (optional)
                - "skipped": bool, True if round was skipped (e.g., unknown gender)
            extract_gender_fn: Optional function to extract gender from impression.
                             If None, tries to extract from impression dict directly.
                             Signature: extract_gender_fn(impression) -> 'male'|'female'|None
        
        Returns:
            Dictionary containing:
            - "slift": system-level selection lift (paper definition, equivalent to slift_balance in m=2)
            - "kappa": revenue ratio (requires baseline comparison, None if not provided)
            - "dTV": advertiser displacement (requires baseline comparison, None if not provided)
            - "per_advertiser": detailed stats per advertiser
            - "exposure_by_gender": exposure counts by gender (auxiliary)
            - "exposure_share_by_gender": exposure shares by gender (auxiliary)
            - "win_rate_by_gender": win rate by gender (auxiliary, using total_wins as denominator)
        """
        # Extract gender information and compute exposures
        exposures_by_advertiser_gender: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        payments_by_advertiser: Dict[str, float] = defaultdict(float)
        total_payment = 0.0
        skipped_rounds = 0
        valid_rounds = 0
        
        for record in round_history:
            # Skip rounds that were explicitly skipped (e.g., no valid bids)
            # Note: Unknown gender rounds are NOT skipped here - they proceed normally
            if record.get("skipped", False):
                skipped_rounds += 1
                continue
            
            winner = record.get("winner")
            payment = record.get("payment")
            impression = record.get("impression")
            
            # Extract gender from impression
            gender = self._extract_gender(impression, extract_gender_fn)
            
            # Only count rounds with valid gender (male/female) for metrics calculation
            # Unknown gender rounds are excluded from metrics but not from bidding
            if gender not in ['male', 'female']:
                skipped_rounds += 1
                continue
            
            valid_rounds += 1
            
            # Count exposures by advertiser and gender
            if winner:
                exposures_by_advertiser_gender[winner][gender] += 1
                
                # Accumulate payments (no restriction on payment > 0)
                if payment is not None:
                    payments_by_advertiser[winner] += payment
                    total_payment += payment
        
        # Compute per-advertiser statistics
        per_advertiser = self._compute_per_advertiser_stats(
            exposures_by_advertiser_gender
        )
        
        # Compute Selection Lift (slift) - paper definition
        # In m=2 setting (male/female), this is equivalent to:
        # slift = min_i min(q_i,m, q_i,f) / max(q_i,m, q_i,f)
        # which equals the paper definition: min_{i,j} q_{ij} / (1 - q_{ij})
        slift, slift_details = self._compute_slift(exposures_by_advertiser_gender)
        
        # Compute auxiliary metrics (by gender)
        exposure_by_gender = self._compute_exposure_by_gender(exposures_by_advertiser_gender)
        exposure_share_by_gender = self._compute_exposure_share_by_gender(
            exposures_by_advertiser_gender, valid_rounds
        )
        total_wins = sum(exposures_by_advertiser_gender[adv].get('male', 0) + 
                        exposures_by_advertiser_gender[adv].get('female', 0)
                        for adv in exposures_by_advertiser_gender)
        win_rate_by_gender = self._compute_win_rate_by_gender(
            exposures_by_advertiser_gender, total_wins
        )
        
        return {
            "slift": slift,
            "slift_weighted": slift_details.get("slift_weighted"),
            "kappa": None,  # Requires baseline comparison
            "dTV": None,    # Requires baseline comparison
            "per_advertiser": per_advertiser,
            "slift_details": slift_details,
            "exposure_by_gender": exposure_by_gender,
            "exposure_share_by_gender": exposure_share_by_gender,
            "win_rate_by_gender": win_rate_by_gender,
            "total_payment": total_payment,
            "payments_by_advertiser": dict(payments_by_advertiser),
            "valid_rounds": valid_rounds,
            "total_impressions": valid_rounds,
            "skipped_rounds": skipped_rounds,
            "total_rounds": len(round_history),
            "total_wins": total_wins
        }
    
    def compute_with_baseline(
        self,
        fair_round_history: List[Dict[str, Any]],
        baseline_round_history: List[Dict[str, Any]],
        extract_gender_fn: Optional[callable] = None,
        strict_check: bool = True
    ) -> Dict[str, Any]:
        """
        Compute fairness metrics with baseline comparison for κ, dTV, and impression_ratio.
        
        Args:
            fair_round_history: Round history from fair mechanism
            baseline_round_history: Round history from baseline (GSP) mechanism
            extract_gender_fn: Optional function to extract gender from impression
            strict_check: If True, perform strict consistency check and raise error on mismatch.
                         If False, issue warnings only.
        
        Returns:
            Dictionary with all metrics including kappa, dTV, and impression_ratio.
            impression_ratio = total_impressions_fair / total_impressions_base (Leveling Down, Baumann et al. 2024).
        
        Raises:
            ValueError: If strict_check=True and consistency check fails
        """
        # Consistency check: verify fair and baseline use same impressions
        self._check_consistency(fair_round_history, baseline_round_history, strict_check)
        
        # Compute fair metrics
        fair_metrics = self.compute(fair_round_history, extract_gender_fn)
        
        # Compute baseline metrics
        baseline_metrics = self.compute(baseline_round_history, extract_gender_fn)
        
        # Compute κ (revenue ratio)
        rev_fair = fair_metrics["total_payment"]
        rev_base = baseline_metrics["total_payment"]
        kappa = rev_fair / rev_base if rev_base > 0 else None
        
        # Compute dTV (advertiser displacement)
        dTV = self._compute_dTV(
            fair_metrics["per_advertiser"],
            baseline_metrics["per_advertiser"]
        )
        
        # Impression ratio (Leveling Down, Baumann et al. 2024): total_impressions_fair / total_impressions_base
        total_impressions_fair = fair_metrics.get("total_impressions") or fair_metrics["valid_rounds"]
        total_impressions_base = baseline_metrics.get("total_impressions") or baseline_metrics["valid_rounds"]
        impression_ratio = (
            total_impressions_fair / total_impressions_base
            if total_impressions_base > 0 else None
        )
        
        # Merge results
        result = fair_metrics.copy()
        result["kappa"] = kappa
        result["dTV"] = dTV
        result["impression_ratio"] = impression_ratio
        result["baseline_metrics"] = {
            "slift": baseline_metrics["slift"],
            "total_payment": baseline_metrics["total_payment"],
            "total_impressions": total_impressions_base,
            "per_advertiser": baseline_metrics["per_advertiser"]
        }
        
        return result
    
    def _check_consistency(
        self,
        fair_round_history: List[Dict[str, Any]],
        baseline_round_history: List[Dict[str, Any]],
        strict_check: bool = True
    ) -> None:
        """
        Check consistency between fair and baseline round histories.
        
        Verifies:
        1. Same number of rounds
        2. Same round IDs (if available)
        3. Same skipped rounds (unknown gender filtering)
        
        Args:
            fair_round_history: Round history from fair mechanism
            baseline_round_history: Round history from baseline mechanism
            strict_check: If True, raise ValueError on mismatch. If False, issue warnings.
        
        Raises:
            ValueError: If strict_check=True and consistency check fails
        """
        # Check length
        fair_len = len(fair_round_history)
        baseline_len = len(baseline_round_history)
        
        if fair_len != baseline_len:
            msg = (
                f"Inconsistent round history lengths: "
                f"fair={fair_len}, baseline={baseline_len}. "
                f"Fair and baseline must use the same batch of impressions."
            )
            if strict_check:
                raise ValueError(msg)
            else:
                warnings.warn(msg)
        
        # Check round IDs and skipped status
        mismatches = []
        for i, (fair_rec, base_rec) in enumerate(zip(fair_round_history, baseline_round_history)):
            fair_round = fair_rec.get("round")
            base_round = base_rec.get("round")
            fair_skipped = fair_rec.get("skipped", False)
            base_skipped = base_rec.get("skipped", False)
            
            if fair_round != base_round:
                mismatches.append(f"Round {i}: round ID mismatch (fair={fair_round}, baseline={base_round})")
            
            if fair_skipped != base_skipped:
                mismatches.append(
                    f"Round {i}: skipped status mismatch "
                    f"(fair={'skipped' if fair_skipped else 'not skipped'}, "
                    f"baseline={'skipped' if base_skipped else 'not skipped'}). "
                    f"Unknown gender filtering must be consistent."
                )
        
        if mismatches:
            msg = "Consistency check failed:\n" + "\n".join(mismatches[:10])  # Show first 10
            if len(mismatches) > 10:
                msg += f"\n... and {len(mismatches) - 10} more mismatches"
            if strict_check:
                raise ValueError(msg)
            else:
                warnings.warn(msg)
    
    def _extract_gender(
        self, 
        impression: Optional[Dict[str, Any]], 
        extract_gender_fn: Optional[callable] = None
    ) -> Optional[str]:
        """Extract gender from impression. Prefer extract_gender_fn if given, else GenderFeatureMapper."""
        if impression is None:
            return None
        
        # Use custom extraction function if provided
        if extract_gender_fn is not None:
            return extract_gender_fn(impression)
        
        # Use GenderFeatureMapper if data_root is available
        if self.data_root:
            from tools.gender_feature_mapper import GenderFeatureMapper
            mapper = GenderFeatureMapper(self.data_root)
            return mapper.extract_gender(impression)
        
        # Fallback: Try direct extraction
        gender = impression.get("user_type") or impression.get("gender")
        if gender in ['male', 'female']:
            return gender
        
        # Fallback: Try to extract from sparse feature matrix (legacy method)
        x = impression.get("x")
        if x is not None and hasattr(x, 'indices'):
            # iPinYou feature mapping: 10110=male, 10111=female
            feature_to_gender = {10110: 'male', 10111: 'female'}
            for feat_idx in x.indices:
                if feat_idx in feature_to_gender:
                    return feature_to_gender[feat_idx]
        
        return None
    
    def _compute_per_advertiser_stats(
        self, 
        exposures_by_advertiser_gender: Dict[str, Dict[str, int]]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Compute per-advertiser statistics.
        
        Returns:
            Dictionary mapping advertiser_name to stats:
            {
                "E_i,m": male exposures,
                "E_i,f": female exposures,
                "E_i,total": total exposures,
                "q_i,m": male ratio,
                "q_i,f": female ratio,
                "slift_i": per-advertiser selection lift
            }
        """
        per_advertiser = {}
        
        for advertiser, exposures in exposures_by_advertiser_gender.items():
            E_i_m = exposures.get('male', 0)
            E_i_f = exposures.get('female', 0)
            E_i_total = E_i_m + E_i_f
            
            if E_i_total == 0:
                # Advertiser with no exposures
                per_advertiser[advertiser] = {
                    "E_i,m": 0,
                    "E_i,f": 0,
                    "E_i,total": 0,
                    "q_i,m": None,
                    "q_i,f": None,
                    "slift_i": None,
                    "q_f_minus_q_m": None  # Signed: <0 male bias, >0 female bias
                }
            else:
                q_i_m = E_i_m / E_i_total
                q_i_f = E_i_f / E_i_total
                min_ratio = min(q_i_m, q_i_f)
                max_ratio = max(q_i_m, q_i_f)
                slift_i = min_ratio / max_ratio if max_ratio > 0 else 0.0
                q_f_minus_q_m = q_i_f - q_i_m
                
                per_advertiser[advertiser] = {
                    "E_i,m": E_i_m,
                    "E_i,f": E_i_f,
                    "E_i,total": E_i_total,
                    "q_i,m": q_i_m,
                    "q_i,f": q_i_f,
                    "slift_i": slift_i,
                    "q_f_minus_q_m": q_f_minus_q_m
                }
        
        return per_advertiser
    
    def _compute_slift(
        self, 
        exposures_by_advertiser_gender: Dict[str, Dict[str, int]]
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Compute Selection Lift (slift) - paper definition, with optional threshold and weighted average.
        
        Paper definition (worst-case): slift = min_i slift_i over advertisers with enough exposures.
        Weighted average: slift_weighted = sum(slift_i * E_i_total) / sum(E_i_total), to avoid one
        small advertiser (e.g. 2 wins, both male) dragging system score to 0.
        
        Only advertisers with E_i,total >= min_impressions_threshold are included in system slift
        (both worst-case and weighted). If threshold is 0, no filter.
        
        Args:
            exposures_by_advertiser_gender: Dict[advertiser][gender] -> count
        
        Returns:
            (slift, details_dict) where:
            - slift: system-level worst-case (min_i slift_i) over advertisers passing threshold
            - details: slift, slift_weighted, min_impressions_threshold, advertisers_excluded_*, etc.
        """
        per_advertiser_slift = {}
        advertisers_with_no_exposures = 0
        slift_values = []   # (slift_i, E_i_total) for advertisers passing threshold
        slift_and_total_for_weighted = []  # (slift_i, E_i_total) for E_i_total >= threshold
        
        threshold = self.min_impressions_threshold
        advertisers_below_threshold = 0
        
        for advertiser, exposures in exposures_by_advertiser_gender.items():
            E_i_m = exposures.get('male', 0)
            E_i_f = exposures.get('female', 0)
            E_i_total = E_i_m + E_i_f
            
            if E_i_total == 0:
                advertisers_with_no_exposures += 1
                per_advertiser_slift[advertiser] = None
            else:
                q_i_m = E_i_m / E_i_total
                q_i_f = E_i_f / E_i_total
                min_ratio = min(q_i_m, q_i_f)
                max_ratio = max(q_i_m, q_i_f)
                slift_i = min_ratio / max_ratio if max_ratio > 0 else 0.0
                
                per_advertiser_slift[advertiser] = slift_i
                
                if E_i_total < threshold:
                    advertisers_below_threshold += 1
                else:
                    slift_values.append(slift_i)
                    slift_and_total_for_weighted.append((slift_i, E_i_total))
        
        # System-level worst-case: min_i slift_i (only over advertisers passing threshold)
        slift = min(slift_values) if slift_values else 1.0
        
        # Weighted average: sum(slift_i * E_i_total) / sum(E_i_total)
        total_weight = sum(e for _, e in slift_and_total_for_weighted)
        slift_weighted = (
            sum(s * e for s, e in slift_and_total_for_weighted) / total_weight
            if total_weight > 0 else None
        )
        
        details = {
            "slift": slift,
            "slift_weighted": slift_weighted,
            "min_impressions_threshold": threshold,
            "advertisers_with_no_exposures": advertisers_with_no_exposures,
            "advertisers_excluded_by_threshold": advertisers_below_threshold,
            "advertisers_included": len(slift_values),
            "per_advertiser_slift": per_advertiser_slift
        }
        
        if advertisers_with_no_exposures > 0:
            warnings.warn(
                f"{advertisers_with_no_exposures} advertiser(s) have no exposures "
                f"(E_i,m + E_i,f = 0), skipped in slift calculation"
            )
        if threshold > 0 and advertisers_below_threshold > 0:
            warnings.warn(
                f"{advertisers_below_threshold} advertiser(s) have E_i,total < {threshold}, "
                f"excluded from system slift (use min_impressions_threshold=0 to include all)"
            )
        
        return slift, details
    
    def _compute_dTV(
        self,
        fair_per_advertiser: Dict[str, Dict[str, Any]],
        baseline_per_advertiser: Dict[str, Dict[str, Any]]
    ) -> float:
        """
        Compute Advertiser Displacement (dTV) - total variation distance.
        
        Formula:
        - For each advertiser i: s_i = (E_i,m + E_i,f) / Σ_k(E_k,m + E_k,f)
        - dTV = 0.5 * Σ_i |s_i^base - s_i^fair|
        
        Args:
            fair_per_advertiser: Per-advertiser stats from fair mechanism
            baseline_per_advertiser: Per-advertiser stats from baseline mechanism
        
        Returns:
            dTV value
        """
        # Get all advertisers (union of fair and baseline)
        all_advertisers = set(fair_per_advertiser.keys()) | set(baseline_per_advertiser.keys())
        
        # Compute total exposures for normalization
        fair_total = sum(
            stats.get("E_i,total", 0) 
            for stats in fair_per_advertiser.values()
        )
        baseline_total = sum(
            stats.get("E_i,total", 0) 
            for stats in baseline_per_advertiser.values()
        )
        
        if fair_total == 0 or baseline_total == 0:
            warnings.warn("Cannot compute dTV: zero total exposures in fair or baseline")
            return None
        
        # Compute shares and dTV
        dTV_sum = 0.0
        for advertiser in all_advertisers:
            fair_stats = fair_per_advertiser.get(advertiser, {})
            baseline_stats = baseline_per_advertiser.get(advertiser, {})
            
            s_i_fair = fair_stats.get("E_i,total", 0) / fair_total
            s_i_base = baseline_stats.get("E_i,total", 0) / baseline_total
            
            dTV_sum += abs(s_i_fair - s_i_base)
        
        dTV = 0.5 * dTV_sum
        return dTV
    
    def _compute_exposure_by_gender(
        self, 
        exposures_by_advertiser_gender: Dict[str, Dict[str, int]]
    ) -> Dict[str, int]:
        """Compute total exposures by gender (auxiliary metric)."""
        total_male = sum(
            exposures.get('male', 0) 
            for exposures in exposures_by_advertiser_gender.values()
        )
        total_female = sum(
            exposures.get('female', 0) 
            for exposures in exposures_by_advertiser_gender.values()
        )
        return {"male": total_male, "female": total_female}
    
    def _compute_exposure_share_by_gender(
        self,
        exposures_by_advertiser_gender: Dict[str, Dict[str, int]],
        total_rounds: int
    ) -> Dict[str, float]:
        """Compute exposure shares by gender (auxiliary metric)."""
        exposure_by_gender = self._compute_exposure_by_gender(exposures_by_advertiser_gender)
        total = exposure_by_gender["male"] + exposure_by_gender["female"]
        
        if total == 0:
            return {"male": 0.0, "female": 0.0}
        
        return {
            "male": exposure_by_gender["male"] / total,
            "female": exposure_by_gender["female"] / total
        }
    
    def _compute_win_rate_by_gender(
        self,
        exposures_by_advertiser_gender: Dict[str, Dict[str, int]],
        total_wins: int
    ) -> Dict[str, float]:
        """
        Compute win rate by gender (auxiliary metric).
        
        Uses total_wins as denominator (not valid_rounds) for clarity.
        
        Args:
            exposures_by_advertiser_gender: Dict[advertiser][gender] -> count
            total_wins: Total number of wins across all advertisers and genders
        
        Returns:
            Dict with win rates by gender
        """
        exposure_by_gender = self._compute_exposure_by_gender(exposures_by_advertiser_gender)
        
        if total_wins == 0:
            return {"male": 0.0, "female": 0.0}
        
        return {
            "male": exposure_by_gender["male"] / total_wins,
            "female": exposure_by_gender["female"] / total_wins
        }

