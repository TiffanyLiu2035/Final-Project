"""
Gender Feature Mapper: look up gender feature indices from each advertiser's featindex.txt.
"""
import os
from typing import Dict, Optional, Tuple
from tools.ipinyou_loader import read_featindex


class GenderFeatureMapper:
    """
    Manages gender feature index mapping per advertiser.
    featindex.txt may map 26:10110 -> male, 26:10111 -> female.
    """

    def __init__(self, data_root: str):
        self.data_root = data_root
        self._cache: Dict[str, Dict[str, int]] = {}

    def get_gender_indices(self, adv_id: str) -> Optional[Dict[str, int]]:
        """Get gender feature indices for the given advertiser. Returns {'male': idx, 'female': idx} or None."""
        if adv_id in self._cache:
            return self._cache[adv_id]
        featindex_path = os.path.join(self.data_root, adv_id, 'featindex.txt')
        if not os.path.exists(featindex_path):
            return None
        
        mapping = read_featindex(featindex_path)
        male_idx = mapping.get('26:10110')
        female_idx = mapping.get('26:10111')
        
        if male_idx is None or female_idx is None:
            return None
        
        result = {'male': male_idx, 'female': female_idx}
        self._cache[adv_id] = result
        return result
    
    def extract_gender(self, impression: Dict) -> Optional[str]:
        """
        Extract gender from impression. Supports: (1) raw_line/namecol -> usertag column;
        (2) x (CSR) + adv_id -> sparse feature matrix. Returns 'male', 'female', or None.
        """
        gender = impression.get("user_type") or impression.get("gender")
        if gender in ['male', 'female']:
            return gender
        if impression.get("raw_line") is not None:
            raw_line = impression["raw_line"]
            namecol = impression.get("namecol", {})
            usertag_col = namecol.get("usertag")
            if usertag_col is None:
                usertag_col = 26
            if usertag_col is not None and usertag_col < len(raw_line):
                usertag = raw_line[usertag_col].strip()
                if usertag:
                    tags = usertag.split(',')
                    if '10110' in tags:
                        return 'male'
                    elif '10111' in tags:
                        return 'female'
            return None
        x = impression.get("x")
        adv_id = impression.get("adv_id")
        if x is None or adv_id is None:
            return None
        gender_indices = self.get_gender_indices(adv_id)
        if gender_indices is None:
            return None
        if hasattr(x, 'indices'):
            if gender_indices['male'] in x.indices:
                return 'male'
            if gender_indices['female'] in x.indices:
                return 'female'
        
        return None

