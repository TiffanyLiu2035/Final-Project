"""
Unified impression pool manager.
Loads from merged test.log.txt (impression_pool_original.log.txt).
"""
import os
import random
from typing import List, Dict, Any
from scipy.sparse import csr_matrix
import numpy as np


class ImpressionPool:
    """Unified impression pool loaded from merged test.log.txt."""

    def __init__(self, data_root: str, random_seed: int = 42, pool_file: str = None):
        """
        Initialize impression pool.

        Args:
            data_root: Data root directory
            random_seed: Random seed
            pool_file: Path to pool file (default: impression_pool_original.log.txt)
        """
        self.data_root = data_root
        self.random_seed = random_seed
        self.pool_file = pool_file or os.path.join(data_root, "impression_pool_original.log.txt")
        self.impressions: List[Dict[str, Any]] = []
        self.current_idx = 0

        self._load_from_log_file()
        random.seed(random_seed)
        random.shuffle(self.impressions)
        self.current_idx = 0

        print(f"  Impression pool ready: {len(self.impressions)} impressions")
        print(f"  Random seed: {random_seed} (same sequence across experiments)")

    def _load_from_log_file(self):
        """Load from merged test.log.txt (impression_pool_original.log.txt)."""
        if not os.path.exists(self.pool_file):
            raise FileNotFoundError(
                f"Impression pool file not found: {self.pool_file}\n"
                f"Run scripts/create_impression_pool_original.py first to create it."
            )
        print(f"Loading from: {self.pool_file}")
        total_count = 0
        namecol = {}  # column name -> index

        with open(self.pool_file, 'r') as f:
            header_line = f.readline().strip()
            header_cols = header_line.split('\t')
            for i, col_name in enumerate(header_cols):
                namecol[col_name.strip().lower()] = i
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split('\t')
                if len(parts) < 25:
                    continue
                click = int(parts[0]) if parts[0].isdigit() else 0
                payprice = 0.0
                if len(parts) > 23:
                    try:
                        payprice = float(parts[23])
                    except ValueError:
                        payprice = 0.0
                adv_id = "unknown"
                if len(parts) > 25:
                    adv_id = parts[25].strip()
                self.impressions.append({
                    "raw_line": parts,
                    "namecol": namecol,
                    "label": click,
                    "price": payprice,
                    "adv_id": adv_id,
                    "x": None
                })
                total_count += 1
        print(f"  Loaded {total_count:,} impressions (raw .log.txt; each agent converts via featindex)")

    def get_next_impression(self) -> Dict[str, Any]:
        """Get next impression (cycles through pool). Returns dict with raw_line, namecol, label, price, adv_id."""
        if not self.impressions:
            return {
                "raw_line": [],
                "namecol": {},
                "label": 0,
                "price": 0.0,
                "adv_id": "unknown",
                "x": None
            }
        
        impression = self.impressions[self.current_idx]
        self.current_idx = (self.current_idx + 1) % len(self.impressions)
        return impression
    
    def get_random_impression(self) -> Dict[str, Any]:
        """Return a random impression from the pool."""
        if not self.impressions:
            return {
                "raw_line": [],
                "namecol": {},
                "label": 0,
                "price": 0.0,
                "adv_id": "unknown",
                "x": None
            }
        
        return random.choice(self.impressions)
    
    def __len__(self) -> int:
        """Return pool size."""
        return len(self.impressions)
