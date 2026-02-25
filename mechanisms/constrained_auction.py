"""
Constrained Auction Mechanism with state-dependent fairness penalty.

This mechanism applies dynamic fairness adjustments based on gender demographics
with fairness strength parameter ℓ (ell) and penalty scale λ (lambda). 
The penalty is computed state-dependently based on current fairness metrics, 
using pseudo-count smoothing to avoid oscillations.

Key features:
- Fairness strength ℓ ∈ [0, 0.5]: target interval [ℓ, 1−ℓ] for male_ratio
- Penalty scale λ: controls the strength of penalty adjustments
- Penalty only triggered when ratio is outside [ℓ, 1−ℓ]
- Uses additive shift: score = bid + adjustment (aligned with GSP offset form)
- Pseudo-count smoothing: r̃ = (E_m + α) / (E_m + E_f + 2α)
- Filters unknown gender impressions (only processes male/female)
- Payment rule matches GSPMechanism exactly: uses next_original_bid
"""
from collections import defaultdict
import warnings
from typing import List, Tuple, Optional, Dict, Any
from tools.gender_feature_mapper import GenderFeatureMapper


class ConstrainedAuctionMechanism:
    """
    Constrained auction mechanism with state-dependent fairness penalty.
    
    This mechanism:
    - Tracks exposure by gender (male/female) for each agent
    - Uses fairness strength ℓ to define target interval [ℓ, 1−ℓ]
    - Uses penalty scale λ to control penalty strength
    - Applies penalty only when ratio is outside target interval
    - Uses additive shift: score = bid + adjustment (aligned with GSP)
    - Uses pseudo-count smoothing to avoid early oscillations
    - Filters unknown gender impressions
    - Payment rule matches GSPMechanism exactly
    """
    
    def __init__(
        self, 
        reserve_price: float = 0.0, 
        fairness_strength: float = 0.45,
        penalty_scale: float = 100.0,
        pseudo_count: float = 1.0,
        warmup_threshold: int = 50,
        data_root: Optional[str] = None
    ):
        """
        Initialize Constrained Auction mechanism.
        
        Args:
            reserve_price: Minimum acceptable bid. Defaults to 0.0.
            fairness_strength: Fairness strength parameter ℓ ∈ [0, 0.5].
                              Defines target interval [ℓ, 1−ℓ] for male_ratio.
            penalty_scale: Penalty scale parameter λ (lambda).
                          Controls the strength of penalty adjustments.
                          Default: 100.0 to match bid scale (10~100+); higher = stronger adjustment.
            pseudo_count: Pseudo-count α for smoothing (default 1.0 for faster response).
            warmup_threshold: Optional warmup threshold for additional scaling (default 50).
        """
        if not (0.0 <= fairness_strength <= 0.5):
            raise ValueError(f"fairness_strength ℓ must be in [0, 0.5], got {fairness_strength}")
        
        if penalty_scale < 0:
            raise ValueError(f"penalty_scale λ must be >= 0, got {penalty_scale}")
        if penalty_scale > 2.0:
            import warnings
            warnings.warn(
                f"penalty_scale λ={penalty_scale} is high (>2.0). "
                f"This may cause fairness term to dominate bid, leading to dTV explosion. "
                f"Recommended range: [0, 2.0], typical values: 0.5~1.0"
            )
        
        self.reserve_price = reserve_price
        self.fairness_strength = fairness_strength  # ℓ
        self.penalty_scale = penalty_scale  # λ
        self.pseudo_count = pseudo_count  # α
        self.warmup_threshold = warmup_threshold
        
        # Track state: exposure by agent and gender
        self.exposures_by_agent_gender: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.total_rounds = 0
        
        # Gender feature mapper (handles different feature indices per advertiser)
        if data_root:
            self.gender_mapper = GenderFeatureMapper(data_root)
        else:
            self.gender_mapper = None
    
    def _extract_gender(self, impression: Optional[Dict[str, Any]]) -> Optional[str]:
        """
        Extract gender from impression (male/female only).
        
        Returns None for unknown gender (to be filtered).
        
        Uses GenderFeatureMapper to handle different feature indices per advertiser.
        
        Args:
            impression: Impression dictionary (must contain 'x' and 'adv_id')
        
        Returns:
            'male', 'female', or None (for unknown/default)
        """
        if impression is None:
            return None
        
        # Method 1: Direct metadata
        gender = impression.get("user_type") or impression.get("gender")
        if gender in ['male', 'female']:
            return gender
        
        # Method 2: Use GenderFeatureMapper (handles per-advertiser feature indices)
        if self.gender_mapper:
            return self.gender_mapper.extract_gender(impression)
        
        # Fallback: Try to extract from sparse feature matrix (legacy method)
        # This won't work correctly for mixed impression pools, but kept for backward compatibility
        x = impression.get("x")
        if x is not None and hasattr(x, 'indices'):
            # Legacy feature indices (may not work for all advertisers)
            legacy_map = {10110: 'male', 10111: 'female'}
            for feat_idx in x.indices:
                if feat_idx in legacy_map:
                    return legacy_map[feat_idx]
        
        # Unknown gender: return None (will be filtered)
        return None
    
    def _compute_smooth_male_ratio(self, agent_name: str) -> Optional[float]:
        """
        Compute smoothed male ratio using pseudo-count.
        
        Formula: r̃ = (E_m + α) / (E_m + E_f + 2α)
        
        Args:
            agent_name: Name of the agent
        
        Returns:
            Smoothed male ratio, or None if no exposures
        """
        exposures = self.exposures_by_agent_gender[agent_name]
        male_exposures = exposures.get('male', 0)
        female_exposures = exposures.get('female', 0)
        
        # Apply pseudo-count smoothing
        smooth_male = male_exposures + self.pseudo_count
        smooth_total = male_exposures + female_exposures + 2 * self.pseudo_count
        
        if smooth_total == 0:
            return None
        
        return smooth_male / smooth_total
    
    def _compute_fairness_adjustment(self, agent_name: str, gender: str) -> float:
        """
        Compute state-dependent fairness adjustment for an agent-gender pair.
        
        Adjustment logic:
        - Target interval: [ℓ, 1−ℓ] for male_ratio
        - If r̃ ∈ [ℓ, 1−ℓ]: adjustment = 0
        - If r̃ < ℓ: for male impression, boost (positive adjustment); for female, penalize (negative)
        - If r̃ > 1−ℓ: for male impression, penalize (negative adjustment); for female, boost (positive)
        
        Uses additive shift: score = bid + adjustment (aligned with GSP offset form)
        Adjustment strength controlled by penalty_scale λ.
        
        Args:
            agent_name: Name of the agent
            gender: Gender of current impression ('male' or 'female')
        
        Returns:
            Adjustment value (positive = boost, negative = penalty)
        """
        if gender not in ['male', 'female']:
            return 0.0
        
        # Compute smoothed male ratio
        smooth_male_ratio = self._compute_smooth_male_ratio(agent_name)
        if smooth_male_ratio is None:
            # No history yet, no adjustment
            return 0.0
        
        ℓ = self.fairness_strength
        lower_bound = ℓ
        upper_bound = 1.0 - ℓ
        
        # Check if ratio is within target interval
        if lower_bound <= smooth_male_ratio <= upper_bound:
            # Within target interval: no adjustment
            return 0.0
        
        # Ratio is outside target interval: compute adjustment
        λ = self.penalty_scale
        
        if gender == 'male':
            if smooth_male_ratio < lower_bound:
                # Male ratio too low: boost for male impression (positive adjustment)
                # Adjustment proportional to how far below lower_bound
                gap = lower_bound - smooth_male_ratio
                adjustment = gap * λ  # Positive = boost
            else:  # smooth_male_ratio > upper_bound
                # Male ratio too high: penalize for male impression (negative adjustment)
                gap = smooth_male_ratio - upper_bound
                adjustment = -gap * λ  # Negative = penalize
        else:  # gender == 'female'
            if smooth_male_ratio < lower_bound:
                # Male ratio too low (female ratio too high): penalize for female impression
                gap = lower_bound - smooth_male_ratio
                adjustment = -gap * λ  # Negative = penalize
            else:  # smooth_male_ratio > upper_bound
                # Male ratio too high (female ratio too low): boost for female impression
                gap = smooth_male_ratio - upper_bound
                adjustment = gap * λ  # Positive = boost
        
        # Optional warmup scaling
        exposures = self.exposures_by_agent_gender[agent_name]
        total_exposures = exposures.get('male', 0) + exposures.get('female', 0)
        if total_exposures < self.warmup_threshold:
            warmup_scale = total_exposures / self.warmup_threshold
            adjustment = adjustment * warmup_scale
        
        return adjustment
    
    def select_winner(
        self, 
        bids: List[Tuple[str, float]], 
        agents: Optional[Any] = None,
        impression: Optional[Dict[str, Any]] = None
    ) -> Optional[Tuple[str, float]]:
        """
        Select winner using constrained auction with state-dependent fairness adjustment.
        
        Filters unknown gender impressions (returns None).
        Payment rule matches GSPMechanism exactly:
        - Ranking based on score = bid + adjustment
        - Payment uses next_original_bid (not adjusted score)
        
        Args:
            bids: List of (agent_name, bid) tuples
            agents: Optional list of agents (for compatibility)
            impression: Current impression dictionary
        
        Returns:
            (winner_name, payment) tuple, or None if no valid bids or unknown gender
        """
        # Extract gender from impression (for fairness adjustment)
        # Note: We don't skip unknown gender - all impressions proceed normally
        # Gender filtering is done only when computing metrics
        gender = self._extract_gender(impression)
        
        # If gender is unknown, we'll use it for adjustment calculation (returns 0.0)
        # This ensures all impressions proceed normally
        self.total_rounds += 1
        
        # Filter valid bids (>= reserve_price)
        valid_bids = [
            (name, bid) for name, bid in bids 
            if bid >= self.reserve_price and bid > 0
        ]
        
        if not valid_bids:
            return None
        
        # Compute fairness adjustments and create ranking list
        # Format: (name, original_bid, adjusted_score)
        # Safety: clip adjusted_score to ensure >= reserve_price (avoid negative scores)
        ranked_bids = []
        for name, original_bid in valid_bids:
            adjustment = self._compute_fairness_adjustment(name, gender)
            adjusted_score = original_bid + adjustment  # Additive shift (aligned with GSP)
            # Safety: clip adjusted_score to ensure >= reserve_price
            # This prevents bid+adjustment < 0 from causing ranking distortion
            adjusted_score = max(adjusted_score, self.reserve_price)
            ranked_bids.append((name, original_bid, adjusted_score))
        
        # Sort by adjusted_score (descending) for ranking
        ranked_bids.sort(key=lambda x: x[2], reverse=True)
        
        # Select winner based on adjusted_score
        winner_name, winner_original_bid, _ = ranked_bids[0]
        
        # Update exposure tracking (only for known gender, unknown gender is not tracked)
        if gender in ['male', 'female']:
            self.exposures_by_agent_gender[winner_name][gender] += 1
        
        # Payment rule: matches GSPMechanism exactly
        # payment = max(reserve_price, next_original_bid)
        # where next is the second-ranked bidder (by adjusted_score)
        if len(ranked_bids) > 1:
            # Multiple bidders: payment = max(reserve_price, next_original_bid)
            _, next_original_bid, _ = ranked_bids[1]
            payment = max(self.reserve_price, next_original_bid)
        else:
            # Single bidder: payment = reserve_price
            payment = self.reserve_price
        
        return winner_name, payment
    
    def get_mechanism_info(self) -> Dict[str, Any]:
        """
        Get mechanism information.
        
        Returns:
            Dictionary containing mechanism configuration
        """
        return {
            "name": "Constrained Auction",
            "type": "fairness_enhanced",
            "reserve_price": self.reserve_price,
            "fairness_strength": self.fairness_strength,
            "penalty_scale": self.penalty_scale,
            "pseudo_count": self.pseudo_count,
            "warmup_threshold": self.warmup_threshold,
            "total_rounds": self.total_rounds
        }
    
    def get_fairness_stats(self) -> Dict[str, Any]:
        """
        Get current fairness statistics by agent and gender.
        
        Returns:
            Dictionary with exposure statistics (raw and smoothed ratios)
        """
        stats = {}
        for agent_name, exposures in self.exposures_by_agent_gender.items():
            male_exposures = exposures.get('male', 0)
            female_exposures = exposures.get('female', 0)
            total = male_exposures + female_exposures
            
            if total > 0:
                raw_male_ratio = male_exposures / total
            else:
                raw_male_ratio = None
            
            smooth_male_ratio = self._compute_smooth_male_ratio(agent_name)
            
            stats[agent_name] = {
                'male_exposures': male_exposures,
                'female_exposures': female_exposures,
                'total_exposures': total,
                'raw_male_ratio': raw_male_ratio,
                'smooth_male_ratio': smooth_male_ratio,
                'in_target_interval': (
                    smooth_male_ratio is not None and
                    self.fairness_strength <= smooth_male_ratio <= (1.0 - self.fairness_strength)
                ) if smooth_male_ratio is not None else None
            }
        return stats
