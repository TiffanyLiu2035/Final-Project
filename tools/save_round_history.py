"""
Save and load round_history so metrics can be recomputed without re-running auctions.
"""
import json
import os
from typing import List, Dict, Any, Optional
from datetime import datetime


def save_round_history(
    round_history: List[Dict[str, Any]],
    output_file: str,
    metadata: Optional[Dict[str, Any]] = None
):
    """
    Save round_history to JSON. Only serializable parts are saved: impression raw_line, namecol, adv_id, label, price.
    CSR matrix (x) is not saved; it can be recomputed.
    """
    serializable_history = []
    for record in round_history:
        impression = record.get("impression", {})
        serializable_impression = None
        if impression:
            serializable_impression = {
                "raw_line": impression.get("raw_line"),
                "namecol": impression.get("namecol"),
                "adv_id": impression.get("adv_id"),
                "label": impression.get("label"),
                "price": impression.get("price")
            }
        
        serializable_record = {
            "round": record.get("round"),
            "bids": [
                {"agent": name, "bid": float(bid)}
                for name, bid in record.get("bids", [])
            ],
            "winner": record.get("winner"),
            "payment": record.get("payment"),
            "impression": serializable_impression,
            "agent_stats": {
                name: {
                    "bid": float(stats.get("bid", 0)),
                    "won": bool(stats.get("won", False)),
                    "budget": float(stats.get("budget", 0)),
                    "agent_type": stats.get("agent_type", "unknown"),
                    "group": stats.get("group", "unknown")
                }
                for name, stats in record.get("agent_stats", {}).items()
            },
            "skipped": record.get("skipped", False)
        }
        serializable_history.append(serializable_record)
    
    payload = {
        "metadata": metadata or {},
        "round_history": serializable_history,
        "total_rounds": len(serializable_history),
        "saved_at": datetime.now().isoformat()
    }
    os.makedirs(os.path.dirname(output_file) if os.path.dirname(output_file) else ".", exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print(f"  Round history saved: {output_file}")
    print(f"  Total rounds: {len(serializable_history)}, with impression: {sum(1 for r in serializable_history if r.get('impression'))}")


def load_round_history(input_file: str) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Load round_history from JSON. Impression dicts do not include CSR; they can be recomputed. Returns (round_history, metadata)."""
    with open(input_file, 'r', encoding='utf-8') as f:
        payload = json.load(f)
    metadata = payload.get("metadata", {})
    serializable_history = payload.get("round_history", [])
    round_history = list(serializable_history)
    print(f"  Loaded: {input_file}, rounds: {len(round_history)}, metadata: {metadata}")
    return round_history, metadata


def compute_metrics_from_saved_history(
    saved_file: str,
    data_root: str,
    metrics_calculator=None
):
    """Recompute metrics from saved round history. If metrics_calculator is None, uses GenderFairnessMetrics."""
    round_history, metadata = load_round_history(saved_file)
    if metrics_calculator is None:
        from metrics.gender_fairness_metrics import GenderFairnessMetrics
        metrics_calculator = GenderFairnessMetrics(data_root=data_root)
    metrics = metrics_calculator.compute(round_history)
    return metrics, metadata

