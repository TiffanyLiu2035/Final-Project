import os
import json
from typing import Dict, Any, List, Optional
import numpy as np
from scipy.sparse import csr_matrix
from .base import BaseAgent
from tools.ctr_models import CTRModel
from tools.ipinyou_loader import iter_yzx, read_featindex


class DataDrivenAgent(BaseAgent):
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
        budget_level: str = "medium"
    ):
        super().__init__(name, budget)
        self.initial_budget = budget
        self.profile = profile
        self.item_value = item_value
        self.max_bid_ratio = max_bid_ratio
        self.model_dir = model_dir
        self.adv_id = adv_id or name
        self.data_root = data_root
        self.budget_level = budget_level

        self.ctr_model = CTRModel.load(os.path.join(model_dir, "ctr.joblib"))
        with open(os.path.join(model_dir, "bidding.json"), "r") as f:
            self.bid_params = json.load(f)

        self.n_features = self._infer_n_features()
        self.impressions = self._load_impressions()
        self.impression_idx = 0

        self.current_round = 0
        self.total_rounds = 0
        self.latest_pctr = self.bid_params.get("mean_pctr", 0.0)
        
        # Unified impression pool: current round impression provided by SimulationEngine
        self.current_impression: Optional[Dict[str, Any]] = None
        self.featindex: Optional[Dict[str, int]] = None
        self._load_featindex()
        
        # Performance tracking
        self.win_count = 0
        self.total_impressions = 0
        self.total_cost = 0.0
        self.total_clicks = 0
        self.bid_history: List[float] = []

    def _infer_n_features(self) -> int:
        coef = getattr(self.ctr_model.model, "coef_", None)
        if coef is not None:
            return coef.shape[1]
        feature_names = getattr(self.ctr_model.model, "feature_names_in_", None)
        if feature_names is not None:
            return len(feature_names)
        return int(self.bid_params.get("n_features", 1))
    
    def _load_featindex(self):
        """Load this agent's featindex for raw-format feature conversion."""
        if not self.data_root or not self.adv_id:
            return
        featindex_path = os.path.join(self.data_root, self.adv_id, "featindex.txt")
        if os.path.exists(featindex_path):
            self.featindex = read_featindex(featindex_path)
            if os.getenv("AGENT_DEBUG", "0") == "1":
                print(f"{self.name}: loaded featindex with {len(self.featindex)} feature mappings")

    def _zero_row(self) -> csr_matrix:
        return csr_matrix((1, self.n_features), dtype=np.float32)
    
    def _convert_log_to_features(self, impression: Dict[str, Any]) -> csr_matrix:
        """Convert raw .log.txt impression to this agent's feature space (see make-ipinyou-data/python/mkyzx.py)."""
        if self.featindex is None:
            return self._zero_row()
        raw_line = impression.get("raw_line")
        namecol = impression.get("namecol", {})
        if not raw_line or not namecol:
            return self._zero_row()
        f1s = ["weekday", "hour", "ip", "region", "city", "adexchange", "domain",
               "slotid", "slotwidth", "slotheight", "slotvisibility", "slotformat",
               "creative", "advertiser"]
        f1sp = ["useragent", "slotprice"]
        oses = ["windows", "ios", "mac", "android", "linux"]
        browsers = ["chrome", "sogou", "maxthon", "safari", "firefox", "theworld", "opera", "ie"]

        def feat_trans(name: str, content: str) -> str:
            """Map feature value (see mkyzx.py featTrans)."""
            content = content.lower()
            if name == "useragent":
                operation = "other"
                for o in oses:
                    if o in content:
                        operation = o
                        break
                browser = "other"
                for b in browsers:
                    if b in content:
                        browser = b
                        break
                return operation + "_" + browser
            if name == "slotprice":
                try:
                    price = int(content)
                    if price > 100:
                        return "101+"
                    elif price > 50:
                        return "51-100"
                    elif price > 10:
                        return "11-50"
                    elif price > 0:
                        return "1-10"
                    else:
                        return "0"
                except:
                    return "0"
            return content
        
        def get_tags(content: str) -> List[str]:
            """Parse usertag (see mkyzx.py getTags)."""
            if not content or content == '\n' or len(content) == 0:
                return ["null"]
            return content.strip().split(',')
        
        indices = []
        data = []
        # 1. Truncate features
        if 'truncate' in self.featindex:
            indices.append(self.featindex['truncate'])
            data.append(1.0)
        
        # 2. Direct features (f1s)
        for f in f1s:
            col_idx = namecol.get(f.lower())
            if col_idx is None or col_idx >= len(raw_line):
                continue
            content = raw_line[col_idx].strip()
            if not content:
                continue
            feat_key = f"{col_idx}:{content}"
            if feat_key not in self.featindex:
                # Use :other as fallback
                feat_key = f"{col_idx}:other"
            if feat_key in self.featindex:
                feat_idx = self.featindex[feat_key]
                if feat_idx < self.n_features:
                    indices.append(feat_idx)
                    data.append(1.0)
        
        # 3. Features that need mapping (f1sp)
        for f in f1sp:
            col_idx = namecol.get(f.lower())
            if col_idx is None or col_idx >= len(raw_line):
                continue
            content = raw_line[col_idx].strip()
            if not content:
                continue
            transformed = feat_trans(f, content)
            feat_key = f"{col_idx}:{transformed}"
            if feat_key not in self.featindex:
                feat_key = f"{col_idx}:other"
            if feat_key in self.featindex:
                feat_idx = self.featindex[feat_key]
                if feat_idx < self.n_features:
                    indices.append(feat_idx)
                    data.append(1.0)
        
        # 4. Usertag features
        usertag_col = namecol.get("usertag")
        if usertag_col is not None and usertag_col < len(raw_line):
            tags = get_tags(raw_line[usertag_col])
            for tag in tags:
                if not tag:
                    continue
                feat_key = f"{usertag_col}:{tag}"
                if feat_key not in self.featindex:
                    feat_key = f"{usertag_col}:other"
                if feat_key in self.featindex:
                    feat_idx = self.featindex[feat_key]
                    if feat_idx < self.n_features:
                        indices.append(feat_idx)
                        data.append(1.0)
        
        # Build CSR matrix
        if not indices:
            return self._zero_row()
        
        # Deduplicate (same feature may be added multiple times)
        unique_indices = {}
        for idx, val in zip(indices, data):
            if idx in unique_indices:
                unique_indices[idx] += val
            else:
                unique_indices[idx] = val
        
        final_indices = list(unique_indices.keys())
        final_data = [unique_indices[idx] for idx in final_indices]
        
        indptr = [0, len(final_data)]
        return csr_matrix(
            (np.array(final_data, dtype=np.float32),
             np.array(final_indices, dtype=np.int32),
             np.array(indptr, dtype=np.int32)),
            shape=(1, self.n_features)
        )

    def _feats_to_row(self, feats: List[tuple]) -> csr_matrix:
        """Convert feature list to CSR matrix row, ensuring correct feature dimension."""
        if not feats:
            return self._zero_row()
        indices = []
        data = []
        for idx, val in feats:
            # Only include features within the model's expected dimension
            if idx < self.n_features:
                indices.append(idx)
                data.append(val)
        # If no valid features, return zero row
        if not indices:
            return self._zero_row()
        indptr = [0, len(data)]
        return csr_matrix(
            (np.array(data, dtype=np.float32),
             np.array(indices, dtype=np.int32),
             np.array(indptr, dtype=np.int32)),
            shape=(1, self.n_features)
        )

    def _load_impressions(self) -> List[Dict[str, Any]]:
        path = os.path.join(self.data_root, self.adv_id, "validation.yzx.txt")
        impressions: List[Dict[str, Any]] = []
        if os.path.exists(path):
            for y, z, feats in iter_yzx(path):
                impressions.append({
                    "x": self._feats_to_row(feats),
                    "label": y,
                    "price": z
                })
        if not impressions:
            impressions.append({"x": self._zero_row(), "label": 0, "price": 0.0})
        return impressions

    def set_round_info(self, current_round: int, total_rounds: int):
        self.current_round = current_round
        self.total_rounds = total_rounds
    
    def set_current_impression(self, impression: Dict[str, Any]):
        """Set current round impression (provided by SimulationEngine; all agents bid on the same impression)."""
        self.current_impression = impression
        if impression.get("raw_line") is not None and self.featindex is not None:
            x_row = self._convert_log_to_features(impression)
            impression["x"] = x_row

    def _next_impression(self) -> Dict[str, Any]:
        """Get next impression (fallback when not using unified pool)."""
        if self.current_impression is not None:
            return self.current_impression
        if self.impressions:
            sample = self.impressions[self.impression_idx]
            self.impression_idx = (self.impression_idx + 1) % len(self.impressions)
            return sample
        return {"x": self._zero_row(), "label": 0, "price": 0.0}

    def _predict_ctr(self, x_row: csr_matrix) -> float:
        p = self.ctr_model.predict_proba(x_row)[0]
        self.latest_pctr = float(p)
        return self.latest_pctr

    def _ortb2_bid(self, pctr: float) -> float:
        c = self.bid_params.get("c", 100.0)
        d = self.bid_params.get("d", 1.0)
        lam = self.bid_params.get("lambda", 1.0)
        val = max(pctr, 0.0) / max(lam, 1e-9) + d
        b = c * (np.sqrt(val) - np.sqrt(d))
        return max(0.0, float(b))

    def _budget_factor(self) -> float:
        mapping = {"high": 1.2, "medium": 1.0, "low": 0.8}
        base = mapping.get(self.budget_level, 1.0)
        if self.profile == "aggressive":
            base *= 1.1
        elif self.profile == "conservative":
            base *= 0.9
        return base

    def _pacing_factor(self) -> float:
        if self.total_rounds <= 0 or self.current_round <= 0:
            return 1.0
        remaining_rounds = max(1, self.total_rounds - self.current_round + 1)
        target_per_round = self.initial_budget / self.total_rounds
        expected_remaining = max(1e-6, remaining_rounds * target_per_round)
        ratio = (self.budget) / expected_remaining
        return float(min(1.5, max(0.5, ratio)))

    def decide_bid(self) -> float:
        if self.budget <= 0:
            return 0.0
        
        # Use the impression provided by the simulation engine
        sample = self.current_impression 
        if sample is None or sample.get("x") is None:
            # Fallback if no impression is provided
            sample = self._next_impression()
        
        # Convert impression features to match model's expected dimension
        x_row = sample["x"]
        # If the feature dimension doesn't match, adjust it
        if hasattr(x_row, 'shape') and x_row.shape[1] != self.n_features:
            # Extract features from the impression and rebuild with correct dimension
            if hasattr(x_row, 'indices') and hasattr(x_row, 'data'):
                # Rebuild CSR matrix with correct dimension
                indices = []
                data = []
                for i in range(len(x_row.indices)):
                    idx = x_row.indices[i]
                    if idx < self.n_features:
                        indices.append(idx)
                        data.append(x_row.data[i])
                if indices:
                    x_row = csr_matrix(
                        (np.array(data, dtype=np.float32),
                         np.array(indices, dtype=np.int32),
                         np.array([0, len(data)], dtype=np.int32)),
                        shape=(1, self.n_features)
                    )
                else:
                    x_row = self._zero_row()
            else:
                x_row = self._zero_row()
        
        pctr = self._predict_ctr(x_row)
        base_bid = self._ortb2_bid(pctr)
        bid = base_bid * self._budget_factor() * self._pacing_factor()

        bid = min(bid, self.budget, self.initial_budget * self.max_bid_ratio)

        if os.getenv("AGENT_DEBUG", "0") == "1":
            print(f"{self.name} (DataDriven) bid={bid:.4f} "
                  f"[pCTR={pctr:.6f}, profile={self.profile}, level={self.budget_level}]")
        return bid
    
    def update_metrics(self, won: bool, bid: float, impressions: int = 0, clicks: int = 0):
        """Update performance metrics after each round"""
        self.bid_history.append(bid)
        if won:
            self.win_count += 1
            self.total_impressions += impressions
            self.total_cost += bid
            self.total_clicks += clicks
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for logging"""
        return {
            "profile": self.profile,
            "budget_level": self.budget_level,
            "last_pctr": self.latest_pctr,
            "win_count": self.win_count,
            "win_rate": self.win_count / self.current_round if self.current_round > 0 else 0.0,
            "total_impressions": self.total_impressions,
            "total_cost": self.total_cost,
            "total_clicks": self.total_clicks,
            "roi": ((self.total_clicks * self.item_value - self.total_cost) / self.total_cost) if self.total_cost > 0 else 0.0,
            "ctr": self.total_clicks / self.total_impressions if self.total_impressions > 0 else 0.0,
            "budget_remaining": self.budget,
            "budget_spent_ratio": (self.initial_budget - self.budget) / self.initial_budget if self.initial_budget > 0 else 0.0
        }
