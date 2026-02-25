import os
from typing import Iterator, Tuple, Dict, List, Optional
import numpy as np
from scipy.sparse import csr_matrix

"""
YZX format per line:
  y \t z \t x1:val x2:val ...
where y is click (0/1), z is winning/market price, xk are feature indices (int) per featindex.txt
"""

def read_featindex(featindex_path: str) -> Dict[str, int]:
    mapping: Dict[str, int] = {}
    with open(featindex_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            # supports formats: "feature index" or "index"
            if len(parts) == 2:
                key, idx = parts[0], int(parts[1])
            else:
                key, idx = parts[0], int(parts[-1])
            mapping[key] = idx
    return mapping


def _parse_yzx_line(line: str) -> Tuple[int, float, List[Tuple[int, float]]]:
    parts = line.strip().split()  # whitespace split handles tabs/spaces
    if len(parts) < 3:
        raise ValueError("Invalid yzx line: fewer than 3 tokens")
    y = int(parts[0])
    z = float(parts[1])
    feats: List[Tuple[int, float]] = []
    for tok in parts[2:]:
        if ':' not in tok:
            # allow bare index => value 1.0
            idx = int(tok)
            val = 1.0
        else:
            k, v = tok.split(':', 1)
            idx = int(k)
            val = float(v)
        feats.append((idx, val))
    return y, z, feats


def load_yzx_as_csr(file_path: str, n_features: Optional[int] = None) -> Tuple[csr_matrix, np.ndarray, np.ndarray, int]:
    """Load a .yzx file into CSR matrix X, labels y, prices z.
    If n_features is None, it will be inferred from max index in the file.
    Returns (X, y, z, n_features).
    """
    indices: List[int] = []
    indptr: List[int] = [0]
    data: List[float] = []
    ys: List[int] = []
    zs: List[float] = []
    max_index = 0
    with open(file_path, 'r') as f:
        for line in f:
            if not line.strip():
                continue
            y, z, feats = _parse_yzx_line(line)
            ys.append(y)
            zs.append(z)
            for idx, val in feats:
                indices.append(idx)
                data.append(val)
                if idx > max_index:
                    max_index = idx
            indptr.append(len(indices))
    if n_features is None:
        n_features = max_index + 1
    X = csr_matrix((np.array(data, dtype=np.float32), np.array(indices, dtype=np.int32), np.array(indptr, dtype=np.int32)), shape=(len(ys), n_features))
    return X, np.array(ys, dtype=np.int8), np.array(zs, dtype=np.float32), n_features


def iter_yzx(file_path: str) -> Iterator[Tuple[int, float, List[Tuple[int, float]]]]:
    with open(file_path, 'r') as f:
        for line in f:
            if not line.strip():
                continue
            yield _parse_yzx_line(line)


