"""
GSP (Generalized Second Price) mechanism for RTB auctions.

This implementation follows standard GSP rules:
- Winner pays the maximum of reserve_price and second-highest bid
- Supports multiple ad slots (num_slots)
- Supports fairness interventions via alpha-shifts (offsets)
- Filters unknown gender impressions (for consistency with fair mechanisms)
"""
from typing import List, Tuple, Optional, Dict, Union, Any


def _extract_gender_static(impression: Optional[Dict[str, Any]], data_root: Optional[str] = None) -> Optional[str]:
    """
    Extract gender from impression (helper function for GSP).
    
    Uses GenderFeatureMapper if data_root is provided, otherwise falls back to legacy method.
    
    Args:
        impression: Impression dictionary
        data_root: Optional data root directory for GenderFeatureMapper
    
    Returns:
        'male', 'female', or None
    """
    if impression is None:
        return None
    
    # Method 1: Direct metadata
    gender = impression.get("user_type") or impression.get("gender")
    if gender in ['male', 'female']:
        return gender
    
    # Method 2: Use GenderFeatureMapper if data_root is provided
    if data_root:
        from tools.gender_feature_mapper import GenderFeatureMapper
        mapper = GenderFeatureMapper(data_root)
        return mapper.extract_gender(impression)
    
    # Method 3: Fallback to legacy method (may not work for mixed impression pools)
    x = impression.get("x")
    if x is not None and hasattr(x, 'indices'):
        # Legacy feature indices (may not work for all advertisers)
        feature_to_gender = {10110: 'male', 10111: 'female'}
        for feat_idx in x.indices:
            if feat_idx in feature_to_gender:
                return feature_to_gender[feat_idx]
    
    return None


class GSPMechanism:
    """
    Generalized Second Price (GSP) auction mechanism.
    
    In GSP:
    - Winners are selected based on bid ranking
    - Each winner pays max(reserve_price, next_highest_bid)
    - If only one valid bidder, payment = reserve_price
    """
    
    def __init__(self, reserve_price: float = 0.0, data_root: Optional[str] = None):
        """
        Initialize GSP mechanism.
        
        Args:
            reserve_price: Minimum acceptable bid. Defaults to 0.0.
            data_root: Optional data root directory for gender feature mapping
        """
        self.reserve_price = reserve_price
        self.offsets: Dict[str, float] = {}  # For fairness interventions (alpha-shifts)
        self.data_root = data_root
    
    def set_offsets(self, offsets: Dict[str, float]) -> None:
        """
        Set fairness intervention offsets (alpha-shifts).
        
        When offsets are set, ranking uses (bid + offset) but payment
        is still based on original bids.
        
        Args:
            offsets: Dictionary mapping agent_name to alpha_value
        """
        self.offsets = offsets or {}
    
    def select_winner(
        self, 
        bids: List[Tuple[str, float]], 
        agents: Optional[Any] = None,
        impression: Optional[Dict[str, Any]] = None,
        num_slots: int = 1
    ) -> Union[Optional[Tuple[str, float]], Optional[List[Tuple[str, float]]]]:
        """
        Select winner(s) using GSP mechanism.
        
        Args:
            bids: List of (agent_name, bid) tuples
            agents: Optional list of agents (for compatibility, not used here)
            impression: Optional impression dictionary. If provided and contains
                       unknown gender, returns None to skip the round (for consistency
                       with fair mechanisms that filter unknown gender).
            num_slots: Number of ad slots to allocate. Defaults to 1.
        
        Returns:
            List of (winner_name, payment) tuples, one per slot.
            Returns None if no valid bids or unknown gender (when impression provided).
        """
        # Note: We don't filter unknown gender here - all impressions proceed normally
        # Gender filtering is done only when computing metrics
        # Filter valid bids (>= reserve_price)
        valid_bids = [
            (name, bid) for name, bid in bids 
            if bid >= self.reserve_price and bid > 0
        ]
        
        if not valid_bids:
            return None
        
        # Apply fairness offsets for ranking (if any)
        if self.offsets:
            ranked_bids = []
            for name, bid in valid_bids:
                adjusted_bid = bid + self.offsets.get(name, 0.0)
                ranked_bids.append((name, bid, adjusted_bid))  # (name, original_bid, adjusted_bid)
            # Sort by adjusted bid for ranking
            ranked_bids.sort(key=lambda x: x[2], reverse=True)
        else:
            # No offsets: use original bids for ranking
            ranked_bids = [(name, bid, bid) for name, bid in valid_bids]
            ranked_bids.sort(key=lambda x: x[2], reverse=True)
        
        # Select winners (up to num_slots)
        winners: List[Tuple[str, float]] = []
        num_winners = min(num_slots, len(ranked_bids))
        
        for i in range(num_winners):
            winner_name, original_bid, _ = ranked_bids[i]
            
            # Calculate payment: max(reserve_price, next_highest_bid)
            if i + 1 < len(ranked_bids):
                # There is a next bidder: payment = max(reserve_price, next_bid)
                _, next_original_bid, _ = ranked_bids[i + 1]
                payment = max(self.reserve_price, next_original_bid)
            else:
                # No next bidder: payment = reserve_price
                payment = self.reserve_price
            
            winners.append((winner_name, payment))
        
        # Return results: tuple for single slot (backward compatibility), list for multi-slot
        if not winners:
            return None
        if num_slots == 1 and len(winners) == 1:
            # Single slot: return tuple for backward compatibility
            return winners[0]
        # Multiple slots: return list
        return winners
    
    def get_mechanism_info(self) -> Dict[str, Any]:
        """
        Get mechanism information.
        
        Returns:
            Dictionary containing mechanism name, type, and reserve_price
        """
        return {
            "name": "GSP",
            "type": "baseline",
            "reserve_price": self.reserve_price,
            "has_offsets": len(self.offsets) > 0,
            "num_offsets": len(self.offsets)
        }
